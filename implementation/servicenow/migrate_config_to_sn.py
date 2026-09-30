"""One-time migration: pushes the current local discovery.SITES list and deployment_profiles.json
into the two ServiceNow tables setup_dynamic_config_tables.py created. After this runs,
common/sn_config.py reads live from ServiceNow -- these local values stop being the source of
truth; this script exists only to seed ServiceNow with what used to live in these files.

Run:  python servicenow/migrate_config_to_sn.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.util import load_json  # noqa: E402
from servicenow.sn_client import ServiceNowClient  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SITE_TABLE = "u_x_2182912_certif_0_monitored_site"
PROFILE_TABLE = "u_x_2182912_certif_0_deploy_profile"

# The SITES list, as it stood in discovery/discover.py before this migration.
SITES = [
    {"binding_id": "lab-win:web01.lab.example.com", "server": "lab-win",
     "host": "127.0.0.1", "port": 8443, "sni": "web01.lab.example.com"},
    {"binding_id": "lab-lnx:api.lab.example.com", "server": "lab-lnx",
     "host": "127.0.0.1", "port": 8445, "sni": "api.lab.example.com"},
    {"binding_id": "ec2-lnx:linuxtest.lab.example.com", "server": "ec2-lnx",
     "host": "16.16.120.70", "port": 443, "sni": "linuxtest.lab.example.com"},
    {"binding_id": "ec2-lnx:16-16-120-70.nip.io", "server": "ec2-lnx",
     "host": "16.16.120.70", "port": 443, "sni": "16-16-120-70.nip.io"},
]


def migrate_sites(sn):
    print("Migrating monitored sites...")
    for site in SITES:
        fields = {"u_binding_id": site["binding_id"], "u_server": site["server"],
                  "u_host": site["host"], "u_port": str(site["port"]), "u_sni": site["sni"], "u_active": "true"}
        existing = sn.find_one(SITE_TABLE, f"u_binding_id={site['binding_id']}")
        if existing:
            status, body = sn.call("PATCH", f"/api/now/table/{SITE_TABLE}/{existing}", fields)
            action = "updated"
        else:
            status, body = sn.insert(SITE_TABLE, fields)
            action = "created"
        print(f"  {site['binding_id']}: {action} -> {status}")


def migrate_profiles(sn):
    print("\nMigrating deployment profiles...")
    profiles = load_json(ROOT / "config" / "deployment_profiles.json", {})
    for profile_id, p in profiles.items():
        if "binding_id" not in p:
            continue
        # Everything technology-specific (linux/windows/java blocks, activation, verification,
        # san, adapter) travels as one JSON blob -- avoids needing dozens of narrow columns for
        # config that's genuinely nested and varies per technology.
        rest = {k: v for k, v in p.items() if k not in
                ("binding_id", "status", "technology", "credential_alias", "owner_group")}
        fields = {
            "u_binding_id": p["binding_id"], "u_profile_id": profile_id,
            "u_status": p.get("status", "approved"), "u_technology": p["technology"],
            "u_credential_alias": p["credential_alias"], "u_owner_group": p.get("owner_group", ""),
            "u_config_json": json.dumps(rest),
        }
        existing = sn.find_one(PROFILE_TABLE, f"u_profile_id={profile_id}")
        if existing:
            status, body = sn.call("PATCH", f"/api/now/table/{PROFILE_TABLE}/{existing}", fields)
            action = "updated"
        else:
            status, body = sn.insert(PROFILE_TABLE, fields)
            action = "created"
        print(f"  {profile_id} ({p['binding_id']}): {action} -> {status}")


if __name__ == "__main__":
    sn = ServiceNowClient()
    migrate_sites(sn)
    migrate_profiles(sn)
    print("\nDone. discovery/discover.py and orchestrator/run.py will be switched to read these tables live.")
