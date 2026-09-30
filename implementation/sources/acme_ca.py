"""ACME CERTIFICATE SOURCE -- a real alternative to folder_ca.py/the Sectigo API, backed by
acme_lab/real_acme_client.py (real JWS-signed ACME, real Let's Encrypt staging, no certbot).

Produces the exact same shape matcher.py and the deployment bundle-fetch already expect (see
folder_ca.py's docstring) -- id/common_name/san/serial/thumbprint/valid_from/valid_to for
list_certificates(), and {id, format, passphrase, pkcs12_base64, chain_pem} for get_bundle() --
so nothing else in matcher.py, orchestrator/run.py or the adapters needed to change; only
config/cdm_config.json's sources.sectigo.mode switches to "acme".

Issuance is cached to acme_lab/issued/<domain>.json rather than re-run on every poll: hitting a
real external CA on every matcher cycle would be wasteful and, against production Let's Encrypt,
rate-limited. A cached certificate naturally stops being offered as a match once it's been
deployed (matcher.py's M1 rule already requires the candidate's thumbprint to differ from what's
currently live), so re-running this against the same domain is safe -- call force_reissue() to
explicitly get a fresh one on demand (e.g. for a real renewal).
"""
import base64
import json
import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs12

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.util import audit  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ISSUED_DIR = ROOT / "acme_lab" / "issued"


def _cache_path(domain: str) -> Path:
    ISSUED_DIR.mkdir(parents=True, exist_ok=True)
    return ISSUED_DIR / f"{domain.replace('*', '_wildcard_')}.json"


def _issue_and_cache(domain: str) -> dict:
    sys.path.insert(0, str(ROOT / "acme_lab"))
    from real_acme_client import issue_certificate  # noqa: E402
    result = issue_certificate(domain)
    _cache_path(domain).write_text(json.dumps(result, indent=2))
    audit("acme_ca.issued", domain=domain, serial=result["serial"], thumbprint=result["thumbprint"])
    return result


def force_reissue(domain: str) -> dict:
    """Explicit real renewal: always gets a fresh certificate from the ACME CA, ignoring cache."""
    return _issue_and_cache(domain)


def _identity_from_cert_pem(cert_pem: str) -> dict:
    leaf_pem = cert_pem[:cert_pem.index("-----END CERTIFICATE-----") + len("-----END CERTIFICATE-----\n")]
    cert = x509.load_pem_x509_certificate(leaf_pem.encode())
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName)
    except x509.ExtensionNotFound:
        san = []
    cn = cert.subject.rfc4514_string().split("CN=")[-1].split(",")[0]
    return {"common_name": cn, "san": san,
            "serial": format(cert.serial_number, "X"),
            "thumbprint": cert.fingerprint(hashes.SHA256()).hex().upper(),
            "valid_from": cert.not_valid_before_utc.isoformat(),
            "valid_to": cert.not_valid_after_utc.isoformat()}


def list_certificates(domains: list = None) -> list:
    """Returns one record per configured domain: the cached certificate if one exists, otherwise
    issues a new one now (a real, live ACME call)."""
    domains = domains or []
    certs = []
    for domain in domains:
        cache = _cache_path(domain)
        if cache.exists():
            result = json.loads(cache.read_text())
        else:
            result = _issue_and_cache(domain)
        ident = _identity_from_cert_pem(result["cert_pem"])
        certs.append({
            "id": domain, "common_name": ident["common_name"], "san": ident["san"],
            "serial": ident["serial"], "thumbprint": ident["thumbprint"],
            "valid_from": ident["valid_from"], "valid_to": ident["valid_to"],
            "status": "issued", "profile": "acme", "issued_at": ident["valid_from"],
            "_source": "acme",
        })
    audit("acme_ca.list", domains=domains, found=len(certs))
    return certs


def get_bundle(cert_id: str, domains: list = None) -> dict:
    """cert_id is the domain name (see list_certificates -- id == domain). Rewraps the ACME-issued
    PEM cert+key as a PKCS12 bundle, the same transport shape every adapter already expects."""
    cache = _cache_path(cert_id)
    if not cache.exists():
        raise KeyError(f"No cached ACME certificate for '{cert_id}' -- call list_certificates() first")
    result = json.loads(cache.read_text())

    cert = x509.load_pem_x509_certificate(
        result["cert_pem"][:result["cert_pem"].index("-----END CERTIFICATE-----") + 26].encode())
    key = serialization.load_pem_private_key(result["key_pem"].encode(), password=None)
    chain_pem = result["cert_pem"][result["cert_pem"].index("-----END CERTIFICATE-----") + 26:]

    passphrase = "acme-" + cert_id.replace(".", "-")
    pfx_bytes = pkcs12.serialize_key_and_certificates(
        name=cert_id.encode(), key=key, cert=cert, cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(passphrase.encode()))

    audit("acme_ca.bundle_fetched", cert_id=cert_id)
    return {"id": cert_id, "format": "pkcs12", "passphrase": passphrase,
            "pkcs12_base64": base64.b64encode(pfx_bytes).decode("ascii"), "chain_pem": chain_pem}


if __name__ == "__main__":
    import sys as _sys
    domain = _sys.argv[1] if len(_sys.argv) > 1 else "16-16-120-70.nip.io"
    certs = list_certificates([domain])
    for c in certs:
        print(f"{c['id']}: CN={c['common_name']}  SAN={c['san']}  thumbprint={c['thumbprint'][:24]}...  valid_to={c['valid_to']}")
