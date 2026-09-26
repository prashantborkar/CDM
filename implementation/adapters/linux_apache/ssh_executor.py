"""Real SSH dispatch for the Linux/Apache adapter -- TESTED against a genuine EC2 Ubuntu machine.

adapter.sh itself runs ON the target (per AD-LNX-02: the MID Server/executor reaches out over SSH;
the script executes locally on the target it's managing). This module is that SSH reach-out: it
serialises the same request envelope every other adapter uses (adapters/base.py's shape), sends it
over stdin to the remote, root-scoped copy of adapter.sh via a deployment account restricted by
sudo to running only that one script (see CDM_Linux_EC2_Setup notes below), and parses the JSON
response back -- so from the orchestrator's or agent's point of view, this behaves exactly like
adapters.windows_cert_store.adapter / adapters.java_keystore.adapter: same run(operation, request)
signature, same response shape.

One-time setup this was validated against (a real EC2 Ubuntu 26.04 host):
  - adapter.sh copied to /usr/local/sbin/cdm_linux_apache_adapter.sh, owned root:root, mode 750
  - /etc/sudoers.d/cdm_deployuser: "deployuser ALL=(root) NOPASSWD: /usr/local/sbin/cdm_linux_apache_adapter.sh"
    -- deployuser can run ONLY that exact script as root, nothing else
  - /var/backups/cdm created, root-owned, mode 700
  - apache2 + mod_ssl installed and enabled
This is a one-time, per-target setup (matches the "enable WinRM once" pattern used for Windows).

This lab's SSH login is as `ubuntu` (the AMI default, key-based) hopping to `deployuser` via
ubuntu's own sudo, because deployuser has no SSH key of its own yet in this environment. In
production, deployuser would have its own SSH key/certificate and be logged into directly (closer
to AD-LNX-02's "short-lived signed SSH certificate" -- the one thing this lab shortcuts, clearly
flagged here rather than left implicit).
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from vault_stub.vault import get_credential  # noqa: E402


def _ssh_run(operation: str, request: dict, cred_alias: str, host: str, remote_script: str, timeout=60) -> dict:
    cred = get_credential(cred_alias)
    ssh_user = cred.get("username", "ubuntu")
    key_path = cred["secret"]  # path to the .pem key file, not the key content itself
    remote_user = "deployuser"

    remote_cmd = f"sudo -u {remote_user} bash -c 'sudo {remote_script} {operation}'"
    cmd = ["ssh", "-i", key_path, "-o", "StrictHostKeyChecking=accept-new",
           "-o", "ConnectTimeout=10", f"{ssh_user}@{host}", remote_cmd]
    proc = subprocess.run(cmd, input=json.dumps(request), capture_output=True, text=True, timeout=timeout)
    if not proc.stdout.strip():
        return {"job_id": request.get("job_id"), "status": "failed", "error_code": "SSH_NO_OUTPUT",
                "message": f"No output from remote adapter (exit {proc.returncode}): {proc.stderr[:500]}"}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"job_id": request.get("job_id"), "status": "failed", "error_code": "BAD_RESPONSE",
                "message": f"Could not parse remote adapter output: {proc.stdout[:500]}"}


def run(operation: str, request: dict) -> dict:
    profile = request["profile"]
    cred_alias = profile["credential_alias"]
    host = profile["linux"]["ssh_host"]
    remote_script = profile["linux"].get("remote_script", "/usr/local/sbin/cdm_linux_apache_adapter.sh")

    # The remote script only needs profile.linux and profile.verification, plus expected/bundle --
    # trim to that shape so nothing extraneous crosses the wire.
    remote_req = {
        "job_id": request["job_id"],
        "expected": request.get("expected", {}),
        "profile": {"linux": profile["linux"], "verification": profile.get("verification", {})},
    }
    if "bundle" in request:
        remote_req["bundle"] = request["bundle"]

    return _ssh_run(operation, remote_req, cred_alias, host, remote_script)
