"""VAULT STUB -- stands in for CyberArk until CyberArk exists (spec chapter 10, FR-SEC-001).

This is deliberately the smallest possible thing that satisfies the *interface* CDM needs from a
vault: "give me the current secret for this alias, on demand, and record that I asked". It is not
secure enough for anything but this local lab: the store file below is plain JSON on disk.

SWAP TO PRODUCTION: replace `LocalVaultStub` with a client for CyberArk's Central Credential
Provider (CCP) that presents a client certificate and calls:
    GET https://<ccp-host>/AIMWebService/api/Accounts?AppID=CDM&Safe=<safe>&Object=<object>
Every caller in this codebase only ever calls `get_credential(alias)`, so that is the one place
that needs to change (spec 10.2).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.util import load_json, save_json, audit, utcnow  # noqa: E402

STORE = Path(__file__).resolve().parent / "store.json"


def _seed_if_missing():
    if not STORE.exists():
        # Lab-only placeholder secrets. Never real credentials. Replace via set_credential().
        save_json(STORE, {
            "lab/windows_deploy": {"username": "cdmdeploy", "secret": "lab-only-not-a-real-secret"},
            "lab/linux_deploy": {"username": "cdmdeploy", "secret": "lab-only-ssh-key-placeholder"},
            "lab/java_keystore": {"username": "keystore", "secret": "lab-only-not-a-real-secret"},
            "sectigo/api": {"username": "cdm-api", "secret": "lab-only-not-a-real-secret"},
            "servicenow/admin": {"username": "admin", "secret": "lab-only-not-a-real-secret"},
        })


def get_credential(alias: str) -> dict:
    """alias looks like 'vault:lab/windows_deploy' or bare 'lab/windows_deploy'."""
    _seed_if_missing()
    key = alias.split("vault:", 1)[-1]
    store = load_json(STORE, {})
    if key not in store:
        audit("vault.retrieve.failed", alias=key, reason="not_found")
        raise KeyError(f"No credential for alias '{key}' in the vault stub")
    audit("vault.retrieve", alias=key)  # CyberArk logs this too; we approximate that here
    return store[key]


def set_credential(alias: str, username: str, secret: str):
    _seed_if_missing()
    store = load_json(STORE, {})
    store[alias] = {"username": username, "secret": secret}
    save_json(STORE, store)
    audit("vault.set", alias=alias)


if __name__ == "__main__":
    _seed_if_missing()
    print("Vault stub store:", STORE)
    print("Aliases:", list(load_json(STORE, {}).keys()))
