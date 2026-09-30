"""Tools the agent is allowed to call.

Deployment is now broken into separate, individually agent-callable steps (precheck, backup,
fetch, install, activate, verify, cleanup) instead of one bundled deploy_certificate() call -- the
agent decides, and you can watch it decide, whether/when to do each one. The one thing that stays
enforced in code, not left to the model: verify_deployment() itself triggers rollback and
re-verification automatically if verification fails -- the agent cannot call verify and choose to
ignore a failure, because the tool's own return value already reflects the rollback having
happened. Every other step is a genuine, separate, skippable-in-principle agent decision.

Every tool returns a small, plain JSON-serialisable dict -- the agent only ever sees structured
facts, never raw stack traces, so its reasoning stays grounded in what actually happened.
"""
import importlib
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import os
os.environ["PATH"] = os.environ.get("PATH", "") + r";C:\Program Files\Microsoft\jdk-17.0.19.10-hotspot\bin"

from common.util import load_json, save_json, audit, utcnow, parse_ts, load_config, CMDB_DIR  # noqa: E402
from common.sn_config import profiles_by_binding as _sn_profiles_by_binding  # noqa: E402
from discovery.discover import scan_all  # noqa: E402
from matcher.match import match_all  # noqa: E402

STATE_PATH = CMDB_DIR / "certificates.json"
ADAPTER_MODULES = {
    "windows_cert_store": "adapters.windows_cert_store.adapter",
    "java_keystore": "adapters.java_keystore.adapter",
    "linux_apache_ssh": "adapters.linux_apache.ssh_executor",
}


def _profiles_by_binding():
    """Live from ServiceNow now -- see common/sn_config.py. No local deployment_profiles.json read."""
    return _sn_profiles_by_binding()


def _run_adapter(technology, operation, request):
    module = importlib.import_module(ADAPTER_MODULES[technology])
    return module.run(operation, request)


def _set_binding_state(binding_id, **fields):
    table = load_json(STATE_PATH, {})
    rec = table.get(binding_id, {})
    rec.update(fields)
    table[binding_id] = rec
    save_json(STATE_PATH, table)


# --------------------------------------------------------------------------- tools the agent sees

def scan_cmdb() -> dict:
    """Reads the current certificate inventory (location, thumbprint, SAN, expiry, state) --
    stands in for a ServiceNow CMDB read, populated here by the local discovery scan."""
    cmdb = scan_all()
    return {"bindings": [
        {"binding_id": b, "server": r["server"], "certificate_name": r["certificate_name"],
         "thumbprint": r["thumbprint"], "valid_to": r["valid_to"], "state": r.get("state")}
        for b, r in cmdb.items()
    ]}


def check_new_certificates() -> dict:
    """Lists certificates available in the input source (the folder standing in for Sectigo,
    or the real API once that exists) that have not necessarily been matched yet."""
    from matcher.match import fetch_ca_list
    certs = fetch_ca_list()
    return {"available": [
        {"id": c["id"], "common_name": c["common_name"], "san": c["san"], "valid_to": c["valid_to"]}
        for c in certs
    ]}


def find_matches() -> dict:
    """Matches expiring/replaced certificates in the CMDB against what's available at the CA,
    by identity (thumbprint, SAN, common name, validity order) -- never by name alone. Ambiguous
    matches are never included here for deployment; they're reported separately for escalation."""
    matches, review = match_all()
    return {
        "matched": [
            {"binding_id": b, "sectigo_id": m["sectigo_id"], "old_thumbprint": m["old_thumbprint"],
             "new_thumbprint": m["new_thumbprint"]}
            for b, m in matches.items()
        ],
        "ambiguous_or_unresolved": [
            {"binding_id": b, "reason": r["reason"]} for b, r in review.items()
        ],
    }


def get_deployment_profile(binding_id: str) -> dict:
    """Looks up whether an approved deployment profile exists for a binding. No profile means the
    agent must not deploy -- it should escalate to a human instead (FR-STR-003)."""
    profile = _profiles_by_binding().get(binding_id)
    if not profile:
        return {"found": False}
    return {"found": True, "technology": profile["technology"], "zone": profile["zone"],
            "owner_group": profile.get("owner_group"), "status": profile.get("status")}


JOBS_PATH = ROOT / "jobs" / "agent_jobs.json"


def _fetch_bundle(sectigo_id):
    cfg = load_config()
    sectigo_cfg = cfg["sources"]["sectigo"]
    if sectigo_cfg.get("mode", "api") == "folder":
        from sources.folder_ca import get_bundle
        return get_bundle(sectigo_id, ROOT / sectigo_cfg.get("folder_path", "input_sectigo_certificates"))
    import json, urllib.request
    with urllib.request.urlopen(f"{sectigo_cfg['base_url']}/api/ssl/v1/bundle/{sectigo_id}", timeout=10) as resp:
        return json.load(resp)


def start_deployment_job(binding_id: str, sectigo_id: str, old_thumbprint: str, new_thumbprint: str, san: list) -> dict:
    """Opens a deployment job for one binding: looks up its profile and records the expected
    identity (old/new thumbprint, SAN) so the following step-by-step tools (precheck,
    backup_current_certificate, fetch_certificate_bundle, install_certificate,
    activate_certificate, verify_deployment) all operate on the same job. Call this once per
    binding before calling any of those. Fails if no approved profile exists -- escalate instead."""
    profile = _profiles_by_binding().get(binding_id)
    if not profile:
        return {"status": "error", "message": "No deployment profile for this binding -- do not proceed, escalate instead"}
    job_id = "AGENT-" + uuid.uuid4().hex[:10].upper()
    jobs = load_json(JOBS_PATH, {})
    jobs[binding_id] = {
        "job_id": job_id, "profile": profile, "technology": profile["technology"],
        "expected": {"old_thumbprint": old_thumbprint, "new_thumbprint": new_thumbprint, "san": san},
        "credential_references": {"deploy": profile["credential_alias"]},
        "sectigo_id": sectigo_id, "bundle": None, "steps_done": [],
    }
    save_json(JOBS_PATH, jobs)
    audit("agent.job.started", binding_id=binding_id, job_id=job_id)
    return {"job_id": job_id, "technology": profile["technology"]}


def _job(binding_id):
    jobs = load_json(JOBS_PATH, {})
    job = jobs.get(binding_id)
    if not job:
        raise RuntimeError("No open job for this binding -- call start_deployment_job first")
    return jobs, job


def _save_job(jobs, binding_id, job):
    jobs[binding_id] = job
    save_json(JOBS_PATH, jobs)


def precheck_deployment(binding_id: str) -> dict:
    """Checks the target is ready: reachable, the credential works, and -- critically -- that the
    server currently presents the thumbprint the CMDB expects (if it presents something else,
    something is already wrong and nothing should be changed)."""
    jobs, job = _job(binding_id)
    r = _run_adapter(job["technology"], "precheck", {"job_id": job["job_id"], "profile": job["profile"], "expected": job["expected"]})
    job["steps_done"].append(("precheck", r["status"]))
    _save_job(jobs, binding_id, job)
    return r


def backup_current_certificate(binding_id: str) -> dict:
    """Backs up the certificate and configuration currently on the target -- the rollback point --
    before anything is changed. Do this before install_certificate."""
    jobs, job = _job(binding_id)
    r = _run_adapter(job["technology"], "backup", {"job_id": job["job_id"], "profile": job["profile"], "expected": job["expected"]})
    job["steps_done"].append(("backup", r["status"]))
    _save_job(jobs, binding_id, job)
    return r


def fetch_certificate_bundle(binding_id: str) -> dict:
    """Fetches the actual certificate and private key for this job from the certificate source
    (Sectigo, or the input folder standing in for it). Needed before install_certificate."""
    jobs, job = _job(binding_id)
    job["bundle"] = _fetch_bundle(job["sectigo_id"])
    job["steps_done"].append(("fetch_bundle", "success"))
    _save_job(jobs, binding_id, job)
    return {"status": "success", "message": "certificate and key fetched (not shown -- handled internally, never exposed to you)"}


def install_certificate(binding_id: str) -> dict:
    """Installs the fetched certificate on the target (certificate store, keystore, or file,
    depending on technology). Requires fetch_certificate_bundle to have been called first."""
    jobs, job = _job(binding_id)
    if not job.get("bundle"):
        return {"status": "error", "message": "No certificate bundle fetched yet -- call fetch_certificate_bundle first"}
    req = {"job_id": job["job_id"], "profile": job["profile"], "expected": job["expected"], "bundle": job["bundle"]}
    r = _run_adapter(job["technology"], "install", req)
    job["steps_done"].append(("install", r["status"]))
    _save_job(jobs, binding_id, job)
    return r


def activate_certificate(binding_id: str) -> dict:
    """Activates the newly installed certificate (binding update, graceful reload, etc.) so it's
    actually used, without restarting the whole service where avoidable."""
    jobs, job = _job(binding_id)
    r = _run_adapter(job["technology"], "activate", {"job_id": job["job_id"], "profile": job["profile"], "expected": job["expected"]})
    job["steps_done"].append(("activate", r["status"]))
    _save_job(jobs, binding_id, job)
    return r


def verify_deployment(binding_id: str) -> dict:
    """Checks the live endpoint actually presents the new certificate. IMPORTANT: this step
    enforces its own safety net in code, not left to your judgement -- if verification fails, this
    function automatically rolls back to the backup and re-verifies before returning to you. You
    will never see a raw 'verify failed' with the old state left broken; you will see either
    'confirmed' or 'rolled_back', already handled."""
    jobs, job = _job(binding_id)
    req = {"job_id": job["job_id"], "profile": job["profile"], "expected": job["expected"]}
    r = _run_adapter(job["technology"], "verify", req)
    if r["status"] == "success":
        _set_binding_state(binding_id, state="Deployed, awaiting scan",
                            deployed_new_thumbprint=job["expected"]["new_thumbprint"], deployed_at=utcnow())
        job["steps_done"].append(("verify", "success"))
        _save_job(jobs, binding_id, job)
        audit("agent.deploy.success", binding_id=binding_id, job_id=job["job_id"])
        return {"status": "success", "state": "Deployed, awaiting scan", "evidence": r["evidence"]}

    # Verification failed -- this part is NOT the agent's decision. It happens unconditionally.
    audit("agent.deploy.verify_failed", binding_id=binding_id, job_id=job["job_id"], error=r.get("message"))
    rb = _run_adapter(job["technology"], "rollback", req)
    vr = _run_adapter(job["technology"], "verify", req)
    _set_binding_state(binding_id, state="Rolled back")
    job["steps_done"].append(("verify", "failed_rolled_back"))
    _save_job(jobs, binding_id, job)
    return {"status": "rolled_back", "error": r.get("message"), "rollback_verified": vr["status"] == "success"}


def cleanup_deployment(binding_id: str) -> dict:
    """Closes out the job: removes temporary files, clears credentials from memory. Always call
    this last, whether the job succeeded or rolled back."""
    jobs, job = _job(binding_id)
    req = {"job_id": job["job_id"], "profile": job["profile"], "expected": job["expected"]}
    r = _run_adapter(job["technology"], "cleanup", req)
    del jobs[binding_id]
    save_json(JOBS_PATH, jobs)
    return r


def check_confirmation(binding_id: str) -> dict:
    """Re-scans and checks whether the binding now independently shows the deployed thumbprint --
    the closed-loop proof that a deployment actually took effect, not just that the job said so."""
    scan_all()
    table = load_json(STATE_PATH, {})
    rec = table.get(binding_id, {})
    if rec.get("state") != "Deployed, awaiting scan":
        return {"applicable": False, "current_state": rec.get("state")}
    expected = rec.get("deployed_new_thumbprint")
    observed = rec.get("thumbprint")
    if observed == expected:
        rec["state"] = "Confirmed by discovery"
        rec["confirmed_at"] = utcnow()
        table[binding_id] = rec
        save_json(STATE_PATH, table)
        return {"applicable": True, "confirmed": True, "thumbprint": observed[:16] + "..."}
    return {"applicable": True, "confirmed": False, "observed": observed[:16] + "...", "expected": expected[:16] + "..."}


def escalate_to_human(binding_id: str, reason: str) -> dict:
    """The only correct move when something should NOT be automated: no profile, an ambiguous
    match, or a failure that shouldn't be retried blindly. Writes a reviewable record rather than
    silently doing nothing (FR-EXC-001, FR-MAT-002)."""
    review = load_json(CMDB_DIR / "agent_escalations.json", {})
    review[binding_id] = {"reason": reason, "escalated_at": utcnow()}
    save_json(CMDB_DIR / "agent_escalations.json", review)
    audit("agent.escalate", binding_id=binding_id, reason=reason)
    return {"status": "escalated", "binding_id": binding_id}


TOOLS = {
    "scan_cmdb": scan_cmdb,
    "check_new_certificates": check_new_certificates,
    "find_matches": find_matches,
    "get_deployment_profile": get_deployment_profile,
    "start_deployment_job": start_deployment_job,
    "precheck_deployment": precheck_deployment,
    "backup_current_certificate": backup_current_certificate,
    "fetch_certificate_bundle": fetch_certificate_bundle,
    "install_certificate": install_certificate,
    "activate_certificate": activate_certificate,
    "verify_deployment": verify_deployment,
    "cleanup_deployment": cleanup_deployment,
    "check_confirmation": check_confirmation,
    "escalate_to_human": escalate_to_human,
}


def _binding_arg(name="binding_id"):
    return {"type": "object", "properties": {name: {"type": "string"}}, "required": [name]}


# Anthropic-shaped tool-use schema for each function above (run_agent.py converts to OpenAI shape).
TOOL_SCHEMAS = [
    {"name": "scan_cmdb", "description": scan_cmdb.__doc__,
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "check_new_certificates", "description": check_new_certificates.__doc__,
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "find_matches", "description": find_matches.__doc__,
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_deployment_profile", "description": get_deployment_profile.__doc__,
     "input_schema": _binding_arg()},
    {"name": "start_deployment_job", "description": start_deployment_job.__doc__,
     "input_schema": {"type": "object", "properties": {
         "binding_id": {"type": "string"}, "sectigo_id": {"type": "string"},
         "old_thumbprint": {"type": "string"}, "new_thumbprint": {"type": "string"},
         "san": {"type": "array", "items": {"type": "string"}},
     }, "required": ["binding_id", "sectigo_id", "old_thumbprint", "new_thumbprint", "san"]}},
    {"name": "precheck_deployment", "description": precheck_deployment.__doc__, "input_schema": _binding_arg()},
    {"name": "backup_current_certificate", "description": backup_current_certificate.__doc__, "input_schema": _binding_arg()},
    {"name": "fetch_certificate_bundle", "description": fetch_certificate_bundle.__doc__, "input_schema": _binding_arg()},
    {"name": "install_certificate", "description": install_certificate.__doc__, "input_schema": _binding_arg()},
    {"name": "activate_certificate", "description": activate_certificate.__doc__, "input_schema": _binding_arg()},
    {"name": "verify_deployment", "description": verify_deployment.__doc__, "input_schema": _binding_arg()},
    {"name": "cleanup_deployment", "description": cleanup_deployment.__doc__, "input_schema": _binding_arg()},
    {"name": "check_confirmation", "description": check_confirmation.__doc__, "input_schema": _binding_arg()},
    {"name": "escalate_to_human", "description": escalate_to_human.__doc__,
     "input_schema": {"type": "object", "properties": {
         "binding_id": {"type": "string"}, "reason": {"type": "string"},
     }, "required": ["binding_id", "reason"]}},
]
