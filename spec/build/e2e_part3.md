
---

## 10. Security and CyberArk

### 10.1 Principles

1. Every credential comes from CyberArk, just in time, short-lived, held in memory. Nothing is stored in ServiceNow, in scripts, in flow variables or in files.
2. The private key that Sectigo creates never enters ServiceNow. The MID Server fetches it directly, holds it briefly, installs it and wipes it.
3. Only approved, signed, versioned adapters run.
4. The MID Server connects outbound only. Each network zone has its own MID Servers and its own accounts.
5. Deployment accounts are different from any account used for Discovery, and each has only the rights it needs.
6. Every action is audited. Every failure is visible. Nothing is closed without proof.

### 10.2 CyberArk integration

| Item | Design |
|---|---|
| Access method | The MID Server asks the CyberArk Central Credential Provider (CCP) for the credential, or ServiceNow's external credential storage for CyberArk is used. To be confirmed for your instance and MID version (item V3) |
| Identity of the caller | A CyberArk application identity per zone (for example `CDM`), authenticated by client certificate and allowed only from the MID Server hosts of that zone |
| Safes | One per zone for deployment accounts (CDM-Internal, CDM-Dmz), one for Sectigo (CDM-Sectigo), one for Java keystore passwords (CDM-Java) |
| Retrieval | Per job. The credential is held in memory for at most the lease time (default 15 minutes) |
| Rotation | Managed by CyberArk. CDM always asks at job time, so a rotated password is always current |
| Audit | CyberArk records who retrieved what and when; CDM records the job |
| Failure | CyberArk unavailable: the job waits, retries and alerts. It never falls back to a stored password |

Example of the retrieval the MID Server performs (indicative; confirm with your CyberArk version):

```text
GET https://ccp.example.com/AIMWebService/api/Accounts?AppID=CDM&Safe=CDM-Internal&Object=svc-cdm-win-deploy
(client certificate authentication)
-> returns the account name and its current secret, used at once and not stored
```

### 10.3 Where each item exists

| Item | ServiceNow | MID Server | Target server | Sectigo | CyberArk |
|---|---|---|---|---|---|
| Certificate identity (thumbprint, SAN, dates, name) | Yes | Briefly | Yes (in use) | Yes | No |
| Public certificate and chain | Metadata only | Briefly | Yes | Yes | No |
| Private key | **Never** | Briefly, in memory or encrypted temporary storage | Yes (in use) | Yes at first (item V1) | No |
| Bundle passphrase | Never | Memory only | No | Only if Sectigo needs it | Optional |
| Deployment account secret | Never | Memory only | Used to log in | No | **Yes** |
| Sectigo API secret | Never | Memory only | No | Used to call | **Yes** |
| Keystore password (Java) | Never | Memory only | In the keystore | No | **Yes** |

### 10.4 Threats and mitigations

| # | Threat | Mitigation | Requirements |
|---|---|---|---|
| T1 | Theft of a deployment credential | CyberArk just-in-time, short-lived, per zone, audited retrieval | FR-SEC-001, FR-DEP-003 |
| T2 | Theft of the private key in transit or at rest on the MID Server | Direct fetch by the MID Server, memory or encrypted temporary storage, short life, protected channel, wipe and confirm | FR-KEY-002 to FR-KEY-009 |
| T3 | Key ends up in ServiceNow, a log or a payload | Never stored; log redaction; jobs carry references only | FR-KEY-003, FR-SEC-006, FR-DEP-001 |
| T4 | Wrong certificate deployed by a bad match | Identity matching, uniqueness, re-check after fetch, drift check, live check, rollback | FR-MAT-002, FR-MAT-006, FR-DEP-004, FR-VER-001 |
| T5 | A modified or malicious adapter | Signed, allow-listed adapters, four-eyes approval | FR-ADP-003, FR-DEP-012, FR-SEC-007 |
| T6 | A compromised MID Server used to move sideways | Outbound only, zone segmentation, least privilege, hardening | FR-SEC-003, FR-SEC-002 |
| T7 | A deployment profile altered to redirect a certificate | Versioned, approved profiles, audit | FR-CFG-004, FR-SEC-007 |
| T8 | A stale or wrong CMDB causes a wrong decision | Stale-data guard, drift check, live check, confirmation by scan | FR-SYN-005, FR-DEP-004, FR-VER-003 |
| T9 | Sectigo or CyberArk outage | Retry, back-off, alerts, renewal window with margin | FR-SYN-008, FR-EXC-006 |
| T10 | Insider misuse | Roles, segregation of duties, audit | FR-SEC-005, FR-AUD-001 |

### 10.5 MID Server hardening

A dedicated service account, no domain administrator rights, disk encryption, a recognised security baseline, egress limited to ServiceNow, Sectigo, CyberArk and the target servers of its zone, and no inbound connections.

---

## 11. Data model and states

### 11.1 Records (ServiceNow tables)

No table stores a private key, a bundle or a secret.

| Record | Key fields | Purpose |
|---|---|---|
| Certificate | certificate id, name, common name, SAN set, serial, thumbprint, valid from, valid to (UTC), state, CMDB CI reference, Sectigo reference, replaced by | The normalised identity of a certificate |
| Binding | binding id, certificate, server, profile, state, old thumbprint, new thumbprint, deployed at, confirmed at | One certificate on one server |
| SectigoRecord | Sectigo ID, order number, name, SAN, serial, thumbprint, valid from, valid to, status, first seen, deployed flag | The landing queue |
| MatchResult | match id, ServiceNow certificate, Sectigo record, rule, result (unique, ambiguous, none, unknown, unlocated), evidence | Why a match was made |
| ReviewItem | item id, match, reason, assignee, decision | Ambiguous and unlocated items |
| DeploymentProfile | profile id, version, status, server, zone, adapter and version, credential references, technology settings, activation, verification, window, owner | How to deploy on one server |
| DeploymentJob | job id, binding, profile version, adapter version, MID Server, state, attempt, backup reference, started, ended, checks, evidence | One run |
| Adapter | id, technology, version, signature, status, approved by | Signed adapter registry |
| Zone | name, MID Servers, accounts references | Segmentation |
| CredentialReference | safe, object, purpose, zone | CyberArk pointer (no secret) |
| Settings | name, value, changed by, changed at | Configuration |
| AuditEvent | event id, actor, action, object, time (UTC), result, previous hash | Tamper-evident audit |

### 11.2 States

Binding states (section 4.4): Discovered, Expiring, Replacement landed, Planned, Deploying, Deployed awaiting scan, Confirmed by discovery. Exception states: No profile (manual task), Ambiguous (review), Drift, Rolled back, Failed, Unconfirmed. Certificate state: Active, Expiring, Replaced, Expired.

A certificate on several servers is Replaced only when every one of its bindings is Confirmed. Until then it stays Active with the count of confirmed bindings shown.

---

## 12. Interfaces

| Interface | Direction | Protocol | Purpose |
|---|---|---|---|
| CDM and ServiceNow CMDB | Inside the instance | Native scripted access | Read certificate CIs, write CDM state, relations and events |
| CDM and Sectigo (list and public certificate) | Instance or MID Server to Sectigo | HTTPS REST, credentials from CyberArk | Landing queue, identity |
| MID Server and Sectigo (bundle) | MID Server to Sectigo | HTTPS REST, credentials from CyberArk | Certificate and private key bundle |
| ServiceNow and MID Server | Instance and MID Server | ECC queue, MID connects outbound over HTTPS 443 | Job dispatch, results |
| MID Server and CyberArk | MID Server to CyberArk | HTTPS with client certificate | Just-in-time credentials |
| MID Server and Windows server | MID Server to server | WinRM over HTTPS or Kerberos | Windows IIS adapter |
| MID Server and Linux server | MID Server to server | SSH with keys or certificates | Linux and Java adapters |
| MID Server and live endpoint | MID Server to server | TLS on the service port | Live verification |
| Users and CDM | Browser | HTTPS with SSO | Workspace, review queue, dashboards |
| Notifications | Instance | Email (Teams or Slack later) | Owners and admins |
| Audit export | Instance | Syslog over TLS or HTTPS | SIEM (later) |

---

## 13. Non-functional requirements

| ID | Requirement | Target | Src |
|---|---|---|---|
| NFR-SEC-01 | TLS 1.2 or higher on every link. No unencrypted WinRM, no Basic over HTTP. | Configuration scan | NEW |
| NFR-SEC-02 | No private key, bundle, passphrase or credential stored in ServiceNow or in any log. | Secret scan finds none | ANS |
| NFR-SEC-03 | Key material on a MID Server lives at most the configured time (default 15 minutes) and is deleted and confirmed. | Test | ANS |
| NFR-SEC-04 | Adapters run only if approved and signed; tampering is blocked and alerted. | Tamper test blocked | NEW |
| NFR-AVL-01 | At least two MID Servers per production zone with failover. | Failover test | NEW |
| NFR-AVL-02 | A MID Server failure during a job leads to resume on the peer or to rollback within 5 minutes. | Chaos test | NEW |
| NFR-AVL-03 | A 7-day outage of CDM, Sectigo or CyberArk does not cause an expiry, because the renewal window has margin. | Design review | NEW |
| NFR-PRF-01 | 10,000 certificates in the inventory; the daily sync finishes in 15 minutes; an incremental sync in 2 minutes. | Load test | NEW |
| NFR-PRF-02 | One IIS or Apache deployment (excluding waiting for a window) completes in 5 minutes including the live check. | Timing test | NEW |
| NFR-REL-01 | The same inputs always give the same match and result. No automatic deployment on an ambiguous match. | Unit tests | PS |
| NFR-REL-02 | First-attempt deployment success of 98 percent or better. Every failure ends in rollback, a manual task or an incident. | KPI | NEW |
| NFR-REL-03 | Deploy-to-confirmation within 36 hours for 99 percent of bindings (daily scan). | KPI | ANS |
| NFR-AUD-01 | 100 percent of actions are audited and tamper-evident. | Audit test | NEW |
| NFR-OPS-01 | Runbooks, monitoring and alerts for CDM, MID Servers, the Sectigo connection and the CyberArk connection. | Review | NEW |
| NFR-MNT-01 | The adapter contract is versioned and backward compatible within a major version. | Contract tests | NEW |
| NFR-USA-01 | An owner sees at a glance what is expiring, what has landed, what is deployed and what is confirmed. | Usability test | NEW |

---

## 14. Building it: proof of concept on the personal instance

### 14.1 Goal

Prove the whole loop on your ServiceNow personal instance with a laptop and small lab servers: match, fetch, deploy, verify, and confirm on the next scan. Then move the same scoped application and configuration file to the licensed instance.

### 14.2 What is needed

| Component | Proof-of-concept choice |
|---|---|
| ServiceNow | Personal instance, a scoped application with the tables in chapter 11 |
| MID Server | One MID Server on the laptop (Java 17), playing every zone |
| Sectigo | Sandbox if you have access. Otherwise a test CA that behaves like the landing area: it lists new certificates, returns the public certificate, and returns a real PKCS#12 with key |
| Discovery data | Real Discovery of the lab server if possible; otherwise a clearly labelled scan simulator that reads the lab server's certificate and updates the certificate CI (thumbprint, serial, SAN, dates, last scanned) |
| CyberArk | A lab or developer safe if available. Otherwise a clearly labelled temporary stand-in that is removed before production |
| Windows target | Local IIS with a site and an HTTPS binding using an old test certificate |
| Linux target | WSL or a small VM with Apache and an old test certificate |
| Java target | A small application with a PKCS#12 keystore |

The test CA must provide these behaviours: list certificates issued since a time; return the public certificate for an ID; return a PKCS#12 bundle for an ID (limited downloads); issue an "old" certificate with a short validity so it is inside the renewal window, and a "new" one for the same names.

### 14.3 Build order

1. Create the scoped application, tables and settings; enter the configuration (chapter 7).
2. Connect the MID Server; verify it reaches the lab servers.
3. Build the Sectigo connector against the test CA (or the sandbox): stage 2.
4. Build the ServiceNow sync and the matching: stages 1 and 3. Show a unique match on the review screen.
5. Build the planning and the deployment profiles: stage 4.
6. Build the MID job with the adapter contract and the IIS adapter: stages 5 to 11 on Windows. Then Apache. Then Java.
7. Add the verification and the confirmation by the next scan: stage 12 (trigger the scan or the simulator by hand instead of waiting a day).
8. Add the failure paths: drift, bad bundle, failed reload, failed verification, rollback, no profile, ambiguous match.
9. Replace the stand-ins: real CyberArk safes, real Sectigo sandbox, real Discovery.

### 14.4 Exit criteria

1. An expiring certificate in the CMDB is matched, uniquely, to the new certificate at Sectigo.
2. CDM fetches the bundle by API through the MID Server and deploys it on IIS (store, key permission, binding), on Apache (owner, permission, graceful reload) and in a Java keystore, with no manual step.
3. The live endpoint shows the new thumbprint immediately. After the next scan the CMDB shows the new thumbprint and dates, and CDM sets "Confirmed by discovery".
4. A forced failure rolls back automatically and the rollback is verified.
5. No key, bundle, passphrase or password is found in ServiceNow, in a log, in a job payload or on the MID Server after the job.
6. Changing a deployment profile changes the behaviour without editing code.

---

## 15. Test and acceptance

| ID | Scenario | Expected result |
|---|---|---|
| TC-01 | IIS certificate nearing expiry, replacement at Sectigo, profile exists | Unique match, deployed, key permission set, binding updated, live check ok, next scan confirms |
| TC-02 | Apache certificate, replacement landed | Files written with the right owner and permission, graceful reload (no restart), live check ok, confirmed |
| TC-03 | Java keystore | Alias updated, application reloaded, live check ok, confirmed |
| TC-04 | Same certificate on three servers | One job per server, canary first, all confirmed, certificate Replaced only when all three are confirmed |
| TC-05 | Two possible replacements | Ambiguous, review queue, no deployment |
| TC-06 | No deployment profile | Status "No profile", manual task, later live check and scan confirm |
| TC-07 | Server presents something other than the CMDB's old thumbprint | Drift: stop before any change, alert |
| TC-08 | Bundle thumbprint or SAN differs from the plan | Stop before any change |
| TC-09 | Reload fails after install | Automatic rollback, verified, incident |
| TC-10 | Live check fails | Automatic rollback, verified, incident |
| TC-11 | Next scan still shows the old thumbprint | Alert, not closed |
| TC-12 | Next scan does not run within 36 hours | Alert, live re-probe, escalation |
| TC-13 | Expiring certificate, nothing at Sectigo | Alerts at 30, 14, 7, 3, 1 days |
| TC-14 | One-month certificate | Renewal window about 10 days |
| TC-15 | CyberArk unavailable | Job waits and retries, alert, no stored password used |
| TC-16 | MID Server down during a job | Moves to the peer or rolls back within 5 minutes |
| TC-17 | Secret scan of ServiceNow, logs, payloads and the MID Server after a run | No key, bundle, passphrase or password |
| TC-18 | Unsigned or modified adapter | Blocked, alert |
| TC-19 | CMDB data older than 36 hours | No decision, alert |
| TC-20 | Certificate at Sectigo with no server, and certificate in the CMDB unknown to Sectigo | Reported as unlocated and unknown |

| Phase | Accepted when |
|---|---|
| P0 | The exit criteria in 14.4 are met on the personal instance |
| P1 | TC-01 to TC-20 pass against the licensed instance, the real Sectigo and the real CyberArk; a security review is closed |
| P2 | The later technologies added in P2 pass their equivalent tests |

---

## 16. Roadmap

Durations are indicative.

| Phase | Duration | Scope |
|---|---|---|
| P0 Proof of concept | 2 to 3 weeks | Chapter 14: personal instance, test CA or sandbox, IIS, Apache, Java, closed loop |
| P1 First release | 8 to 10 weeks | Licensed instance, real Sectigo, real CyberArk, real Discovery, all stages, three adapters, dashboards, alerts, audit, manual fallback, security review, pilot on a few real servers |
| P2 Next | 6 to 8 weeks | Trigger the renewal at Sectigo from CDM, approvals and change windows, on-demand rescan, cluster support, OpenShift or Kubernetes, more technologies |
| P3 Later | To be planned | Load balancers, databases, network devices, reporting and SIEM export |
| Parked | Not scheduled | Selling and packaging, Apple, cloud services. IWS and Rundeck are not used |

---

## 17. Risks

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | Sectigo cannot deliver the private key by API for your organisation or profile | Design change | Verify first (V1); fall back to the key created on the server (6.2) |
| R2 | Discovery fields differ from the assumption (for example the server relationship or SAN format) | Matching fails | Verify (V2); normalise; use the review queue |
| R3 | Discovery data is stale | Wrong decisions | Stale-data guard, drift check, live check |
| R4 | A shared key across several servers is unacceptable to the security team | Design change | Agree the policy early; per-server certificates if required |
| R5 | Deployment profile data (site names, paths, keystore locations) is missing | Fewer automatic deployments | Onboarding with owners; templates; manual fallback |
| R6 | Java applications that need a restart | Service impact | Hot reload where possible; windows for restarts |
| R7 | CyberArk access for MID Servers takes time to approve | Delay | Start the request early; use the lab safe meanwhile |
| R8 | The personal instance limits (plugins, inactivity) | POC delay | Keep configuration exportable; confirm plugins (V4) |
| R9 | Network and firewall approvals per zone | Delay | Outbound-only MID Servers; raise early |
| R10 | One-month certificates leave little margin | Missed renewals | Adaptive window, alerts, daily loop |

---

## 18. Items to verify

Your answers settled most points. These remain, each with the assumption used until it is checked.

| # | Item | Assumption until verified |
|---|---|---|
| V1 | **Sectigo:** server-side key generation by API for your organisation and profile; the call that returns the bundle and its format; passphrase handling; number and lifetime of downloads; whether Sectigo keeps a copy of the key; whether a renewal has a new key; list and status endpoints; sandbox availability | You are right that it can be done by API; PKCS#12 bundle, one download |
| V2 | **ServiceNow:** the certificate class and the exact field names; how the server is related to the certificate CI; the SAN format; where the last scanned time is kept | Fields exist as listed in 7.5 |
| V3 | **CyberArk:** access through the Central Credential Provider or through ServiceNow's external credential storage; the MID Server version; application identity and safes | CCP called by the MID Server with a client certificate |
| V4 | **Personal instance:** which plugins and steps are available (for example scripted REST, MID script includes, external credential storage) | Scripted application code and MID script includes are available |
| V5 | **Renewal at Sectigo today:** who triggers it, and how many days before expiry the new certificate lands | Lands before the renewal window starts |
| V6 | **Estate:** how many servers and certificates per technology, the certificate lifetimes, and who supplies the deployment profile data | Start with a pilot set per technology |
| V7 | **Change and approval:** whether production deployments need approval and a change window | No approval at first, a night window for production |
| V8 | **Zones:** the network zones and where MID Servers can be placed | One MID Server per zone, as a pair in production |
| V9 | **Discovery:** whether one server can be rescanned on demand | Not needed for the first release; the daily scan confirms |
| V10 | **Shared keys:** whether one certificate and key may be deployed to several servers | Allowed, recorded per binding |

---

## Appendix A: Adapter contract

Every adapter implements the same operations and returns the same result. The request carries references; the result carries evidence and no secret.

```json
{
  "request": {
    "job_id": "JOB0012345",
    "operation": "install",
    "adapter": {"id": "windows-iis", "version": "1.0.0", "sha256": "<hash>"},
    "binding": {"server": "web01.example.com", "zone": "internal", "profile": "PRF-0001", "profile_version": 1},
    "expected": {"old_thumbprint": "<sha256 of old>", "new_thumbprint": "<sha256 of new>", "san": ["app.example.com"]},
    "sectigo": {"certificate_id": "<id>"},
    "credential_references": {"deploy": {"safe": "CDM-Internal", "object": "svc-cdm-win-deploy"}},
    "timeout_seconds": 300
  },
  "response": {
    "job_id": "JOB0012345",
    "status": "success",
    "error_code": null,
    "evidence": {
      "thumbprint_before": "<sha256>",
      "thumbprint_after": "<sha256>",
      "presented_san": ["app.example.com"],
      "not_after": "2027-03-19T00:00:00Z",
      "key_permission": ["IIS APPPOOL\\AppPool1"],
      "backup_reference": "BKP-0009"
    },
    "cleanup": {"temp_files_removed": true, "memory_cleared": true, "session_closed": true}
  }
}
```

`operation` is one of precheck, backup, install, activate, verify, rollback, cleanup, discover. `status` is one of success, failed, rolled_back, manual_required.

## Appendix B: Sectigo API (indicative)

Indicative and to be verified against the current Sectigo documentation and your tenant (item V1).

| Purpose | Indicative call | Notes |
|---|---|---|
| Authentication | Headers: login, password or key, customerUri | From CyberArk |
| List certificates and status | `GET /api/ssl/v1` with filters | Landing queue |
| Collect public certificate | `GET /api/ssl/v1/collect/{sslId}?format=...` | Exact thumbprint, no key |
| Certificate and private key bundle | The server-side key generation download for the certificate (to be identified) | Fetched only by the MID Server at deployment |
| Renew (later) | `POST /api/ssl/v1/renewById/{sslId}` | P2 |

## Appendix C: How your problem statement is covered

| Problem statement point | Where it is specified |
|---|---|
| 1 Many applications, many technologies | Chapter 9, FR-ADP |
| 2 Validity from one month to a year, renewal before expiry | Section 7.4, FR-PLN-001 |
| 3 Sectigo landing area, read by API | Stage 2, FR-SYN-002 |
| 4 Discovery knows name, thumbprint, serial, SAN, server, dates; not the certificate or key | Stage 1, section 5.1, FR-SYN-001, FR-SYN-009 |
| 5 The two locations, joined by hand today | Chapter 4 |
| 6 Access both, identity, pick from ServiceNow, pick from Sectigo, deploy through the MID Server | Stages 1 to 9, chapter 5, FR-MAT |
| 7 Next-day scan proves the deployment | Stage 12, FR-VER-003 |
| 8 Technology methods: IIS (store, key permission, binding), Apache (key, owner, permission, reload not restart), Java (keystore) | Chapter 9, AD-WIN, AD-LNX, AD-JVA |
| 9 API is the best pickup method | Chapter 2 item 10, FR-SYN-002, FR-KEY-001 |
