"""Shared envelope helpers for every adapter, matching Appendix A of the specification exactly:
operations precheck | backup | install | activate | verify | rollback | cleanup | discover, and a
response of status success | failed | rolled_back | manual_required with an `evidence` block and no
secrets in it (redacted before it is ever logged or returned to the orchestrator/ServiceNow).
"""
import ssl
import socket
import datetime as dt
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import NameOID


def ok(job_id, evidence=None, cleanup=None):
    return {"job_id": job_id, "status": "success", "error_code": None,
            "evidence": evidence or {}, "cleanup": cleanup or {}}


def fail(job_id, error_code, message, evidence=None):
    return {"job_id": job_id, "status": "failed", "error_code": error_code, "message": message,
            "evidence": evidence or {}, "cleanup": {}}


def manual(job_id, reason, evidence=None):
    return {"job_id": job_id, "status": "manual_required", "error_code": "NO_SAFE_ADAPTER",
            "message": reason, "evidence": evidence or {}, "cleanup": {}}


def probe_tls(host: str, port: int, sni: str, timeout=5):
    """Live endpoint verification (FR-VER-001 / FR-SAF-004): connect over TLS with SNI and read
    back exactly what is presented, independent of whatever the adapter believes it installed."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # self-signed lab certs; production verifies the real chain
    with socket.create_connection((host, port), timeout=timeout) as sock:
        with ctx.wrap_socket(sock, server_hostname=sni) as tls:
            der = tls.getpeercert(binary_form=True)
    cert = x509.load_der_x509_certificate(der)
    thumb = cert.fingerprint(hashes.SHA256()).hex().upper()
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName)
    except x509.ExtensionNotFound:
        san = []
    try:
        cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    except IndexError:
        cn = None
    return {
        "thumbprint": thumb,
        "serial": format(cert.serial_number, "X"),
        "common_name": cn,
        "san": san,
        "not_before": cert.not_valid_before_utc.isoformat(),
        "not_after": cert.not_valid_after_utc.isoformat(),
    }
