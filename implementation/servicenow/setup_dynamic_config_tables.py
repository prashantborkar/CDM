"""Creates the two ServiceNow tables that replace local hardcoded config:

  x_2182912_certif_0_monitored_site   -- replaces discovery/discover.py's SITES list
  x_2182912_certif_0_deploy_profile   -- replaces config/deployment_profiles.json

Both land in Global scope with a u_ prefix, same as the certificate table (see sn_client.py's
docstring for why -- this is a confirmed platform behavior, not a bug). This script only CREATES
these two new tables; it never touches u_x_2182912_certif_0_certificate, so it is safe to run
against the shared instance.

Run:  python servicenow/setup_dynamic_config_tables.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sn_client import ServiceNowClient

TABLES = {
    "x_2182912_certif_0_monitored_site": [
        ("binding_id", "Binding ID", "string", 200),
        ("server", "Server", "string", 100),
        ("host", "Host", "string", 200),
        ("port", "Port", "integer", None),
        ("sni", "SNI", "string", 200),
        ("active", "Active", "boolean", None),
    ],
    "x_2182912_certif_0_deploy_profile": [
        ("binding_id", "Binding ID", "string", 200),
        ("profile_id", "Profile ID", "string", 100),
        ("status", "Status", "string", 30),
        ("technology", "Technology", "string", 60),
        ("credential_alias", "Credential Alias", "string", 200),
        ("owner_group", "Owner Group", "string", 100),
        ("config_json", "Config JSON", "string", 4000),
    ],
}


def cleanup_duplicates(sn, name):
    for n in (name, f"u_{name}"):
        sys_id = sn.find_one("sys_db_object", f"name={n}")
        if sys_id:
            status, _ = sn.delete("sys_db_object", sys_id)
            print(f"  removed existing table {n} ({sys_id}): delete status {status}")


def create_table(sn, name, columns):
    print(f"\nCreating table {name}...")
    cleanup_duplicates(sn, name)
    status, body = sn.insert("sys_db_object", {
        "name": name, "label": name.split("_")[-1].replace("_", " ").title(),
        "is_extendable": "false", "access": "public",
    })
    if status != 201:
        print("FAILED:", status, body)
        return None
    real_name = body["result"]["name"]
    print(f"  created as: {real_name}")

    for element, label, internal_type, max_length in columns:
        fields = {"name": real_name, "element": element, "column_label": label, "internal_type": internal_type}
        if max_length:
            fields["max_length"] = str(max_length)
        status, body = sn.insert("sys_dictionary", fields)
        print(f"  {element:20s} {internal_type:10s} -> {'ok' if status == 201 else 'FAILED ' + str(status)}")
    return real_name


def main():
    sn = ServiceNowClient()
    real_names = {}
    for name, columns in TABLES.items():
        real_names[name] = create_table(sn, name, columns)
    print("\nDone. Real table names:")
    for logical, real in real_names.items():
        print(f"  {logical} -> {real}")


if __name__ == "__main__":
    main()
