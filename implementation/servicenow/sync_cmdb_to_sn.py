"""Pushes implementation/cmdb/certificates.json (produced by discovery/discover.py and updated by
orchestrator/run.py) into the real ServiceNow table, upserting by binding_id.

This is the first real bridge between the local implementation and the live instance: everything
that discovery, matching, deployment and confirmation already do locally now becomes visible in
ServiceNow too. Run it any time after `python orchestrator/run.py demo` (or any individual stage)
to reflect the current local state into ServiceNow.

Run:  python servicenow/sync_cmdb_to_sn.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.util import load_json, CMDB_DIR  # noqa: E402
from servicenow.sn_client import ServiceNowClient  # noqa: E402

TABLE = "u_x_2182912_certif_0_certificate"

FIELD_MAP = {
    "binding_id": "u_binding_id", "server": "u_server", "certificate_name": "u_certificate_name",
    "thumbprint": "u_thumbprint", "serial": "u_serial", "state": "u_state",
    "deployed_new_thumbprint": "u_deployed_new_thumbprint",
}
DATE_FIELD_MAP = {
    "valid_from": "u_valid_from", "valid_to": "u_valid_to", "last_scanned": "u_last_scanned",
    "deployed_at": "u_deployed_at", "confirmed_at": "u_confirmed_at",
}


def to_sn_datetime(iso_ts):
    """ServiceNow glide_date_time wants 'YYYY-MM-DD HH:MM:SS'; our records are ISO-8601 UTC."""
    if not iso_ts:
        return None
    return iso_ts.replace("T", " ").split("+")[0].split(".")[0]


def to_sn_record(rec: dict) -> dict:
    out = {}
    for k, sn_field in FIELD_MAP.items():
        if rec.get(k):
            v = rec[k]
            out[sn_field] = ",".join(v) if isinstance(v, list) else v
    for k, sn_field in DATE_FIELD_MAP.items():
        ts = to_sn_datetime(rec.get(k))
        if ts:
            out[sn_field] = ts
    if isinstance(rec.get("san"), list):
        out["u_san"] = ",".join(rec["san"])
    return out


def sync():
    sn = ServiceNowClient()
    certs = load_json(CMDB_DIR / "certificates.json", {})
    if not certs:
        print("No local certificate records found. Run 'python orchestrator/run.py sync' (or 'demo') first.")
        return

    for binding_id, rec in certs.items():
        fields = to_sn_record(rec)
        existing_id = sn.find_one(TABLE, f"u_binding_id={binding_id}")
        if existing_id:
            status, body = sn.call("PATCH", f"/api/now/table/{TABLE}/{existing_id}", fields)
            action = "updated"
        else:
            status, body = sn.insert(TABLE, fields)
            action = "created"
        ok = status in (200, 201)
        print(f"{binding_id}: {action} -> {status}{' OK' if ok else ' FAILED: ' + str(body)}")


if __name__ == "__main__":
    sync()
