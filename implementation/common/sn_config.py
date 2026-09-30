"""Live configuration, read from ServiceNow -- not from local files.

Replaces two things that used to be hardcoded on this one laptop:
  - discovery/discover.py's SITES list      -> u_x_2182912_certif_0_monitored_site
  - config/deployment_profiles.json          -> u_x_2182912_certif_0_deploy_profile

Every caller gets a fresh read from the real ServiceNow instance each time these functions are
called -- add a server or change a profile in ServiceNow and the next run picks it up, with no
code change and no file edit on this machine. See servicenow/setup_dynamic_config_tables.py for
how the tables were created and servicenow/migrate_config_to_sn.py for how they were seeded.

The one thing deliberately NOT moved here: the vault credential itself. That still comes from
vault_stub/ (standing in for CyberArk) -- secrets belong in a vault, never in ServiceNow, real or
otherwise. Only the *alias* naming which credential to use travels through these tables.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from servicenow.sn_client import ServiceNowClient  # noqa: E402

SITE_TABLE = "u_x_2182912_certif_0_monitored_site"
PROFILE_TABLE = "u_x_2182912_certif_0_deploy_profile"


def get_monitored_sites() -> list:
    """Live-reads the servers Discovery should scan. Returns the same shape discover.py's old
    hardcoded SITES list used: [{binding_id, server, host, port, sni}, ...]."""
    sn = ServiceNowClient()
    status, body = sn.query(SITE_TABLE, "u_active=true",
                             fields="u_binding_id,u_server,u_host,u_port,u_sni", limit=200)
    if status != 200:
        raise RuntimeError(f"Could not read monitored sites from ServiceNow: {status} {body}")
    return [{
        "binding_id": r["u_binding_id"], "server": r["u_server"],
        "host": r["u_host"], "port": int(r["u_port"]), "sni": r["u_sni"],
    } for r in body["result"]]


def get_deployment_profiles() -> dict:
    """Live-reads every approved deployment profile. Returns the same shape
    config/deployment_profiles.json used to: {profile_id: {binding_id, status, technology,
    credential_alias, owner_group, ...technology-specific fields}}."""
    sn = ServiceNowClient()
    status, body = sn.query(PROFILE_TABLE, "",
                             fields="u_profile_id,u_binding_id,u_status,u_technology,"
                                    "u_credential_alias,u_owner_group,u_config_json", limit=200)
    if status != 200:
        raise RuntimeError(f"Could not read deployment profiles from ServiceNow: {status} {body}")
    profiles = {}
    for r in body["result"]:
        rest = json.loads(r["u_config_json"]) if r.get("u_config_json") else {}
        profiles[r["u_profile_id"]] = {
            "binding_id": r["u_binding_id"], "status": r["u_status"], "technology": r["u_technology"],
            "credential_alias": r["u_credential_alias"], "owner_group": r.get("u_owner_group", ""),
            **rest,
        }
    return profiles


def profiles_by_binding() -> dict:
    """Same shape orchestrator.run.profiles_by_binding()/agent.tools._profiles_by_binding() used
    to build from the local file: {binding_id: {...profile, _profile_id}}."""
    profiles = get_deployment_profiles()
    return {p["binding_id"]: {**p, "_profile_id": pid} for pid, p in profiles.items() if "binding_id" in p}


if __name__ == "__main__":
    sites = get_monitored_sites()
    print(f"{len(sites)} monitored site(s) from ServiceNow:")
    for s in sites:
        print(f"  {s['binding_id']}  ({s['host']}:{s['port']}, sni={s['sni']})")

    profiles = get_deployment_profiles()
    print(f"\n{len(profiles)} deployment profile(s) from ServiceNow:")
    for pid, p in profiles.items():
        print(f"  {pid}: {p['binding_id']}  technology={p['technology']}  status={p['status']}")
