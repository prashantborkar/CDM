"""DISCOVERY -- stands in for ServiceNow Discovery's certificate scan (spec section 14.2). Reads
the list of servers to scan live from ServiceNow (u_x_2182912_certif_0_monitored_site, via
common/sn_config.py), then really connects to each one and reads what certificate it presents,
the same way a network-based certificate scan would.

The list of servers to scan is no longer hardcoded here -- it used to be a fixed SITES list in
this file; that has been replaced by a live ServiceNow table so adding/removing a monitored
server is a ServiceNow record, not a code change on this machine (see
servicenow/setup_dynamic_config_tables.py and servicenow/migrate_config_to_sn.py for how that
table was created and seeded).

What's still local: cmdb/certificates.json, the CURRENT SCAN RESULTS (thumbprint, SAN, validity
of what each server is presenting right now). That's runtime state, re-read from the network
every scan -- not configuration -- and it's pushed into ServiceNow's own certificate table by
servicenow/sync_cmdb_to_sn.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.util import load_json, save_json, audit, utcnow, CMDB_DIR  # noqa: E402
from common.sn_config import get_monitored_sites  # noqa: E402
from adapters.base import probe_tls  # noqa: E402

CERT_TABLE = CMDB_DIR / "certificates.json"


def scan_all():
    sites = get_monitored_sites()
    table = load_json(CERT_TABLE, {})
    scanned = 0
    for site in sites:
        try:
            presented = probe_tls(site["host"], site["port"], site["sni"])
        except (ConnectionRefusedError, OSError, TimeoutError) as exc:
            audit("discovery.scan.unreachable", binding_id=site["binding_id"], error=str(exc))
            continue
        record = table.get(site["binding_id"], {})
        record.update({
            "binding_id": site["binding_id"],
            "server": site["server"],
            "certificate_name": site["sni"],
            "thumbprint": presented["thumbprint"],
            "serial": presented["serial"],
            "san": presented["san"],
            "valid_from": presented["not_before"],
            "valid_to": presented["not_after"],
            "last_scanned": utcnow(),
        })
        record.setdefault("state", "Discovered")
        table[site["binding_id"]] = record
        scanned += 1
    save_json(CERT_TABLE, table)
    audit("discovery.scan.complete", scanned=scanned, total=len(sites))
    return table


if __name__ == "__main__":
    result = scan_all()
    for binding_id, rec in result.items():
        print(f"{binding_id}: thumbprint={rec['thumbprint'][:16]}...  valid_to={rec['valid_to']}  state={rec['state']}")
