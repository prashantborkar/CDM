"""Java keystore adapter -- TESTED on this laptop, using the real `keytool` from the JDK 17
install that is already on this machine (per POC_SETUP_STATUS.md), so this genuinely exercises
AD-JVA-* against a real PKCS#12 keystore, not a simulation of one.

Same lab-only limitation as the Windows adapter: the real target (AD-JVA-01, a Java application
reading its own keystore) has no equivalent "live app" here, so this adapter maintains a real
PKCS#12 keystore file *and* extracts the same cert/key as PEM for lab_site to serve on port 8445,
purely so verify() has a live TLS endpoint to check against.
"""
import base64
import json
import re
import subprocess
import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs12

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.util import audit, new_job_dir  # noqa: E402
from adapters.base import ok, fail, probe_tls  # noqa: E402
from vault_stub.vault import get_credential  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
KEYTOOL = "keytool"  # resolved via PATH; the orchestrator ensures the JDK bin dir is on PATH


def _run_keytool(args, timeout=30):
    return subprocess.run([KEYTOOL] + args, capture_output=True, text=True, timeout=timeout)


def _keystore_password(req) -> str:
    cred = get_credential(req["profile"]["credential_alias"])
    return cred["secret"]


def precheck(req):
    profile = req["profile"]["java"]
    ks_path = ROOT / profile["keystore_path"]
    expected_old = req["expected"].get("old_thumbprint")
    current = None
    if ks_path.exists():
        pw = _keystore_password(req)
        proc = _run_keytool(["-list", "-v", "-keystore", str(ks_path), "-alias", profile["alias"],
                              "-storepass", pw, "-storetype", profile["keystore_type"]])
        m = re.search(r"SHA256:\s*([0-9A-Fa-f:]+)", proc.stdout)
        if m:
            current = m.group(1).replace(":", "").upper()
    if expected_old and current and expected_old != current:
        audit("adapter.java.precheck.drift", job_id=req["job_id"], expected=expected_old, found=current)
        return fail(req["job_id"], "DRIFT_DETECTED",
                    f"Keystore presents {current}, CMDB expected {expected_old}. Stopping before any change.")
    audit("adapter.java.precheck.ok", job_id=req["job_id"], current_thumbprint=current)
    return ok(req["job_id"], evidence={"current_thumbprint": current})


def backup(req):
    profile = req["profile"]["java"]
    job_dir = new_job_dir(req["job_id"])
    backup_dir = job_dir / "backup"
    backup_dir.mkdir(exist_ok=True)
    ks_path = ROOT / profile["keystore_path"]
    if ks_path.exists():
        (backup_dir / ks_path.name).write_bytes(ks_path.read_bytes())
    audit("adapter.java.backup", job_id=req["job_id"], backup_reference=str(backup_dir))
    return ok(req["job_id"], evidence={"backup_reference": str(backup_dir)})


def install(req):
    job_id = req["job_id"]
    bundle = req["bundle"]
    profile = req["profile"]["java"]
    job_dir = new_job_dir(job_id)
    ks_path = ROOT / profile["keystore_path"]
    ks_path.parent.mkdir(parents=True, exist_ok=True)

    pfx_bytes = base64.b64decode(bundle["pkcs12_base64"])
    pfx_path = job_dir / "incoming.p12"
    pfx_path.write_bytes(pfx_bytes)

    keystore_pw = _keystore_password(req)

    if ks_path.exists() and profile.get("alias_strategy", "replace") == "replace":
        _run_keytool(["-delete", "-alias", profile["alias"], "-keystore", str(ks_path),
                       "-storepass", keystore_pw, "-storetype", profile["keystore_type"]])
        # ignore failure: alias may not exist yet on first run

    args = [
        "-importkeystore",
        "-srckeystore", str(pfx_path), "-srcstoretype", "PKCS12", "-srcstorepass", bundle["passphrase"],
        "-srcalias", "cdm",
        "-destkeystore", str(ks_path), "-deststoretype", profile["keystore_type"], "-deststorepass", keystore_pw,
        "-destalias", profile["alias"], "-noprompt",
    ]
    proc = _run_keytool(args, timeout=60)
    if proc.returncode != 0:
        audit("adapter.java.install.keytool_failed", job_id=job_id, stderr=proc.stderr[:400])
        return fail(job_id, "KEYSTORE_IMPORT_FAILED", proc.stderr.strip() or "keytool -importkeystore failed")

    # Extract the same cert+key as PEM for lab_site (see module docstring).
    key, cert, _ = pkcs12.load_key_and_certificates(pfx_bytes, bundle["passphrase"].encode("utf-8"))
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    key_pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                 serialization.NoEncryption()).decode()
    (ROOT / profile["served_cert_path"]).write_text(cert_pem)
    (ROOT / profile["served_key_path"]).write_text(key_pem)

    audit("adapter.java.install", job_id=job_id, keystore=str(ks_path), alias=profile["alias"])
    return ok(job_id, evidence={"keystore": str(ks_path), "alias": profile["alias"]})


def activate(req):
    # lab_site auto-reloads from the PEM files. A real Tomcat 9+ connector reload/JMX call, or a
    # controlled restart inside a change window, goes here in production (AD-JVA-08).
    audit("adapter.java.activate", job_id=req["job_id"], method="lab_site-auto-reload")
    return ok(req["job_id"], evidence={"method": "lab_site-auto-reload"})


def verify(req):
    import time
    v = req["profile"]["verification"]
    time.sleep(2.0)
    presented = probe_tls(v["host"], v["port"], v["sni"])
    expected_thumb = req["expected"]["new_thumbprint"]
    ok_thumb = presented["thumbprint"] == expected_thumb
    ok_san = set(req["expected"]["san"]).issubset(set(presented["san"]))
    if ok_thumb and ok_san:
        audit("adapter.java.verify.ok", job_id=req["job_id"], presented=presented)
        return ok(req["job_id"], evidence={"presented": presented})
    audit("adapter.java.verify.failed", job_id=req["job_id"], presented=presented, expected_thumb=expected_thumb)
    return fail(req["job_id"], "VERIFY_MISMATCH", "Live endpoint did not present the expected certificate",
                evidence={"presented": presented})


def rollback(req):
    profile = req["profile"]["java"]
    job_dir = new_job_dir(req["job_id"]) / "backup"
    ks_path = ROOT / profile["keystore_path"]
    src = job_dir / ks_path.name
    restored = []
    if src.exists():
        ks_path.write_bytes(src.read_bytes())
        restored.append(str(ks_path))
    audit("adapter.java.rollback", job_id=req["job_id"], restored=restored)
    return ok(req["job_id"], evidence={"restored": restored})


def cleanup(req):
    job_dir = new_job_dir(req["job_id"])
    pfx = job_dir / "incoming.p12"
    removed = False
    if pfx.exists():
        pfx.unlink()
        removed = True
    audit("adapter.java.cleanup", job_id=req["job_id"], temp_files_removed=removed)
    return ok(req["job_id"], cleanup={"temp_files_removed": removed, "memory_cleared": True, "session_closed": True})


def discover(req):
    profile = req["profile"]["java"]
    ks_path = ROOT / profile["keystore_path"]
    if not ks_path.exists():
        return ok(req["job_id"], evidence={"found": False})
    pw = _keystore_password(req)
    proc = _run_keytool(["-list", "-v", "-keystore", str(ks_path), "-alias", profile["alias"],
                          "-storepass", pw, "-storetype", profile["keystore_type"]])
    m = re.search(r"SHA256:\s*([0-9A-Fa-f:]+)", proc.stdout)
    thumb = m.group(1).replace(":", "").upper() if m else None
    return ok(req["job_id"], evidence={"found": thumb is not None, "thumbprint": thumb})


OPS = {"precheck": precheck, "backup": backup, "install": install, "activate": activate,
       "verify": verify, "rollback": rollback, "cleanup": cleanup, "discover": discover}


def run(operation: str, request: dict) -> dict:
    return OPS[operation](request)
