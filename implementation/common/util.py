"""Shared helpers for the CDM local implementation.

Every module in this implementation writes through here so that:
  - all timestamps are UTC, ISO-8601 (matches FR-SYN-006 / NFR requirement to compare in UTC)
  - every action is appended to the audit log (stands in for FR-AUD-001 until ServiceNow exists)
  - JSON files are read/written consistently (stand in for ServiceNow tables, chapter 11 of the spec)

Nothing in this file, or anywhere in /implementation, ever writes a private key or a password to
a JSON "table" file or to the audit log. Keys live only in memory or under jobs/<job_id>/ (which is
deleted by adapters after use, per FR-KEY-004). Passwords live only in vault_stub's store file,
which stands in for CyberArk and is clearly marked as a stand-in everywhere it is used.
"""
import json
import os
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .../implementation
DATA = ROOT / "data"
CMDB_DIR = ROOT / "cmdb"
LOGS = ROOT / "logs"
JOBS = ROOT / "jobs"
CONFIG_PATH = ROOT / "config" / "cdm_config.json"

for d in (DATA, CMDB_DIR, LOGS, JOBS):
    d.mkdir(parents=True, exist_ok=True)


def utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def parse_ts(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def load_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=False)
    os.replace(tmp, path)  # atomic on the same volume


def load_config():
    return load_json(CONFIG_PATH, {})


def audit(event: str, **fields):
    """Append one tamper-evident-style audit line (stands in for FR-AUD-001 / ServiceNow AuditEvent).

    Real production audit is in ServiceNow with a previous-hash chain (spec 11.1 AuditEvent.prev_hash).
    Here we approximate the "tamper evident" property with a running SHA-256 chain over the log file,
    so the mechanism is real even though the storage (a local file) is a stand-in.
    """
    import hashlib
    LOGS.mkdir(parents=True, exist_ok=True)
    log_path = LOGS / "audit.jsonl"
    prev_hash = ""
    if log_path.exists():
        with open(log_path, "rb") as fh:
            lines = fh.readlines()
        if lines:
            prev_hash = json.loads(lines[-1].decode("utf-8")).get("hash", "")
    record = {"time": utcnow(), "event": event, **fields, "prev_hash": prev_hash}
    record["hash"] = hashlib.sha256(json.dumps(record, sort_keys=True).encode("utf-8")).hexdigest()
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def new_job_dir(job_id: str) -> Path:
    d = JOBS / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def redact(d: dict, keys=("private_key_pem", "pkcs12_base64", "passphrase", "password", "secret")) -> dict:
    """Return a copy of d with sensitive fields masked, for anything that gets logged or printed."""
    out = {}
    for k, v in d.items():
        if k in keys:
            out[k] = "***REDACTED***"
        elif isinstance(v, dict):
            out[k] = redact(v, keys)
        else:
            out[k] = v
    return out
