"""FOLDER-BASED CERTIFICATE INPUT -- the real, simplified stand-in for Sectigo until it's ready.

Drop a certificate and its private key into input_sectigo_certificates/ and CDM picks it up from
there. No API, no simulator process to run, no server to keep alive. This is the "real
implementation, no more complexity" input path.

Accepted file pairs, same basename, either form:
  <name>.crt + <name>.key     -- PEM certificate + PEM private key (unencrypted)
  <name>.pfx                  -- PKCS#12 bundle (certificate + key together)
                                  optional <name>.pass.txt next to it holds the passphrase
                                  (if missing, an empty passphrase is tried)

Identity (common name, SAN, serial, thumbprint, validity) is read from the certificate's own
content -- not from the filename -- exactly as it would be from a real CA. The filename is only
a convenience label for you; CDM never relies on it for matching.

This module produces the exact same shape matcher.py and the deployment bundle-fetch already
expect (see ca_simulator/server.py), so nothing else in the system needed to change: only
config/cdm_config.json's sources.sectigo.mode switches from "api" to "folder".
"""
import base64
import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.util import audit  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _identity_from_cert(cert) -> dict:
    try:
        cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    except IndexError:
        cn = None
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName)
    except x509.ExtensionNotFound:
        san = []
    return {
        "common_name": cn,
        "san": san,
        "serial": format(cert.serial_number, "X"),
        "thumbprint": cert.fingerprint(hashes.SHA256()).hex().upper(),
        "valid_from": cert.not_valid_before_utc.isoformat(),
        "valid_to": cert.not_valid_after_utc.isoformat(),
    }


def _load_cert_and_key(cert_path: Path, key_path: Path = None, pfx_path: Path = None, passphrase: bytes = b""):
    if pfx_path:
        key, cert, _ = pkcs12.load_key_and_certificates(pfx_path.read_bytes(), passphrase or None)
        return cert, key
    cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
    key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    return cert, key


def list_certificates(folder: Path = None) -> list:
    """Scans the folder for cert/key pairs and returns them in the same shape the CA simulator's
    /api/ssl/v1 list endpoint would (see ca_simulator/server.py), so matcher.py needs no changes."""
    folder = folder or (ROOT / "input_sectigo_certificates")
    folder.mkdir(exist_ok=True)
    certs = []
    seen = set()

    for crt_path in sorted(folder.glob("*.crt")) + sorted(folder.glob("*.cer")) + sorted(folder.glob("*.pem")):
        stem = crt_path.stem
        if stem in seen:
            continue
        key_path = crt_path.with_suffix(".key")
        if not key_path.exists():
            audit("folder_ca.skip_no_key", file=crt_path.name)
            continue
        try:
            cert = x509.load_pem_x509_certificate(crt_path.read_bytes())
        except Exception as exc:  # noqa: BLE001
            audit("folder_ca.parse_error", file=crt_path.name, error=str(exc))
            continue
        ident = _identity_from_cert(cert)
        certs.append({
            "id": stem, "common_name": ident["common_name"], "san": ident["san"],
            "serial": ident["serial"], "thumbprint": ident["thumbprint"],
            "valid_from": ident["valid_from"], "valid_to": ident["valid_to"],
            "status": "issued", "profile": "folder-input", "issued_at": ident["valid_from"],
            "_source": "folder", "_cert_path": str(crt_path), "_key_path": str(key_path),
        })
        seen.add(stem)

    for pfx_path in sorted(folder.glob("*.pfx")) + sorted(folder.glob("*.p12")):
        stem = pfx_path.stem
        if stem in seen:
            continue
        pass_file = pfx_path.with_suffix(".pass.txt")
        passphrase = pass_file.read_text().strip().encode() if pass_file.exists() else b""
        try:
            cert, _key = _load_cert_and_key(None, pfx_path=pfx_path, passphrase=passphrase)
        except Exception as exc:  # noqa: BLE001
            audit("folder_ca.parse_error", file=pfx_path.name, error=str(exc))
            continue
        ident = _identity_from_cert(cert)
        certs.append({
            "id": stem, "common_name": ident["common_name"], "san": ident["san"],
            "serial": ident["serial"], "thumbprint": ident["thumbprint"],
            "valid_from": ident["valid_from"], "valid_to": ident["valid_to"],
            "status": "issued", "profile": "folder-input", "issued_at": ident["valid_from"],
            "_source": "folder", "_pfx_path": str(pfx_path), "_pass_path": str(pass_file) if pass_file.exists() else None,
        })
        seen.add(stem)

    audit("folder_ca.scan", folder=str(folder), found=len(certs))
    return certs


def get_bundle(cert_id: str, folder: Path = None) -> dict:
    """Returns {pkcs12_base64, passphrase, chain_pem} for the given certificate id -- the same
    shape the CA simulator's /bundle/ endpoint returns, so the adapters and orchestrator need no
    changes to consume it."""
    certs = {c["id"]: c for c in list_certificates(folder)}
    rec = certs.get(cert_id)
    if not rec:
        raise KeyError(f"No certificate '{cert_id}' found in the input folder")

    if rec.get("_pfx_path"):
        pfx_bytes = Path(rec["_pfx_path"]).read_bytes()
        passphrase = Path(rec["_pass_path"]).read_text().strip() if rec.get("_pass_path") else ""
        cert, key = _load_cert_and_key(None, pfx_path=Path(rec["_pfx_path"]), passphrase=passphrase.encode())
    else:
        cert_path, key_path = Path(rec["_cert_path"]), Path(rec["_key_path"])
        cert, key = _load_cert_and_key(cert_path, key_path)
        passphrase = "folder-input-" + cert_id  # re-wrap as PFX with a fresh passphrase for the trip to the adapter
        pfx_bytes = pkcs12.serialize_key_and_certificates(
            name=cert_id.encode(), key=key, cert=cert, cas=None,
            encryption_algorithm=serialization.BestAvailableEncryption(passphrase.encode()))

    audit("folder_ca.bundle_fetched", cert_id=cert_id)
    return {"id": cert_id, "format": "pkcs12", "passphrase": passphrase,
            "pkcs12_base64": base64.b64encode(pfx_bytes).decode("ascii"), "chain_pem": ""}


if __name__ == "__main__":
    certs = list_certificates()
    print(f"{len(certs)} certificate(s) found in input_sectigo_certificates/:")
    for c in certs:
        print(f"  {c['id']}: CN={c['common_name']}  SAN={c['san']}  valid_to={c['valid_to']}")
