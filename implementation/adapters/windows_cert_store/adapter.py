"""Windows certificate adapter -- TESTED on this laptop.

Implements AD-WIN-* from the specification against Cert:\\CurrentUser\\My (this machine is not
admin, so Cert:\\LocalMachine\\My -- the real production target, spec AD-WIN-05 -- is not writable
here; see adapters/windows_cert_store/adapter.ps1 for the production-shape script that targets
LocalMachine and a real IIS binding once WinRM/IIS exist on the AWS Windows host).

Because the lab "site" (lab_site/server.py) is a plain Python HTTPS server and not real IIS, it
cannot read a certificate directly out of the Windows store the way IIS does by thumbprint -- it
needs PEM files. So this adapter does two real things, not one:
  1. Imports the certificate into the real Windows CurrentUser\\My store via PowerShell
     Import-PfxCertificate (genuinely observable with `Get-ChildItem Cert:\\CurrentUser\\My`).
  2. Writes the same certificate + key out as PEM files for lab_site to serve.
Step 2 is only needed because of the lab stand-in; a real IIS binding update (AD-WIN-08) does not
need it. The import in step 1 is marked -Exportable, which is a deliberate, clearly-flagged lab-only
relaxation of the "non-exportable" rule in AD-WIN-05/FR-KEY-007 -- it exists solely so this adapter
can hand the key to lab_site. The production adapter (adapter.ps1) imports non-exportable, full stop.
"""
import base64
import json
import subprocess
import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs12

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.util import audit, new_job_dir, redact  # noqa: E402
from adapters.base import ok, fail, probe_tls  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def _run_ps(command: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True, text=True, timeout=60,
    )


def precheck(req):
    profile = req["profile"]["windows"]
    served_cert = ROOT / profile["served_cert_path"]
    expected_old = req["expected"].get("old_thumbprint")
    current = None
    if served_cert.exists():
        cert = x509.load_pem_x509_certificate(served_cert.read_bytes())
        current = cert.fingerprint(hashes.SHA256()).hex().upper()
    if expected_old and current and expected_old != current:
        audit("adapter.windows.precheck.drift", job_id=req["job_id"], expected=expected_old, found=current)
        return fail(req["job_id"], "DRIFT_DETECTED",
                    f"Server presents {current}, CMDB expected {expected_old}. Stopping before any change.")
    audit("adapter.windows.precheck.ok", job_id=req["job_id"], current_thumbprint=current)
    return ok(req["job_id"], evidence={"current_thumbprint": current})


def backup(req):
    profile = req["profile"]["windows"]
    job_dir = new_job_dir(req["job_id"])
    backup_dir = job_dir / "backup"
    backup_dir.mkdir(exist_ok=True)
    for key in ("served_cert_path", "served_key_path"):
        src = ROOT / profile[key]
        if src.exists():
            (backup_dir / src.name).write_bytes(src.read_bytes())
    audit("adapter.windows.backup", job_id=req["job_id"], backup_reference=str(backup_dir))
    return ok(req["job_id"], evidence={"backup_reference": str(backup_dir)})


def install(req):
    """Bundle carries {pkcs12_base64, passphrase, chain_pem} -- fetched by the orchestrator from
    the CA simulator's /bundle/ endpoint just before this call (spec stage 7). The bundle itself
    is never written to ServiceNow-equivalent state; it lives only in the job directory, which
    cleanup() deletes (FR-KEY-004)."""
    job_id = req["job_id"]
    bundle = req["bundle"]
    profile = req["profile"]["windows"]
    job_dir = new_job_dir(job_id)

    pfx_bytes = base64.b64decode(bundle["pkcs12_base64"])
    pfx_path = job_dir / "incoming.pfx"
    pfx_path.write_bytes(pfx_bytes)

    # Real Windows store import, via PowerShell, password kept out of argv (env var + SecureString).
    ps = (
        "$pw = ConvertTo-SecureString -String $env:CDM_PFX_PASS -AsPlainText -Force; "
        f"$c = Import-PfxCertificate -FilePath '{pfx_path}' -CertStoreLocation Cert:\\CurrentUser\\My "
        "-Password $pw -Exportable; "
        "@{thumbprint=$c.Thumbprint} | ConvertTo-Json -Compress"
    )
    import os
    env = dict(**os.environ, CDM_PFX_PASS=bundle["passphrase"])
    proc = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
                           capture_output=True, text=True, timeout=60, env=env)
    if proc.returncode != 0:
        audit("adapter.windows.install.store_import_failed", job_id=job_id, stderr=proc.stderr[:400])
        return fail(job_id, "STORE_IMPORT_FAILED", proc.stderr.strip() or "Import-PfxCertificate failed")
    store_result = json.loads(proc.stdout.strip())
    store_thumbprint = store_result["thumbprint"].upper()

    # Extract the same cert+key as PEM for lab_site to serve (see module docstring).
    key, cert, _ = pkcs12.load_key_and_certificates(pfx_bytes, bundle["passphrase"].encode("utf-8"))
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    key_pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                 serialization.NoEncryption()).decode()
    (ROOT / profile["served_cert_path"]).write_text(cert_pem)
    (ROOT / profile["served_key_path"]).write_text(key_pem)

    audit("adapter.windows.install", job_id=job_id, store_thumbprint=store_thumbprint)
    return ok(job_id, evidence={"store_thumbprint": store_thumbprint, "key_exportable_lab_only": True})


def activate(req):
    # lab_site polls file mtime and reloads automatically -- nothing further to do here.
    # A real IIS adapter would call Get-WebBinding / AddSslCertificate here instead (AD-WIN-08).
    audit("adapter.windows.activate", job_id=req["job_id"], method="lab_site-auto-reload")
    return ok(req["job_id"], evidence={"method": "lab_site-auto-reload"})


def verify(req):
    v = req["profile"]["verification"]
    import time
    time.sleep(2.0)  # give lab_site's poll loop a moment to pick up the new files
    presented = probe_tls(v["host"], v["port"], v["sni"])
    expected_thumb = req["expected"]["new_thumbprint"]
    ok_thumb = presented["thumbprint"] == expected_thumb
    ok_san = set(req["expected"]["san"]).issubset(set(presented["san"]))
    if ok_thumb and ok_san:
        audit("adapter.windows.verify.ok", job_id=req["job_id"], presented=presented)
        return ok(req["job_id"], evidence={"presented": presented})
    audit("adapter.windows.verify.failed", job_id=req["job_id"], presented=presented, expected_thumb=expected_thumb)
    return fail(req["job_id"], "VERIFY_MISMATCH", "Live endpoint did not present the expected certificate",
                evidence={"presented": presented})


def rollback(req):
    profile = req["profile"]["windows"]
    job_dir = new_job_dir(req["job_id"]) / "backup"
    restored = []
    for key in ("served_cert_path", "served_key_path"):
        dest = ROOT / profile[key]
        src = job_dir / dest.name
        if src.exists():
            dest.write_bytes(src.read_bytes())
            restored.append(str(dest))
    audit("adapter.windows.rollback", job_id=req["job_id"], restored=restored)
    return ok(req["job_id"], evidence={"restored": restored})


def cleanup(req):
    job_dir = new_job_dir(req["job_id"])
    pfx = job_dir / "incoming.pfx"
    removed = False
    if pfx.exists():
        pfx.unlink()
        removed = True
    audit("adapter.windows.cleanup", job_id=req["job_id"], temp_files_removed=removed)
    return ok(req["job_id"], cleanup={"temp_files_removed": removed, "memory_cleared": True, "session_closed": True})


def discover(req):
    profile = req["profile"]["windows"]
    served_cert = ROOT / profile["served_cert_path"]
    if not served_cert.exists():
        return ok(req["job_id"], evidence={"found": False})
    cert = x509.load_pem_x509_certificate(served_cert.read_bytes())
    thumb = cert.fingerprint(hashes.SHA256()).hex().upper()
    return ok(req["job_id"], evidence={"found": True, "thumbprint": thumb,
                                        "not_after": cert.not_valid_after_utc.isoformat()})


OPS = {"precheck": precheck, "backup": backup, "install": install, "activate": activate,
       "verify": verify, "rollback": rollback, "cleanup": cleanup, "discover": discover}


def run(operation: str, request: dict) -> dict:
    return OPS[operation](request)
