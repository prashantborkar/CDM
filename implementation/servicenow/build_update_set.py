"""Builds ServiceNow Update Set XML files by hand, for import via
System Update Sets > Retrieved Update Sets > Import from XML.

This exists because the generic Table API (/api/now/table/...) is disabled instance-wide on
dev436337 for external OAuth clients ("Access to unscoped api is not allowed") -- confirmed by
testing against three different tables with a valid, freshly-issued OAuth token. Update Set import
is a different mechanism (the platform's own customization loader, driven through the UI), so it is
not subject to that restriction, and lets us create real artifacts (Scripted REST APIs, tables,
script includes) without needing Table API write access at all.

Important XML detail: a sys_update_xml record's <payload> is itself XML text, wrapped in ONE CDATA
section (so the outer parser treats it as opaque). Any field *within* that payload whose value could
contain '<', '>' or '&' (for example a JavaScript operation_script) must be handled WITHOUT a nested
literal CDATA -- nested CDATA is not valid XML (the first "]]>" anywhere closes the outer section,
truncating everything after it). Instead, xml_escape() below entity-escapes such values so they sit
safely inside the single outer CDATA. Every generator function in this file follows that rule.

Run:  python servicenow/build_update_set.py
Output:  servicenow/update_sets/*.xml
"""
import uuid
import datetime as dt
from pathlib import Path

OUT = Path(__file__).resolve().parent / "update_sets"
OUT.mkdir(exist_ok=True)

APP_SYS_ID = "03bd97688327871024fcad30ceaad3db"       # Certificate Deployment Manager (x_2182912_certif_0)
APP_SCOPE = "x_2182912_certif_0"
APP_NAME = "Certificate Deployment Manager"
CREATED_BY = "cdm.integration"


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def guid():
    return uuid.uuid4().hex


def xml_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "&apos;"))


def field(name, value, cdata=False):
    """One <name>value</name> element for inside a record's XML, safely escaped."""
    if value is None:
        return f"<{name}/>"
    v = xml_escape(str(value))
    return f"<{name}>{v}</{name}>"


def ref_field(name, sys_id, display_value):
    """One <name display_value="...">sys_id</name> element -- the form real ServiceNow exports use
    for reference fields (sys_scope, sys_package, application, ...). Some commit-time scope checks
    key off sys_package specifically, not just sys_scope, so both are set wherever either appears."""
    return f'<{name} display_value="{xml_escape(display_value)}">{sys_id}</{name}>'


def record_update(table, sys_id, fields: dict, raw: list = None) -> str:
    """fields: plain name->value pairs, escaped and rendered via field().
    raw: pre-rendered XML element strings (e.g. from ref_field()) appended as-is, for reference
    fields that need a display_value attribute."""
    inner = "".join(field(k, v) for k, v in fields.items()) + "".join(raw or [])
    return f'<record_update table="{table}"><{table} action="INSERT_OR_UPDATE">{inner}</{table}></record_update>'


def sys_update_xml_wrapper(name, payload_xml, update_set_id, target_name, type_, sys_id=None):
    sys_id = sys_id or guid()
    return f"""<sys_update_xml action="INSERT_OR_UPDATE">
<name>{xml_escape(name)}</name>
<payload><![CDATA[{payload_xml}]]></payload>
<remote_update_set display_value="{xml_escape(APP_NAME)}">{update_set_id}</remote_update_set>
<sys_id>{sys_id}</sys_id>
<target_name>{xml_escape(target_name)}</target_name>
<type>{xml_escape(type_)}</type>
<update_domain>global</update_domain>
<update_set display_value="{xml_escape(APP_NAME)}">{update_set_id}</update_set>
<view/>
</sys_update_xml>"""


def remote_update_set(update_set_id, name, description):
    ts = now()
    return f"""<sys_remote_update_set action="INSERT_OR_UPDATE">
<application display_value="{xml_escape(APP_NAME)}">{APP_SYS_ID}</application>
<application_name>{xml_escape(APP_NAME)}</application_name>
<application_scope>{APP_SCOPE}</application_scope>
<application_version/>
<description>{xml_escape(description)}</description>
<name>{xml_escape(name)}</name>
<origin_sys_id>{update_set_id}</origin_sys_id>
<release_date/>
<remote_sys_id>{update_set_id}</remote_sys_id>
<state>loaded</state>
<sys_class_name>sys_remote_update_set</sys_class_name>
<sys_id>{update_set_id}</sys_id>
<sys_created_by>{CREATED_BY}</sys_created_by>
<sys_created_on>{ts}</sys_created_on>
<sys_mod_count>0</sys_mod_count>
<sys_updated_by>{CREATED_BY}</sys_updated_by>
<sys_updated_on>{ts}</sys_updated_on>
</sys_remote_update_set>"""


def unload(update_set_xml: str, parts: list[str]) -> str:
    body = "\n".join(parts)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<unload unload_date="{now()}">
{update_set_xml}
{body}
</unload>
"""


# --------------------------------------------------------------------------- 01: ping (no table)
def build_ping_api():
    us_id = guid()
    ws_def_id = guid()
    ws_op_id = guid()
    ts = now()

    def_payload = record_update("sys_ws_definition", ws_def_id, {
        "active": "true",
        "consumes": "application/json",
        "consumes_customized": "false",
        "name": "CDM",
        "produces": "application/json",
        "produces_customized": "false",
        "protection_policy": "read_only",
        "service_id": "cdm",
        "short_description": "Certificate Deployment Manager REST API",
        "sys_class_name": "sys_ws_definition",
        "sys_id": ws_def_id,
        "sys_created_by": CREATED_BY, "sys_created_on": ts, "sys_mod_count": "0",
        "sys_updated_by": CREATED_BY, "sys_updated_on": ts,
    }, raw=[
        ref_field("sys_scope", APP_SYS_ID, APP_NAME),
        ref_field("sys_package", APP_SYS_ID, APP_NAME),
    ])

    ping_script = (
        '(function process(/*RESTAPIRequest*/ request, /*RESTAPIResponse*/ response) {\n'
        '    response.setStatus(200);\n'
        '    return {\n'
        '        status: "ok",\n'
        '        message: "CDM Scripted REST API is live",\n'
        '        time: new GlideDateTime().getDisplayValue()\n'
        '    };\n'
        '})(request, response);'
    )
    op_payload = record_update("sys_ws_operation", ws_op_id, {
        "active": "true",
        "consumes": "application/json",
        "consumes_customized": "false",
        "http_method": "GET",
        "name": "ping",
        "operation_script": ping_script,
        "produces": "application/json",
        "produces_customized": "false",
        "relative_path": "/ping",
        "requires_authentication": "true",
        "requires_snc_internal_role": "false",
        "short_description": "Health check",
        "sys_class_name": "sys_ws_operation",
        "sys_id": ws_op_id,
        "web_service_definition": ws_def_id,
        "sys_created_by": CREATED_BY, "sys_created_on": ts, "sys_mod_count": "0",
        "sys_updated_by": CREATED_BY, "sys_updated_on": ts,
    }, raw=[
        ref_field("sys_scope", APP_SYS_ID, APP_NAME),
        ref_field("sys_package", APP_SYS_ID, APP_NAME),
    ])

    parts = [
        sys_update_xml_wrapper(f"sys_ws_definition_{ws_def_id}", def_payload, us_id, "CDM", "Scripted REST Service"),
        sys_update_xml_wrapper(f"sys_ws_operation_{ws_op_id}", op_payload, us_id, "CDM/ping", "Scripted REST Resource"),
    ]
    us_xml = remote_update_set(us_id, "CDM 01 - Ping REST API (retry 2, sys_package added)",
                                "Minimal Scripted REST API (GET /ping) to verify the unscoped-API "
                                "restriction does not block a real Scripted REST endpoint.")
    xml = unload(us_xml, parts)
    out = OUT / "01_ping_api.xml"
    out.write_text(xml, encoding="utf-8")
    print(f"wrote {out}  ({len(xml)} bytes)")
    print(f"  service_id=cdm  operation path=/ping")
    print(f"  expected URL once installed: https://dev436337.service-now.com/api/{APP_SCOPE}/cdm/ping")


if __name__ == "__main__":
    build_ping_api()
