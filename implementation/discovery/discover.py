"""DISCOVERY SIMULATOR -- stands in for ServiceNow Discovery + the certificate CIs in the CMDB
(spec section 14.2, PRE-SN-07/T2 in the readiness documents). Your answer to the prerequisite
questions was that Discovery already stores thumbprint, serial, SAN, server and exact dates, and
scans daily -- so this simulator produces exactly that shape of record (Appendix E of the
specification) by really connecting to the lab sites and reading what they present, the same way a
network-based certificate scan would.

SWAP TO PRODUCTION: replace SITES below (and this whole module) with real reads of the ServiceNow
CMDB certificate table (FR-SYN-001). Everything downstream (matcher, orchestrator) only ever reads
cmdb/certificates.json, so that is the one file format that has to be matched by the real CMDB
export/API mapping (see CDM_Prerequisites_and_Readiness.md template T2).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.util import load_json, save_json, audit, utcnow, CMDB_DIR  # noqa: E402
from adapters.base import probe_tls  # noqa: E402

CERT_TABLE = CMDB_DIR / "certificates.json"

# The servers Discovery would already know about via CMDB relationships (spec FR-SN-06). This
# stands in for "Discovery already found these servers"; it does not stand in for the deployment
# details (site name, keystore path, etc.), which never come from Discovery -- those come from the
# deployment profile (config/deployment_profiles.json), exactly as the specification says.
SITES = [
    {"binding_id": "lab-win:web01.lab.example.com", "server": "lab-win",
     "host": "127.0.0.1", "port": 8443, "sni": "web01.lab.example.com"},
    {"binding_id": "lab-lnx:api.lab.example.com", "server": "lab-lnx",
     "host": "127.0.0.1", "port": 8445, "sni": "api.lab.example.com"},
    {"binding_id": "ec2-lnx:linuxtest.lab.example.com", "server": "ec2-lnx",
     "host": "16.16.120.70", "port": 443, "sni": "linuxtest.lab.example.com"},
]


def scan_all():
    table = load_json(CERT_TABLE, {})
    scanned = 0
    for site in SITES:
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
    audit("discovery.scan.complete", scanned=scanned, total=len(SITES))
    return table


if __name__ == "__main__":
    result = scan_all()
    for binding_id, rec in result.items():
        print(f"{binding_id}: thumbprint={rec['thumbprint'][:16]}...  valid_to={rec['valid_to']}  state={rec['state']}")
