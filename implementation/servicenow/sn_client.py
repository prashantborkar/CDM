"""A real, working ServiceNow REST client -- now that we know how to authenticate.

Root cause of every earlier 401/403: the account's Identity Type must be set to "Machine" in
ServiceNow (System Security > Users, or the user record's Identity Type field) for Basic Auth /
external API calls to be accepted at all on this instance. Once that's set, plain Basic Auth works
normally -- no OAuth client, no scope gymnastics needed.

IMPORTANT: Machine identity type also blocks *interactive UI login* for that same account -- we
learned this the hard way by setting it on `admin` and locking ourselves out of the browser. All
automation now runs under `cdm.integration` (a dedicated Machine-identity account, credential alias
"servicenow/cdm_integration"), so `admin` and any other real person's login can stay Human and keep
working in the browser. Never flip a real person's login account to Machine -- always use a
dedicated service account for that.

Table-creation scoping note: creating a NEW table (sys_db_object) via the Table API always lands in
Global scope with a u_ prefix on this instance, regardless of what sys_scope/sys_package value is
sent (confirmed empirically -- not a value problem, a platform behavior for API-originated schema
changes). We accept that: Global-scope custom tables work completely normally for read/write/REST;
they're just not bundled inside the CDM scoped app for later export. Anything built by hand in
Studio (like the /ping endpoint) *does* land in the real x_2182912_certif_0 scope correctly.

Credentials: read from vault_stub, the same as everything else in implementation/, so nothing is
hardcoded here and this module can later point at CyberArk (or a Machine-identity service account)
by changing exactly one thing: the vault alias it reads.
"""
import base64
import json
import sys
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vault_stub.vault import get_credential  # noqa: E402

INSTANCE = "https://dev436337.service-now.com"


class ServiceNowClient:
    def __init__(self, instance=INSTANCE, credential_alias="servicenow/cdm_integration"):
        cred = get_credential(credential_alias)
        auth = base64.b64encode(f"{cred['username']}:{cred['secret']}".encode()).decode()
        self.instance = instance
        self.headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json",
                         "Accept": "application/json"}

    def call(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"{self.instance}{path}", data=data, headers=self.headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode()
                return resp.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            return e.code, (json.loads(raw) if raw else None)

    def get(self, path):
        return self.call("GET", path)

    def insert(self, table, fields: dict):
        return self.call("POST", f"/api/now/table/{table}", fields)

    def query(self, table, encoded_query="", fields=None, limit=100):
        q = f"sysparm_query={urllib.parse.quote(encoded_query)}&" if encoded_query else ""
        f = f"sysparm_fields={urllib.parse.quote(fields)}&" if fields else ""
        return self.call("GET", f"/api/now/table/{table}?{q}{f}sysparm_limit={limit}")

    def delete(self, table, sys_id):
        return self.call("DELETE", f"/api/now/table/{table}/{sys_id}")

    def find_one(self, table, encoded_query):
        status, body = self.query(table, encoded_query, fields="sys_id", limit=1)
        if status == 200 and body and body.get("result"):
            return body["result"][0]["sys_id"]
        return None
