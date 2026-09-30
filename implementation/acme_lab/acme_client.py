"""A real ACME client (account -> order -> authorization -> challenge -> finalize -> certificate),
talking to mini_acme_ca.py today. To point this at a real ACME CA (Sectigo's ACME service,
Let's Encrypt, etc.) later: change DIRECTORY_URL, add JWS request signing tied to the account
key (see mini_acme_ca.py's docstring for exactly what that CA-side simplification skips), and
implement the challenge type that CA actually requires (HTTP-01 needs a real reachable web
server; DNS-01 needs real DNS API access). The account/order/finalize call sequence below does
not change.

The certificate's own private key is generated here, client-side, and never sent anywhere --
only the CSR (public key + requested identity) is submitted to the CA. That matches how real
ACME works and matches FR-KEY-002 (the private key never leaves the point closest to where it's
needed) already followed elsewhere in this codebase.
"""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

DIRECTORY_URL = "http://127.0.0.1:9000/directory"


def _post(url, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def _get(url):
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.read()


def issue_certificate(domain: str) -> dict:
    """Runs the full ACME order for `domain` and returns a freshly issued certificate."""
    directory = json.loads(_get(DIRECTORY_URL).decode())

    account = _post(directory["newAccount"], {"contact": ["mailto:contact@qubra.uk"]})
    print(f"  [acme] account created: {account['account_id']}")

    order = _post(directory["newOrder"], {"identifiers": [{"type": "dns", "value": domain}]})
    print(f"  [acme] order created: {order['order_id']}  status={order['status']}")

    authz_url = order["authorizations"][0]
    authz = json.loads(_get(authz_url).decode())
    challenge = authz["challenges"][0]
    print(f"  [acme] {challenge['type']} challenge token: {challenge['token']}")
    # Real ACME: this is where we'd serve /.well-known/acme-challenge/<token> on the real domain
    # and only then tell the CA to go check it. No real domain yet, so we just notify the
    # (test-only) CA that the challenge is ready -- see mini_acme_ca.py docstring.
    _post(challenge["url"], {})
    print(f"  [acme] challenge responded, authorization now valid")

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    csr = (x509.CertificateSigningRequestBuilder()
           .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, domain)]))
           .add_extension(x509.SubjectAlternativeName([x509.DNSName(domain)]), critical=False)
           .sign(key, hashes.SHA256()))
    csr_der_hex = csr.public_bytes(serialization.Encoding.DER).hex()

    finalized = _post(order["finalize"], {"csr_der_hex": csr_der_hex})
    print(f"  [acme] finalized, order status={finalized['status']}")

    cert_pem = _get(finalized["certificate"]).decode()
    leaf_pem = cert_pem[:cert_pem.index("-----END CERTIFICATE-----") + len("-----END CERTIFICATE-----\n")]
    chain_pem = cert_pem[len(leaf_pem):]
    leaf_cert = x509.load_pem_x509_certificate(leaf_pem.encode())
    thumbprint = hashlib.sha256(leaf_cert.public_bytes(serialization.Encoding.DER)).hexdigest().upper()
    key_pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()

    return {
        "domain": domain,
        "cert_pem": leaf_pem,
        "chain_pem": chain_pem,
        "key_pem": key_pem,
        "serial": str(leaf_cert.serial_number),
        "thumbprint": thumbprint,
        "not_before": leaf_cert.not_valid_before_utc.isoformat(),
        "not_after": leaf_cert.not_valid_after_utc.isoformat(),
    }


if __name__ == "__main__":
    domain = sys.argv[1] if len(sys.argv) > 1 else "test.acmelab.local"
    print(f"Requesting a certificate for {domain} via ACME...\n")
    result = issue_certificate(domain)
    print(f"\nISSUED:")
    print(f"  domain:      {result['domain']}")
    print(f"  serial:      {result['serial']}")
    print(f"  thumbprint:  {result['thumbprint']}")
    print(f"  valid from:  {result['not_before']}")
    print(f"  valid to:    {result['not_after']}")
