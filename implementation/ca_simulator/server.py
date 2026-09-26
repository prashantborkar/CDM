"""CA SIMULATOR -- stands in for the Sectigo landing area until a real Sectigo tenant/sandbox exists
(spec chapter 6, section 14.2, item V1: "Sectigo creates the private key together with the
certificate and delivers it by API"). This is Path A from CDM_Prerequisites_Simple_Steps.md step 14.

Unlike the earlier mock_sectigo.ps1 (finding G1: a fixed fake string), this issues real certificates
with real keys using ca_simulator/certs.py, and exposes the three calls CDM actually needs:

  GET  /api/ssl/v1?since=<iso8601>        -> list of certificates available (the landing area)
  GET  /api/ssl/v1/collect/{id}           -> public certificate PEM only (no key)   [stage 2]
  GET  /api/ssl/v1/bundle/{id}            -> certificate + chain + PRIVATE KEY, PKCS#12   [stage 7]

The bundle endpoint enforces `expected_downloads` from the config and records every download in the
audit log, mirroring FR-KEY-006 ("record each bundle download and alert on an unexpected repeat").

SWAP TO PRODUCTION: point sources.sectigo.base_url at the real tenant and route the API credential
through the vault (FR-SRC-012). Nothing else in the orchestrator, matcher or adapters needs to change
because they only ever talk to this HTTP interface.

Run:  python ca_simulator/server.py
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.util import load_json, save_json, audit, utcnow, load_config  # noqa: E402
from ca_simulator.certs import (  # noqa: E402
    issue_certificate, cert_to_pem, key_to_pem, thumbprint_sha256, serial_hex, san_list,
    to_pkcs12_b64, new_id,
)

STATE_PATH = Path(__file__).resolve().parent / "state.json"
BIND_PORT = 8843


def _load_state():
    return load_json(STATE_PATH, {"certificates": {}, "downloads": {}})


def _save_state(state):
    save_json(STATE_PATH, state)


def seed_pair(common_name: str, san: list[str], old_valid_days: int = 3, new_valid_days: int = 365,
              already_deployed_serial=None):
    """Create an OLD certificate (near/inside its renewal window) and a NEW replacement for the
    same identity, as the CA simulator's landing area content. Used by seed.py for the demo."""
    state = _load_state()

    old_key, old_cert = issue_certificate(common_name, san, valid_days=old_valid_days,
                                           not_before_offset_days=-(old_valid_days - 1))
    old_id = new_id()
    state["certificates"][old_id] = {
        "id": old_id, "common_name": common_name, "san": san,
        "serial": serial_hex(old_cert), "thumbprint": thumbprint_sha256(old_cert),
        "valid_from": old_cert.not_valid_before_utc.isoformat(),
        "valid_to": old_cert.not_valid_after_utc.isoformat(),
        "status": "issued", "profile": "lab-default", "issued_at": utcnow(),
        "_role": "old",
    }
    old_bundle = {"cert_pem": cert_to_pem(old_cert), "chain_pem": "", "key_pem": key_to_pem(old_key)}
    save_json(Path(__file__).resolve().parent / f"private_{old_id}.json", old_bundle)

    new_key, new_cert = issue_certificate(common_name, san, valid_days=new_valid_days, not_before_offset_days=0)
    new_id_ = new_id()
    state["certificates"][new_id_] = {
        "id": new_id_, "common_name": common_name, "san": san,
        "serial": serial_hex(new_cert), "thumbprint": thumbprint_sha256(new_cert),
        "valid_from": new_cert.not_valid_before_utc.isoformat(),
        "valid_to": new_cert.not_valid_after_utc.isoformat(),
        "status": "issued", "profile": "lab-default", "issued_at": utcnow(),
        "_role": "new", "_replaces": old_id,
    }
    new_bundle = {"cert_pem": cert_to_pem(new_cert), "chain_pem": "", "key_pem": key_to_pem(new_key)}
    save_json(Path(__file__).resolve().parent / f"private_{new_id_}.json", new_bundle)

    _save_state(state)
    audit("ca_sim.seed", common_name=common_name, old_id=old_id, new_id=new_id_)
    return {"old": state["certificates"][old_id], "new": state["certificates"][new_id_]}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # quiet; audit log already records what matters

    def _json(self, code, payload):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        parts = [p for p in parsed.path.split("/") if p]
        qs = parse_qs(parsed.query)
        state = _load_state()

        if parts == ["api", "ssl", "v1"]:
            since = qs.get("since", [None])[0]
            items = list(state["certificates"].values())
            if since:
                items = [c for c in items if c["issued_at"] >= since]
            audit("ca_sim.list", count=len(items), since=since)
            self._json(200, {"count": len(items), "certificates": items})
            return

        if len(parts) == 4 and parts[:3] == ["api", "ssl", "v1"] and parts[3] == "collect":
            self._json(404, {"error": "missing id"}); return

        if len(parts) == 5 and parts[:3] == ["api", "ssl", "v1"]:
            action, cert_id = parts[3], parts[4]
            cert = state["certificates"].get(cert_id)
            if not cert:
                audit("ca_sim.request.not_found", action=action, id=cert_id)
                self._json(404, {"error": "not found"}); return
            priv_path = Path(__file__).resolve().parent / f"private_{cert_id}.json"
            bundle = load_json(priv_path, None)
            if bundle is None:
                self._json(410, {"error": "certificate material no longer available"}); return

            if action == "collect":
                audit("ca_sim.collect", id=cert_id)
                self._json(200, {"id": cert_id, "cert_pem": bundle["cert_pem"], "chain_pem": bundle["chain_pem"]})
                return

            if action == "bundle":
                cfg = load_config()
                expected = cfg.get("sources", {}).get("sectigo", {}).get("expected_downloads", 1)
                count = state.get("downloads", {}).get(cert_id, 0) + 1
                state.setdefault("downloads", {})[cert_id] = count
                _save_state(state)
                if count > expected:
                    audit("ca_sim.bundle.unexpected_repeat", id=cert_id, count=count, expected=expected)
                else:
                    audit("ca_sim.bundle", id=cert_id, count=count)
                passphrase = "cdm-lab-" + cert_id.lower()
                pkcs12_b64 = to_pkcs12_b64_from_pems(bundle, passphrase)
                self._json(200, {
                    "id": cert_id, "format": "pkcs12", "passphrase": passphrase,
                    "pkcs12_base64": pkcs12_b64, "chain_pem": bundle["chain_pem"],
                    "download_count": count, "expected_downloads": expected,
                })
                return

        self._json(404, {"error": "unknown route"})


def to_pkcs12_b64_from_pems(bundle, passphrase):
    from cryptography.hazmat.primitives import serialization
    key = serialization.load_pem_private_key(bundle["key_pem"].encode(), password=None)
    from cryptography import x509
    cert = x509.load_pem_x509_certificate(bundle["cert_pem"].encode())
    return to_pkcs12_b64(key, cert, passphrase)


def run():
    _load_state()  # ensure state.json exists
    httpd = ThreadingHTTPServer(("127.0.0.1", BIND_PORT), Handler)
    print(f"CA simulator (stands in for the Sectigo landing area) listening on http://127.0.0.1:{BIND_PORT}/")
    print("Endpoints: GET /api/ssl/v1  GET /api/ssl/v1/collect/<id>  GET /api/ssl/v1/bundle/<id>")
    audit("ca_sim.start", port=BIND_PORT)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
