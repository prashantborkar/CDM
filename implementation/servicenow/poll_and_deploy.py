"""The ServiceNow-driven trigger loop: ServiceNow decides (by a record's State being set to
"Deploy Requested"), this script -- acting as the agent on the MID Server's host -- notices,
executes the real local deployment (same adapters, same certificate+key bundle fetch as
orchestrator/run.py), and reports the result back to ServiceNow.

This is NOT the internal MID Server ECC Queue/probe protocol (that binary protocol is undocumented
to us and too risky to hand-guess, especially with Orchestration not installed on this instance --
confirmed by checking for sn_orchestration_activity, which does not exist here). It achieves the
same practical outcome -- ServiceNow triggers, a laptop-side agent executes, results flow back --
over the Table API we already have working. If/when Orchestration becomes available, this script's
role could be replaced by a real MID Server probe without changing anything else in the system:
the adapters, the matching, the vault -- all of it stays exactly the same either way.

Run once (process every currently-requested binding, then exit):
    python servicenow/poll_and_deploy.py --once

Run continuously (checks every 15 seconds until Ctrl+C):
    python servicenow/poll_and_deploy.py
"""
import importlib
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import os
os.environ["PATH"] = os.environ.get("PATH", "") + r";C:\Program Files\Microsoft\jdk-17.0.19.10-hotspot\bin"

from common.util import load_json, load_config, audit, utcnow  # noqa: E402
from common.sn_config import profiles_by_binding as _sn_profiles_by_binding  # noqa: E402
from servicenow.sn_client import ServiceNowClient  # noqa: E402
from servicenow.sync_cmdb_to_sn import to_sn_datetime  # noqa: E402

TABLE = "u_x_2182912_certif_0_certificate"
REQUEST_STATE = "Deploy Requested"

ADAPTER_MODULES = {
    "windows_cert_store": "adapters.windows_cert_store.adapter",
    "java_keystore": "adapters.java_keystore.adapter",
    "linux_apache_ssh": "adapters.linux_apache.ssh_executor",
}


def profiles_by_binding():
    """Live from ServiceNow now -- see common/sn_config.py. No local deployment_profiles.json read."""
    return _sn_profiles_by_binding()


def local_match_for(binding_id):
    matches = load_json(ROOT / "cmdb" / "matches.json", {})
    return matches.get(binding_id)


def fetch_bundle(sectigo_id):
    cfg = load_config()
    sectigo_cfg = cfg["sources"]["sectigo"]
    if sectigo_cfg.get("mode", "api") == "folder":
        from sources.folder_ca import get_bundle
        return get_bundle(sectigo_id, ROOT / sectigo_cfg.get("folder_path", "input_sectigo_certificates"))
    base = sectigo_cfg["base_url"]
    import json
    with urllib.request.urlopen(f"{base}/api/ssl/v1/bundle/{sectigo_id}", timeout=10) as resp:
        return json.load(resp)


def run_adapter(technology, operation, request):
    module = importlib.import_module(ADAPTER_MODULES[technology])
    return module.run(operation, request)


def process_one(sn, sn_record, profiles):
    binding_id = sn_record["u_binding_id"]
    print(f"\n[{utcnow()}] ServiceNow requested deployment for: {binding_id}")
    audit("sn_trigger.deploy_requested", binding_id=binding_id, sn_sys_id=sn_record["sys_id"])

    profile = profiles.get(binding_id)
    match = local_match_for(binding_id)
    if not profile or not match:
        print("  no local profile/match available for this binding -- run 'python orchestrator/run.py sync' "
              "and 'plan' first so there is something to deploy. Marking as failed in ServiceNow.")
        sn.call("PATCH", f"/api/now/table/{TABLE}/{sn_record['sys_id']}", {"u_state": "No profile / not matched"})
        return

    technology = profile["technology"]
    job_id = "SNJOB-" + sn_record["sys_id"][:10].upper()
    req = {
        "job_id": job_id,
        "profile": profile,
        "expected": {"old_thumbprint": match["old_thumbprint"], "new_thumbprint": match["new_thumbprint"],
                     "san": match["san"]},
        "credential_references": {"deploy": profile["credential_alias"]},
    }

    try:
        for op in ("precheck", "backup"):
            r = run_adapter(technology, op, req)
            print(f"  {op}: {r['status']}")
            if r["status"] != "success":
                raise RuntimeError(f"{op}: {r.get('message')}")

        print("  fetching certificate + private key bundle from the CA...")
        req["bundle"] = fetch_bundle(match["sectigo_id"])

        for op in ("install", "activate"):
            r = run_adapter(technology, op, req)
            print(f"  {op}: {r['status']}")
            if r["status"] != "success":
                raise RuntimeError(f"{op}: {r.get('message')}")

        r = run_adapter(technology, "verify", req)
        print(f"  verify: {r['status']}")
        if r["status"] != "success":
            raise RuntimeError(f"verify: {r.get('message')}")

        sn.call("PATCH", f"/api/now/table/{TABLE}/{sn_record['sys_id']}", {
            "u_state": "Deployed, awaiting scan",
            "u_deployed_new_thumbprint": match["new_thumbprint"],
            "u_deployed_at": to_sn_datetime(utcnow()),
        })
        print(f"  RESULT: success. ServiceNow record updated -> 'Deployed, awaiting scan'.")
        audit("sn_trigger.deploy_success", binding_id=binding_id, job_id=job_id)

    except Exception as exc:
        print(f"  FAILURE: {exc}. Rolling back...")
        audit("sn_trigger.deploy_failed", binding_id=binding_id, job_id=job_id, error=str(exc))
        run_adapter(technology, "rollback", req)
        run_adapter(technology, "verify", req)
        sn.call("PATCH", f"/api/now/table/{TABLE}/{sn_record['sys_id']}", {"u_state": "Rolled back"})
        print("  ServiceNow record updated -> 'Rolled back'.")
    finally:
        run_adapter(technology, "cleanup", req)


def poll_once():
    sn = ServiceNowClient()
    profiles = profiles_by_binding()
    status, body = sn.query(TABLE, f"u_state={REQUEST_STATE}", fields="sys_id,u_binding_id,u_state", limit=20)
    if status != 200:
        print("Failed to query ServiceNow:", status, body)
        return
    requested = body.get("result", [])
    if not requested:
        print(f"[{utcnow()}] No bindings with State='{REQUEST_STATE}' right now.")
        return
    for rec in requested:
        process_one(sn, rec, profiles)


if __name__ == "__main__":
    if "--once" in sys.argv:
        poll_once()
    else:
        print("Polling ServiceNow every 15 seconds for State='Deploy Requested'. Ctrl+C to stop.")
        while True:
            poll_once()
            time.sleep(15)
