"""Real X.509 certificate generation, used by the CA simulator.

Produces genuine, correctly-formed certificates and PKCS#12 bundles (unlike the old
mock_sectigo.ps1, which returned a fixed fake string -- finding G1 in the earlier analysis).
The certificates are self-signed for the lab; the shape (SAN, validity, key size) matches what a
real CA would return, so the matching, adapter and verification logic is exercised for real.
"""
import base64
import datetime as dt
import uuid

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID


def _key(bits=3072):
    return rsa.generate_private_key(public_exponent=65537, key_size=bits)


def issue_certificate(common_name: str, san: list[str], valid_days: int, not_before_offset_days: int = 0):
    """Create a self-signed certificate + private key, as a real CA would issue (mode A/B in the spec:
    here the CA -- this simulator -- creates the key together with the certificate, per your answer
    that Sectigo can do this by API)."""
    key = _key()
    not_before = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=not_before_offset_days)
    not_after = not_before + dt.timedelta(days=valid_days)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(n) for n in san]), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
    )
    cert = builder.sign(key, hashes.SHA256())
    return key, cert


def cert_to_pem(cert) -> str:
    return cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")


def key_to_pem(key) -> str:
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("utf-8")


def thumbprint_sha256(cert) -> str:
    return cert.fingerprint(hashes.SHA256()).hex().upper()


def serial_hex(cert) -> str:
    return format(cert.serial_number, "X")


def san_list(cert) -> list[str]:
    try:
        ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        return ext.value.get_values_for_type(x509.DNSName)
    except x509.ExtensionNotFound:
        return []


def to_pkcs12_b64(key, cert, passphrase: str) -> str:
    """The certificate + private key bundle Sectigo would deliver by API (spec chapter 6)."""
    data = pkcs12.serialize_key_and_certificates(
        name=b"cdm",
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(passphrase.encode("utf-8")),
    )
    return base64.b64encode(data).decode("ascii")


def new_id() -> str:
    return "SEC-" + uuid.uuid4().hex[:10].upper()
