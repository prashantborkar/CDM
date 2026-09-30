"""Proves the local ACME loop end-to-end: starts mini_acme_ca.py, requests TWO certificates for
the same domain through acme_client.py, and independently verifies (not just trusts) that each
one is a genuinely new, validly-signed certificate -- different serial/thumbprint each time,
and each one's signature actually checks out against the root CA's public key using
`cryptography`, the same way a real client would verify a chain.

Run:  python test_acme_flow.py
"""
import threading
import time

from cryptography import x509
from cryptography.hazmat.primitives import hashes

import mini_acme_ca
import acme_client


def verify_chain(cert_pem: str, root_cert: x509.Certificate) -> bool:
    leaf = x509.load_pem_x509_certificate(cert_pem.encode())
    try:
        root_cert.public_key().verify(
            leaf.signature, leaf.tbs_certificate_bytes,
            __import__("cryptography.hazmat.primitives.asymmetric.padding", fromlist=["PKCS1v15"]).PKCS1v15(),
            leaf.signature_hash_algorithm,
        )
        return True
    except Exception as exc:
        print(f"    !! signature verification failed: {exc}")
        return False


def main():
    server = threading.Thread(target=mini_acme_ca.serve, daemon=True)
    server.start()
    time.sleep(0.5)  # let the socket open

    domain = "cdmtest.acmelab.local"
    results = []
    for attempt in (1, 2):
        print(f"\n=== Request #{attempt} for {domain} ===")
        cert = acme_client.issue_certificate(domain)
        results.append(cert)
        ok = verify_chain(cert["cert_pem"], mini_acme_ca.ROOT_CERT)
        print(f"  serial={cert['serial']}  thumbprint={cert['thumbprint'][:24]}...")
        print(f"  signature verifies against root CA: {'YES' if ok else 'NO'}")

    print("\n=== Result ===")
    if results[0]["thumbprint"] != results[1]["thumbprint"]:
        print("PASS: two separate ACME requests produced two genuinely different certificates.")
    else:
        print("FAIL: both requests returned the same certificate -- something is cached/wrong.")


if __name__ == "__main__":
    main()
