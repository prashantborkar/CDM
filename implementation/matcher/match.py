"""MATCHER -- implements the identity matching rules from specification chapter 5 (M1-M8),
joining what discovery.py read from the "CMDB" with what the CA simulator's landing area holds.

Deploys automatically only when the match is unique (FR-MAT-002); anything else goes to
cmdb/review_queue.json rather than being silently skipped (FR-MAT-002, FR-SRC-004).
"""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.util import load_json, save_json, audit, load_config, CMDB_DIR  # noqa: E402

CERT_TABLE = CMDB_DIR / "certificates.json"
LANDING_QUEUE = CMDB_DIR / "landing_queue.json"
MATCHES = CMDB_DIR / "matches.json"
REVIEW_QUEUE = CMDB_DIR / "review_queue.json"


def fetch_ca_list():
    cfg = load_config()
    sectigo_cfg = cfg["sources"]["sectigo"]
    if sectigo_cfg.get("mode", "api") == "folder":
        from sources.folder_ca import list_certificates
        root = Path(__file__).resolve().parents[1]
        certs = list_certificates(root / sectigo_cfg.get("folder_path", "input_sectigo_certificates"))
    elif sectigo_cfg.get("mode") == "acme":
        from sources.acme_ca import list_certificates
        certs = list_certificates(sectigo_cfg.get("acme_domains", []))
    else:
        base = sectigo_cfg["base_url"]
        with urllib.request.urlopen(f"{base}/api/ssl/v1", timeout=10) as resp:
            certs = json.load(resp)["certificates"]
    save_json(LANDING_QUEUE, certs)
    audit("matcher.ca_sync", count=len(certs))
    return certs


def _san_ok(cmdb_san, ca_san, rule="equal"):
    a, b = set(cmdb_san), set(ca_san)
    return a == b if rule == "equal" else a.issubset(b)


def match_all():
    cfg = load_config()
    rule = cfg.get("matching", {}).get("san_rule", "equal")
    cmdb = load_json(CERT_TABLE, {})
    ca_certs = fetch_ca_list()

    matches, review = {}, {}
    for binding_id, rec in cmdb.items():
        candidates = [
            c for c in ca_certs
            if c["common_name"] == rec["certificate_name"]
            and _san_ok(rec["san"], c["san"], rule)
            and c["thumbprint"] != rec["thumbprint"]           # M1: not already deployed
            and c["valid_to"] > rec["valid_to"]                 # M2: strictly newer than what's live
        ]
        if len(candidates) == 0:
            continue
        if len(candidates) > 1:
            review[binding_id] = {"reason": "ambiguous", "candidate_ids": [c["id"] for c in candidates]}
            audit("matcher.ambiguous", binding_id=binding_id, candidates=[c["id"] for c in candidates])
            continue
        chosen = candidates[0]
        matches[binding_id] = {
            "binding_id": binding_id, "sectigo_id": chosen["id"],
            "old_thumbprint": rec["thumbprint"], "new_thumbprint": chosen["thumbprint"],
            "san": chosen["san"], "rule": "M2", "matched_at": rec["last_scanned"],
        }
        audit("matcher.matched", binding_id=binding_id, sectigo_id=chosen["id"], rule="M2")

    save_json(MATCHES, matches)
    save_json(REVIEW_QUEUE, review)
    return matches, review


if __name__ == "__main__":
    m, r = match_all()
    print(f"Matched: {len(m)}   Ambiguous/review: {len(r)}")
    for b, v in m.items():
        print(f"  {b} -> {v['sectigo_id']}  ({v['old_thumbprint'][:12]}... -> {v['new_thumbprint'][:12]}...)")
