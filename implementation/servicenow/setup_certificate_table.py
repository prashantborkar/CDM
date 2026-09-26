"""Creates the real Certificate table in ServiceNow via the Table API, matching exactly what
discovery/discover.py already produces locally (see cmdb/certificates.json), so the orchestrator
can later be pointed at this table instead of the local JSON file with no other changes.

Lands in Global scope with a u_ prefix (see sn_client.py docstring for why). Fully functional table,
just not bundled inside the CDM app scope.

Run:  python servicenow/setup_certificate_table.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sn_client import ServiceNowClient

TABLE_NAME = "x_2182912_certif_0_certificate"  # ServiceNow will rename this to u_<name> -- see below

COLUMNS = [
    ("binding_id", "Binding ID", "string", 200),
    ("server", "Server", "string", 100),
    ("certificate_name", "Certificate Name", "string", 200),
    ("thumbprint", "Thumbprint", "string", 100),
    ("serial", "Serial", "string", 100),
    ("san", "SAN", "string", 1000),
    ("valid_from", "Valid From", "glide_date_time", None),
    ("valid_to", "Valid To", "glide_date_time", None),
    ("last_scanned", "Last Scanned", "glide_date_time", None),
    ("state", "State", "string", 60),
    ("deployed_new_thumbprint", "Deployed New Thumbprint", "string", 100),
    ("deployed_at", "Deployed At", "glide_date_time", None),
    ("confirmed_at", "Confirmed At", "glide_date_time", None),
]


def cleanup_duplicates(sn):
    for name in (TABLE_NAME, f"u_{TABLE_NAME}"):
        sys_id = sn.find_one("sys_db_object", f"name={name}")
        if sys_id:
            status, _ = sn.delete("sys_db_object", sys_id)
            print(f"  removed existing table {name} ({sys_id}): delete status {status}")


def main():
    sn = ServiceNowClient()

    print("Cleaning up any earlier test tables...")
    cleanup_duplicates(sn)

    print(f"\nCreating table {TABLE_NAME}...")
    status, body = sn.insert("sys_db_object", {
        "name": TABLE_NAME, "label": "Certificate", "is_extendable": "false", "access": "public",
    })
    if status != 201:
        print("FAILED:", status, body)
        return
    real_name = body["result"]["name"]
    table_sys_id = body["result"]["sys_id"]
    print(f"  created as: {real_name}  (sys_id {table_sys_id})")

    print("\nAdding columns...")
    for element, label, internal_type, max_length in COLUMNS:
        fields = {"name": real_name, "element": element, "column_label": label, "internal_type": internal_type}
        if max_length:
            fields["max_length"] = str(max_length)
        status, body = sn.insert("sys_dictionary", fields)
        ok = status == 201
        print(f"  {element:28s} {label:26s} {internal_type:16s} -> {'ok' if ok else 'FAILED ' + str(status)}")
        if not ok:
            print("    ", body)

    print("\nVerifying...")
    status, body = sn.query("sys_dictionary", f"name={real_name}", fields="element,column_label,internal_type", limit=30)
    cols = [r for r in body["result"] if r["element"]] if status == 200 else []
    print(f"  {len(cols)} columns confirmed on {real_name}")
    for c in cols:
        print(f"    {c['element']}")

    print(f"\nDone. Table API path: /api/now/table/{real_name}")


if __name__ == "__main__":
    main()
