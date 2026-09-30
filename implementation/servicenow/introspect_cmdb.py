"""Read-only introspection of a ServiceNow instance's CMDB -- run this FIRST when onboarding CDM
against any organization's real instance, before assuming anything about their table structure.

Answers two questions:
  1. What CI tables represent real servers, and are they actually populated (by real Discovery,
     not empty demo data)?
  2. Does anything resembling certificate/SSL data already exist anywhere, so CDM doesn't create
     a duplicate certificate table next to one that's already there?

Makes no writes. Safe to run against any instance CDM has read access to.

Run:  python servicenow/introspect_cmdb.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sn_client import ServiceNowClient

# Base + common subclasses. A real org may have others (network gear, load balancers, etc.) --
# this list is a starting point, not exhaustive; sys_db_object's own hierarchy (queried below)
# is the authoritative answer for a given instance.
SERVER_CI_TABLES = [
    "cmdb_ci_server", "cmdb_ci_linux_server", "cmdb_ci_win_server",
    "cmdb_ci_unix_server", "cmdb_ci_app_server",
]


def check_table_populated(sn, table, fields):
    status, body = sn.query(table, "", fields=fields, limit=5)
    if status == 404:
        return None  # table doesn't exist on this instance
    if status != 200:
        return {"error": f"{status} {body}"}
    return body.get("result", [])


def find_cert_related_tables(sn):
    status, body = sn.query("sys_db_object", "nameLIKEcert^ORnameLIKEssl^ORnameLIKEx509",
                             fields="name,label,super_class", limit=50)
    if status != 200:
        return []
    return body["result"]


def find_ssl_discovery_sensors(sn):
    # ServiceNow's Discovery ships SSL-related sensors/probes on some plugin combinations
    # (ITOM Discovery + Service Graph Connectors). Their presence indicates certificate data
    # may already be flowing in via Discovery itself, not just CI tables.
    status, body = sn.query("sys_script_probe" if False else "sys_db_object",
                             "nameLIKEssl^ORnameLIKEcertificate", fields="name,label", limit=20)
    return body.get("result", []) if status == 200 else []


def main():
    sn = ServiceNowClient()
    print(f"Introspecting: {sn.instance}\n")

    print("=" * 70)
    print("1. SERVER CI TABLES -- is Discovery actually populating these?")
    print("=" * 70)
    any_populated = False
    for table in SERVER_CI_TABLES:
        rows = check_table_populated(sn, table, "name,ip_address,sys_class_name,discovery_source")
        if rows is None:
            print(f"  {table:28s} -- not present on this instance")
        elif isinstance(rows, dict) and "error" in rows:
            print(f"  {table:28s} -- ERROR: {rows['error']}")
        elif len(rows) == 0:
            print(f"  {table:28s} -- exists, but EMPTY (Discovery not populating it, or no read access)")
        else:
            any_populated = True
            print(f"  {table:28s} -- {len(rows)}+ record(s) found, sample:")
            for r in rows[:3]:
                print(f"      {r.get('name', '?'):30s} ip={r.get('ip_address', '?'):16s} "
                      f"class={r.get('sys_class_name', '?')} source={r.get('discovery_source', '?')}")
    if not any_populated:
        print("\n  NONE of the standard server CI tables have data visible to this account.")
        print("  Either Discovery hasn't run yet, this account lacks read ACLs on cmdb_ci*, or")
        print("  this org uses non-standard CI tables -- check with their CMDB admin.")

    print("\n" + "=" * 70)
    print("2. CERTIFICATE / SSL -- does anything like this already exist?")
    print("=" * 70)
    cert_tables = find_cert_related_tables(sn)
    if not cert_tables:
        print("  No table names matching 'cert', 'ssl', or 'x509' found.")
        print("  -> Safe to introduce CDM's own certificate table; nothing to collide with.")
    else:
        print(f"  {len(cert_tables)} table(s) found with cert/ssl-like names:")
        for t in cert_tables:
            print(f"    {t['name']:40s} label='{t.get('label', '')}'  extends='{t.get('super_class', '')}'")
        print("\n  -> Check these before creating a new table -- one of them may already be")
        print("     what Discovery (or a security tool integration) populates certificate data into.")

    print("\n" + "=" * 70)
    print("DONE. Use this output to decide: point CDM's discovery at an existing CI table")
    print("(recommended if populated) vs. standing up CDM's own (only if nothing fits).")
    print("=" * 70)


if __name__ == "__main__":
    main()
