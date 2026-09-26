"""Bootstraps the demo: creates an OLD certificate (already "deployed") and a NEW replacement (the
one Sectigo would have issued and made available in its landing area) for each lab identity, then
installs the OLD ones as the starting state -- so the very first `orchestrator/run.py demo` run has
something real to discover, match and replace.

Run once, before starting lab_site.py and ca_simulator/server.py, or any time you want to reset the
lab back to its starting state:  python seed.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12

from ca_simulator.server import seed_pair, STATE_PATH
from common.util import load_json, save_json
from vault_stub.vault import get_credential, _seed_if_missing

CERTS = ROOT / "lab_site" / "certs"
CERTS.mkdir(parents=True, exist_ok=True)


def _reset_state():
    for f in [STATE_PATH] + list((ROOT / "ca_simulator").glob("private_*.json")):
        Path(f).unlink(missing_ok=True)
    save_json(ROOT / "cmdb" / "certificates.json", {})
    save_json(ROOT / "cmdb" / "matches.json", {})
    save_json(ROOT / "cmdb" / "review_queue.json", {})
    save_json(ROOT / "jobs" / "plan.json", [])
    save_json(ROOT / "jobs" / "job_log.json", [])


def _install_old_windows(old_id: str):
    priv = load_json(ROOT / "ca_simulator" / f"private_{old_id}.json", None)
    (CERTS / "win01.pem").write_text(priv["cert_pem"])
    (CERTS / "win01.key.pem").write_text(priv["key_pem"])
    print(f"  wrote lab_site/certs/win01.pem (+key) from {old_id}")

    # Also import into the real CurrentUser\My store for realism (harmless if it fails; the demo
    # only depends on the served PEM files above).
    try:
        from cryptography import x509
        cert = x509.load_pem_x509_certificate(priv["cert_pem"].encode())
        key = serialization.load_pem_private_key(priv["key_pem"].encode(), password=None)
        pfx_bytes = pkcs12.serialize_key_and_certificates(
            b"cdm", key, cert, None, serialization.BestAvailableEncryption(b"seed-only"))
        pfx_path = ROOT / "jobs" / "_seed_win.pfx"
        pfx_path.parent.mkdir(exist_ok=True)
        pfx_path.write_bytes(pfx_bytes)
        import os
        env = dict(**os.environ, CDM_PFX_PASS="seed-only")
        ps = ("$pw = ConvertTo-SecureString -String $env:CDM_PFX_PASS -AsPlainText -Force; "
              f"Import-PfxCertificate -FilePath '{pfx_path}' -CertStoreLocation Cert:\\CurrentUser\\My "
              "-Password $pw -Exportable | Out-Null")
        subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
                        capture_output=True, text=True, timeout=30, env=env)
        pfx_path.unlink(missing_ok=True)
        print("  also imported the old certificate into Cert:\\CurrentUser\\My")
    except Exception as exc:  # noqa: BLE001 - best effort only, not required for the demo
        print(f"  (skipped CurrentUser\\My import: {exc})")


def _install_old_java(old_id: str):
    priv = load_json(ROOT / "ca_simulator" / f"private_{old_id}.json", None)
    (CERTS / "api.pem").write_text(priv["cert_pem"])
    (CERTS / "api.key.pem").write_text(priv["key_pem"])
    print(f"  wrote lab_site/certs/api.pem (+key) from {old_id}")

    from cryptography import x509
    cert = x509.load_pem_x509_certificate(priv["cert_pem"].encode())
    key = serialization.load_pem_private_key(priv["key_pem"].encode(), password=None)
    _seed_if_missing()
    keystore_pw = get_credential("lab/java_keystore")["secret"]
    pfx_bytes = pkcs12.serialize_key_and_certificates(
        b"api", key, cert, None, serialization.BestAvailableEncryption(keystore_pw.encode()))
    (CERTS / "api-keystore.p12").write_bytes(pfx_bytes)
    print(f"  wrote lab_site/certs/api-keystore.p12 (alias 'api')")


def main():
    print("Resetting lab state...")
    _reset_state()

    print("\nSeeding web01.lab.example.com (Windows target)...")
    pair = seed_pair("web01.lab.example.com", ["web01.lab.example.com"], old_valid_days=3, new_valid_days=365)
    print(f"  old={pair['old']['id']}  new={pair['new']['id']}")
    _install_old_windows(pair["old"]["id"])

    print("\nSeeding api.lab.example.com (Java target)...")
    pair = seed_pair("api.lab.example.com", ["api.lab.example.com"], old_valid_days=3, new_valid_days=365)
    print(f"  old={pair['old']['id']}  new={pair['new']['id']}")
    _install_old_java(pair["old"]["id"])

    print("\nDone. Now, in separate terminals:")
    print("  1) python lab_site/server.py")
    print("  2) python ca_simulator/server.py")
    print("  3) python orchestrator/run.py demo")


if __name__ == "__main__":
    main()
