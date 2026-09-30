"""A small local CA that speaks ACME's real state machine (RFC 8555 shape: account -> order ->
authorization -> challenge -> finalize -> certificate) over plain HTTP/JSON.

WHY THIS EXISTS: we have no product domain yet, so no public ACME CA (Let's Encrypt, Sectigo's
ACME service) can issue us anything -- every one of them validates domain ownership by reaching a
real, publicly resolvable hostname, and there isn't one yet. This stands in for that CA so the
CDM side of the conversation (the ACME *client*) can be built and proven today. When a real
Sectigo ACME endpoint + EAB credentials exist, acme_client.py points at that directory URL
instead of this one -- the account/order/challenge/finalize shape is identical either way.

ONE DELIBERATE SIMPLIFICATION, stated plainly so nobody mistakes this for a full RFC 8555
implementation: real ACME requires every request to be wrapped in a signed JWS (JSON Web
Signature) tied to the account's key, and a real CA actually reaches out and checks the
challenge (HTTP-01/DNS-01) against the real domain. This test CA skips both -- it accepts plain
JSON and auto-approves the challenge, because there is no real domain to check yet. Everything
else -- the sequence of calls, the state each object moves through, the fact that the client
generates its own certificate keypair and only submits a CSR -- is the real ACME shape. Adding
JWS signing when pointing at a real ACME service is the only protocol-level gap to close later.

Run:  python mini_acme_ca.py
Serves on http://127.0.0.1:9000
"""
import datetime
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

PKI_DIR = Path(__file__).parent / "pki"
PKI_DIR.mkdir(exist_ok=True)
ROOT_KEY_PATH = PKI_DIR / "root_ca.key"
ROOT_CERT_PATH = PKI_DIR / "root_ca.crt"

LOCK = threading.Lock()
ACCOUNTS = {}
ORDERS = {}
AUTHZ = {}


def _load_or_create_root():
    if ROOT_KEY_PATH.exists() and ROOT_CERT_PATH.exists():
        key = serialization.load_pem_private_key(ROOT_KEY_PATH.read_bytes(), password=None)
        cert = x509.load_pem_x509_certificate(ROOT_CERT_PATH.read_bytes())
        return key, cert

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "CDM ACME Lab Test Root (NOT TRUSTED, LOCAL ONLY)"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CDM ACME Lab"),
    ])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder()
            .subject_name(subject).issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(minutes=5))
            .not_valid_after(now + datetime.timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .sign(key, hashes.SHA256()))

    ROOT_KEY_PATH.write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    ROOT_CERT_PATH.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return key, cert


ROOT_KEY, ROOT_CERT = _load_or_create_root()


def _sign_csr(csr: x509.CertificateSigningRequest) -> x509.Certificate:
    now = datetime.datetime.now(datetime.timezone.utc)
    builder = (x509.CertificateBuilder()
               .subject_name(csr.subject)
               .issuer_name(ROOT_CERT.subject)
               .public_key(csr.public_key())
               .serial_number(x509.random_serial_number())
               .not_valid_before(now - datetime.timedelta(minutes=5))
               .not_valid_after(now + datetime.timedelta(days=90)))
    for ext in csr.extensions:
        if isinstance(ext.value, x509.SubjectAlternativeName):
            builder = builder.add_extension(ext.value, critical=False)
    return builder.sign(ROOT_KEY, hashes.SHA256())


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # keep the console output to what acme_client.py prints

    def _json(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        with LOCK:
            if self.path == "/directory":
                base = "http://127.0.0.1:9000"
                return self._json(200, {
                    "newAccount": f"{base}/new-account",
                    "newOrder": f"{base}/new-order",
                    "root": f"{base}/root-cert",
                })
            if self.path == "/root-cert":
                self.send_response(200)
                self.send_header("Content-Type", "application/x-pem-file")
                pem = ROOT_CERT.public_bytes(serialization.Encoding.PEM)
                self.send_header("Content-Length", str(len(pem)))
                self.end_headers()
                self.wfile.write(pem)
                return
            if self.path.startswith("/authz/"):
                authz_id = self.path.split("/")[-1]
                authz = AUTHZ.get(authz_id)
                if not authz:
                    return self._json(404, {"error": "no such authorization"})
                return self._json(200, authz)
            if self.path.startswith("/cert/"):
                order_id = self.path.split("/")[-1]
                order = ORDERS.get(order_id)
                if not order or order["status"] != "valid":
                    return self._json(409, {"error": "certificate not ready"})
                self.send_response(200)
                self.send_header("Content-Type", "application/pem-certificate-chain")
                chain = order["cert_pem"] + ROOT_CERT.public_bytes(serialization.Encoding.PEM).decode()
                data = chain.encode()
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            return self._json(404, {"error": "not found"})

    def do_POST(self):
        with LOCK:
            body = self._read_json()

            if self.path == "/new-account":
                acct_id = secrets.token_hex(8)
                ACCOUNTS[acct_id] = {"contact": body.get("contact")}
                return self._json(201, {"account_id": acct_id, "status": "valid"})

            if self.path == "/new-order":
                domain = body["identifiers"][0]["value"]
                order_id = secrets.token_hex(8)
                authz_id = secrets.token_hex(8)
                AUTHZ[authz_id] = {
                    "identifier": {"type": "dns", "value": domain},
                    "status": "pending",
                    "challenges": [{
                        "type": "http-01",
                        "url": f"http://127.0.0.1:9000/challenge/{authz_id}",
                        "token": secrets.token_urlsafe(16),
                        "status": "pending",
                    }],
                }
                ORDERS[order_id] = {
                    "domain": domain, "status": "pending",
                    "authorizations": [f"http://127.0.0.1:9000/authz/{authz_id}"],
                    "finalize": f"http://127.0.0.1:9000/finalize/{order_id}",
                    "certificate": None,
                }
                return self._json(201, {"order_id": order_id, **ORDERS[order_id]})

            if self.path.startswith("/challenge/"):
                authz_id = self.path.split("/")[-1]
                authz = AUTHZ.get(authz_id)
                if not authz:
                    return self._json(404, {"error": "no such authorization"})
                # SIMPLIFICATION (see module docstring): a real CA now goes and fetches
                # http://<domain>/.well-known/acme-challenge/<token> itself and checks the
                # response. We have no real domain to check yet, so this auto-approves.
                authz["status"] = "valid"
                authz["challenges"][0]["status"] = "valid"
                return self._json(200, authz)

            if self.path.startswith("/finalize/"):
                order_id = self.path.split("/")[-1]
                order = ORDERS.get(order_id)
                if not order:
                    return self._json(404, {"error": "no such order"})
                authz_ok = all(AUTHZ[u.rsplit("/", 1)[-1]]["status"] == "valid" for u in order["authorizations"])
                if not authz_ok:
                    return self._json(403, {"error": "authorization not valid yet"})
                csr_der = bytes.fromhex(body["csr_der_hex"])
                csr = x509.load_der_x509_csr(csr_der)
                cert = _sign_csr(csr)
                order["cert_pem"] = cert.public_bytes(serialization.Encoding.PEM).decode()
                order["status"] = "valid"
                order["certificate"] = f"http://127.0.0.1:9000/cert/{order_id}"
                return self._json(200, {"order_id": order_id, **order})

            return self._json(404, {"error": "not found"})


def serve(port=9000):
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"mini ACME CA listening on http://127.0.0.1:{port}  (root CA: {ROOT_CERT_PATH})")
    httpd.serve_forever()


if __name__ == "__main__":
    serve()
