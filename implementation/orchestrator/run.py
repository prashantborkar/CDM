"""ORCHESTRATOR -- ties every stage in specification chapter 4 together. This is the local stand-in
for the ServiceNow scoped application (orchestration + lifecycle state machine, spec chapter 5.2);
the stage numbers in the comments below match section 4.2 of CDM_End_to_End_Specification.md exactly.

Commands:
  python orchestrator/run.py sync        stage 1 + 2: read the CMDB (discovery) and the CA landing area
  python orchestrator/run.py plan        stage 3 + 4: match, then plan one job per unique match with a profile
  python orchestrator/run.py deploy      stage 5-11: run every planned job through its adapter
  python orchestrator/run.py confirm     stage 12: rescan, then confirm any binding awaiting confirmation
  python orchestrator/run.py demo        sync + plan + deploy + confirm, one after another (the full loop)
  python orchestrator/run.py status      print the state of every binding
"""
import importlib
import json
import os
import sys
import time
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["PATH"] = os.environ.get("PATH", "") + r";C:\Program Files\Microsoft\jdk-17.0.19.10-hotspot\bin"

from common.util import load_json, save_json, audit, utcnow, parse_ts, load_config, CMDB_DIR  # noqa: E402
from discovery.discover import scan_all  # noqa: E402
from matcher.match import match_all  # noqa: E402

from common.sn_config import profiles_by_binding as _sn_profiles_by_binding  # noqa: E402

JOBS_LOG = ROOT / "jobs" / "job_log.json"
STATE_PATH = CMDB_DIR / "certificates.json"

ADAPTER_MODULES = {
    "windows_cert_store": "adapters.windows_cert_store.adapter",
    "java_keystore": "adapters.java_keystore.adapter",
    "linux_apache_ssh": "adapters.linux_apache.ssh_executor",
    # linux_apache runs on the real Linux host over SSH once it exists (adapters/linux_apache/adapter.sh);
    # there is no local Python module for it because there is nothing on this laptop to deploy to.
}


def profiles_by_binding():
    """Live from ServiceNow now -- see common/sn_config.py. No local deployment_profiles.json read."""
    return _sn_profiles_by_binding()


def cmd_sync():
    print("Stage 1: syncing ServiceNow CMDB (discovery simulator)...")
    cmdb = scan_all()
    for b, r in cmdb.items():
        print(f"  {b}: thumbprint {r['thumbprint'][:16]}...  valid_to {r['valid_to']}")
    print("Stage 2: syncing Sectigo landing area (CA simulator)...")
    from matcher.match import fetch_ca_list
    ca = fetch_ca_list()
    print(f"  {len(ca)} certificates visible at the CA")
    return cmdb, ca


def cmd_plan():
    print("Stage 3: matching...")
    matches, review = match_all()
    by_binding = profiles_by_binding()
    plan = []
    for binding_id, m in matches.items():
        profile = by_binding.get(binding_id)
        if not profile:
            audit("orchestrator.plan.no_profile", binding_id=binding_id)
            print(f"  {binding_id}: no deployment profile -> manual task (FR-EXC-001)")
            continue
        job_id = "JOB-" + uuid.uuid4().hex[:10].upper()
        plan.append({"job_id": job_id, "binding_id": binding_id, "profile_id": profile["_profile_id"],
                      "sectigo_id": m["sectigo_id"], "old_thumbprint": m["old_thumbprint"],
                      "new_thumbprint": m["new_thumbprint"], "san": m["san"]})
        print(f"  {binding_id}: planned {job_id} (profile {profile['_profile_id']}, "
              f"{m['old_thumbprint'][:10]}... -> {m['new_thumbprint'][:10]}...)")
    if review:
        print(f"  {len(review)} binding(s) sent to the review queue (ambiguous or unlocated) -- see cmdb/review_queue.json")
    save_json(ROOT / "jobs" / "plan.json", plan)
    audit("orchestrator.plan", planned=len(plan), review=len(review))
    return plan


def _fetch_bundle(cfg, sectigo_id):
    sectigo_cfg = cfg["sources"]["sectigo"]
    if sectigo_cfg.get("mode", "api") == "folder":
        from sources.folder_ca import get_bundle
        return get_bundle(sectigo_id, ROOT / sectigo_cfg.get("folder_path", "input_sectigo_certificates"))
    if sectigo_cfg.get("mode") == "acme":
        from sources.acme_ca import get_bundle
        return get_bundle(sectigo_id, sectigo_cfg.get("acme_domains", []))
    base = sectigo_cfg["base_url"]
    with urllib.request.urlopen(f"{base}/api/ssl/v1/bundle/{sectigo_id}", timeout=10) as resp:
        return json.load(resp)


def _run_adapter(technology, operation, request):
    module = importlib.import_module(ADAPTER_MODULES[technology])
    return module.run(operation, request)


def _set_binding_state(binding_id, **fields):
    table = load_json(STATE_PATH, {})
    rec = table.get(binding_id, {})
    rec.update(fields)
    table[binding_id] = rec
    save_json(STATE_PATH, table)


def cmd_deploy():
    cfg = load_config()
    plan = load_json(ROOT / "jobs" / "plan.json", [])
    by_binding = profiles_by_binding()
    if not plan:
        print("Nothing planned. Run 'plan' first.")
        return
    results = load_json(JOBS_LOG, [])

    for item in plan:
        binding_id = item["binding_id"]
        profile = by_binding[binding_id]
        technology = profile["technology"]
        job_id = item["job_id"]
        print(f"\nStage 5-11: deploying {job_id} for {binding_id} ({technology})")

        if technology not in ADAPTER_MODULES:
            print(f"  No local executor for '{technology}' on this laptop -> manual/deferred "
                  f"(run adapters/linux_apache/adapter.sh over SSH once the Linux host exists).")
            audit("orchestrator.deploy.no_local_executor", job_id=job_id, technology=technology)
            _set_binding_state(binding_id, state="No local executor (deferred)")
            continue

        req = {
            "job_id": job_id,
            "profile": profile,
            "expected": {"old_thumbprint": item["old_thumbprint"], "new_thumbprint": item["new_thumbprint"],
                         "san": item["san"]},
            "credential_references": {"deploy": profile["credential_alias"]},
        }

        step_result = {"job_id": job_id, "binding_id": binding_id, "started": utcnow()}
        try:
            for op in ("precheck", "backup"):
                r = _run_adapter(technology, op, req)
                print(f"  {op}: {r['status']}")
                if r["status"] != "success":
                    raise RuntimeError(f"{op} failed: {r.get('message')}")

            print("  fetching certificate + private key bundle from the CA (stage 7)...")
            req["bundle"] = _fetch_bundle(cfg, item["sectigo_id"])
            audit("orchestrator.bundle_fetched", job_id=job_id, sectigo_id=item["sectigo_id"],
                  download_count=req["bundle"].get("download_count"))

            for op in ("install", "activate"):
                r = _run_adapter(technology, op, req)
                print(f"  {op}: {r['status']}")
                if r["status"] != "success":
                    raise RuntimeError(f"{op} failed: {r.get('message')}")

            r = _run_adapter(technology, "verify", req)
            print(f"  verify: {r['status']}")
            if r["status"] != "success":
                raise RuntimeError(f"verify failed: {r.get('message')}")

            step_result.update({"status": "Deployed, awaiting scan", "ended": utcnow(),
                                 "evidence": r["evidence"]})
            _set_binding_state(binding_id, state="Deployed, awaiting scan",
                                deployed_new_thumbprint=item["new_thumbprint"], deployed_at=utcnow())
            print(f"  RESULT: success -> state 'Deployed, awaiting scan'")

        except Exception as exc:
            print(f"  FAILURE: {exc}. Rolling back...")
            audit("orchestrator.deploy.failed", job_id=job_id, error=str(exc))
            rb = _run_adapter(technology, "rollback", req)
            print(f"  rollback: {rb['status']}")
            vr = _run_adapter(technology, "verify", req)
            step_result.update({"status": "Rolled back", "ended": utcnow(), "error": str(exc),
                                 "rollback_verified": vr["status"] == "success"})
            _set_binding_state(binding_id, state="Rolled back")
            print(f"  RESULT: rolled back (verified: {vr['status'] == 'success'})")

        finally:
            cr = _run_adapter(technology, "cleanup", req)
            print(f"  cleanup: {cr['status']}  (temp files removed: {cr.get('cleanup', {}).get('temp_files_removed')})")

        results.append(step_result)

    save_json(JOBS_LOG, results)
    save_json(ROOT / "jobs" / "plan.json", [])  # planned jobs are consumed once dispatched


def cmd_confirm():
    cfg = load_config()
    timeout_hours = cfg.get("verification", {}).get("confirm_timeout_hours", 36)
    print("Stage 12: rescanning (simulates the next day's Discovery scan)...")
    scan_all()
    table = load_json(STATE_PATH, {})
    for binding_id, rec in table.items():
        if rec.get("state") != "Deployed, awaiting scan":
            continue
        expected = rec.get("deployed_new_thumbprint")
        observed = rec.get("thumbprint")
        deployed_at = rec.get("deployed_at")
        last_scanned = rec.get("last_scanned")
        if observed == expected and deployed_at and last_scanned and parse_ts(last_scanned) > parse_ts(deployed_at):
            rec["state"] = "Confirmed by discovery"
            rec["confirmed_at"] = utcnow()
            print(f"  {binding_id}: CONFIRMED BY DISCOVERY (thumbprint {observed[:16]}...)")
            audit("orchestrator.confirmed", binding_id=binding_id, thumbprint=observed)
        elif observed != expected:
            hours_since = (parse_ts(utcnow()) - parse_ts(deployed_at)).total_seconds() / 3600 if deployed_at else 0
            if hours_since > timeout_hours:
                rec["state"] = "ALERT: not confirmed within timeout"
                audit("orchestrator.confirm.timeout", binding_id=binding_id, hours_since=hours_since)
                print(f"  {binding_id}: ALERT -- still not confirmed after {hours_since:.1f}h")
            else:
                print(f"  {binding_id}: not yet confirmed (scan still shows the deployment as pending)")
    save_json(STATE_PATH, table)


def cmd_status():
    table = load_json(STATE_PATH, {})
    if not table:
        print("No bindings known yet. Run 'sync' first.")
        return
    for binding_id, rec in table.items():
        print(f"{binding_id}")
        print(f"  state:        {rec.get('state')}")
        print(f"  thumbprint:   {rec.get('thumbprint')}")
        print(f"  valid_to:     {rec.get('valid_to')}")
        print(f"  last_scanned: {rec.get('last_scanned')}")


def cmd_demo():
    cmd_sync()
    print()
    cmd_plan()
    print()
    cmd_deploy()
    print()
    print("--- simulating the passage of a day before the next Discovery scan ---")
    time.sleep(1)
    cmd_confirm()
    print()
    cmd_status()


COMMANDS = {"sync": cmd_sync, "plan": cmd_plan, "deploy": cmd_deploy, "confirm": cmd_confirm,
            "status": cmd_status, "demo": cmd_demo}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: python orchestrator/run.py [{'|'.join(COMMANDS)}]")
        sys.exit(1)
    COMMANDS[sys.argv[1]]()
