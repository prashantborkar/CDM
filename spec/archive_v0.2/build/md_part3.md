
---

## 8. Non-functional requirements

| ID | Requirement | Measure or target | Src |
|---|---|---|---|
| NFR-SEC-01 | All CDM links use TLS 1.2 or higher (1.3 preferred). MID Server to vault uses mutual TLS. No HTTP, Basic over HTTP or unencrypted WinRM outside the POC. | Configuration scan | D2, SETUP |
| NFR-SEC-02 | MID Servers and executors make outbound-only connections (443) to the instance and accept no inbound connections. Hardened to a recognised baseline, dedicated service account, disk encryption, no domain admin. | Firewall review, benchmark scan | D2 |
| NFR-SEC-03 | Adapter signatures are verified before execution. Tampering blocks execution and raises an alert. Signing keys live in an HSM or KMS. | Tamper test blocked 100 percent | D3 |
| NFR-SEC-04 | Credentials are JIT from the vault, TTL 15 minutes or less, never reused across zones, never embedded in scripts, variables or files. Discovery and deployment credentials are separate. | Secret scan finds none | D1, D2 |
| NFR-SEC-05 | Logs, ECC payloads and flow context never contain private keys, passwords or PKCS#12 content. | Log review and automated test | D2 |
| NFR-SEC-06 | Mapped to NIST SP 800-57 (key management), NIST SP 800-52 (TLS), CA/B Forum Baseline Requirements, ISO 27001 cryptography controls, SOC 2, and PCI DSS 4.0 certificate inventory expectations where applicable. | Control mapping document | NEW |
| NFR-AVL-01 | At least two MID Servers per production zone with automatic failover. | Failover test | D2 |
| NFR-AVL-02 | A MID Server failure does not lose an in-flight job: it resumes or rolls back within 5 minutes. | Chaos test | D2 |
| NFR-AVL-03 | The system tolerates a 7-day outage of CDM or of the CA without an expiry incident, because renewal starts ahead of expiry (FR-REQ-005). | Design review | NEW |
| NFR-PRF-01 | At least 10,000 certificates in inventory and 200 concurrent deployment jobs across zones (configurable). Dashboard loads in 5 seconds or less. | Load test | NEW |
| NFR-PRF-02 | One Windows or Linux deployment, excluding CA issuance and approvals, completes in 5 minutes or less including live verification. | Timing test | NEW |
| NFR-PRF-03 | Source sync (CMDB and Sectigo) for 10,000 certificates completes in 15 minutes or less for a full run and in 2 minutes or less for an incremental run. | Load test | PS |
| NFR-REL-01 | First-attempt success of 98 percent or more in steady state. 100 percent of failures end in automatic rollback or a manual task. | Operational KPI | NEW |
| NFR-REL-02 | Matching is deterministic: the same inputs always produce the same match and confidence; no automatic deployment on ambiguous matches. | Unit and property tests | PS |
| NFR-AUD-01 | 100 percent of actions audited, tamper-evident, exportable to the SIEM, retained per policy. | Audit test | NEW |
| NFR-OPS-01 | Runbooks, monitoring and alerting for every component. Disaster recovery for CDM configuration with RPO 24 hours or less and RTO 8 hours or less (subject to platform SLA). | DR exercise | NEW |
| NFR-MNT-01 | The adapter contract is semantically versioned and backward compatible within a major version. | Contract tests | NEW |
| NFR-USA-01 | A requester can submit a standard request in 3 minutes or less using no more than 8 fields. Portal meets WCAG 2.1 AA. | Usability test | NEW |
| NFR-PRT-01 | CA, vault, executor and adapter interfaces are vendor-neutral so components can be swapped. | Design review | D1 |
| NFR-CRY-01 | Crypto-agility: algorithms and sizes are configuration. Automation copes with certificates of one month or less (frequent, daily scheduling) and with post-quantum algorithms later. | Design review | PS |

---

## 9. Data model and lifecycle

### 9.1 Entities (ServiceNow tables)

No table stores a private key or a plain-text secret. `CredentialRef` holds vault paths only.

| Entity | Key fields | Purpose |
|---|---|---|
| Certificate | cert_id, common_name, SAN set, serial, issuer, thumbprint SHA-256 and SHA-1, not_before, not_after (UTC), key algorithm and size, state, owner group, CMDB CI reference, Sectigo record reference, replaced_by | The normalised certificate identity |
| CertObservation | observation_id, certificate reference, host, store or path, binding, port, seen_at, source (Discovery, probe, adapter) | What Discovery or a probe saw where and when; drives the closed loop |
| CASourceRecord | record_id, CA, order or certificate ID, status, thumbprint, serial, SAN, validity, collected_at | Snapshot of the Sectigo record |
| MatchResult | match_id, CMDB certificate, CA record, rule (M1 to M6), confidence, state (linked, candidate, ambiguous, rejected) | Explains why two records are considered the same or a renewal |
| ReviewItem | item_id, match reference, reason, assignee, decision | Ambiguous matches and unlocated certificates awaiting a person |
| Binding | binding_id, certificate reference, target reference, service, port, SNI, store or path or secret, previous thumbprint, last verified | Where a certificate is used |
| TargetEndpoint (CMDB CI) | target_id, hostname or URL or cluster, technology, environment, criticality, zone reference, cluster reference, owner group | The place to deploy |
| DeploymentStrategy | strategy_id, binding, adapter and version, zone, executor, credential alias, key mode, activation, verification, rollback, window, owner, status, version | The unit of automation |
| DeploymentJob | job_id, request or renewal reference, binding, strategy, adapter, executor, state, attempt, backup reference, started, ended, evidence, confirmation state | One run of a deployment |
| Adapter | adapter_id, technology, version, signature SHA-256, status (approved or revoked), allowed operations, approved by | Signed adapter registry |
| Executor | executor_id, type (MID, IWS, Rundeck, Ansible, in-cluster), zone, status, capacity, last heartbeat | Where jobs run |
| Zone | zone_id, network zone, MID set, allowed adapters | Network segmentation |
| CredentialRef | alias, vault path (no secret), scope (discovery or deploy), zone, lease TTL, rotation policy | Vault reference |
| CAProfile | ca_id, type, endpoint, environment (sandbox or production), profile, credential alias, rate limits | CA configuration |
| Policy | policy_id, key rules, maximum validity, allowed CAs and domains, approval rule, renewal rule, window | Rules |
| Request and Approval | request_id, type (new, renew, revoke), state, requester, approvals | Human-driven flows |
| AuditEvent | event_id, actor, role, action, object, timestamp UTC, result, evidence reference, previous hash | Tamper-evident audit |
| LicenceUsage | period, edition, managed certificates, targets, zones, executors | Metering for commercial use (PRD-003) |

### 9.2 Lifecycle states

```text
 Discovered --> Requested/Renewal due --> [Pending approval] --> Approved
      |                                                            |
      |                       (CA issues; certificate lands in the landing queue)
      v                                                            v
   Unmanaged                                              Issued (landed)
                                                                   |  strategy exists? no -> "No strategy" (manual task)
                                                                   v
                                                              Deploying
                                                                   |  fail -> Rolled back -> incident -> retry after fix
                                                                   v
                                                        Deployed, awaiting rescan
                                                                   |  next Discovery scan shows new thumbprint + dates
                                                                   v
                                                        Confirmed by discovery  == Active
                                                                   |  renewal window reached
                                                                   v
                                                        Expiring --> Renewing --> (loop)
                                        Expired / Revoked / Retired  (terminal)
```

| State | Meaning | Exit |
|---|---|---|
| Discovered | Found by Discovery or import, not yet managed | Adopted, or marked unmanaged |
| Requested or renewal due | Request created by a person or by the renewal window | Policy ok, or rejected |
| Pending approval | Waiting for approver or change | Approved or rejected |
| Issued (landed) | Certificate at the CA and in the landing queue, validated and matched | Deploy job, or "No strategy" |
| Deploying | Adapter job running | Verified, or rolled back |
| Deployed, awaiting rescan | Live endpoint verified; waiting for Discovery to see it | Confirmed, or alert after the timeout |
| Confirmed by discovery (Active) | Discovery sees the new certificate at the location | Renewal window, revocation |
| Expiring | In the renewal window | Renewing, or expired |
| Rolled back | Deployment failed and was reverted | Incident, retry after fix |
| Expired, Revoked, Retired | End of life | None |

---

## 10. External interfaces

| Interface | Direction | Protocol and auth | Notes |
|---|---|---|---|
| CDM to ServiceNow CMDB and Discovery | Inside the instance, or remote API | Native scripted access, or REST with a dedicated integration user | Read certificate CIs and relationships; write CDM state, relations and events. |
| CDM to Sectigo | Instance or MID to CA | HTTPS REST; credentials from the vault | List, collect, enroll, renew, revoke (Appendix D). Sandbox and production profiles are separate. |
| CDM to ACME CAs (later) | Instance or MID to CA | HTTPS, ACME RFC 8555 | HTTP-01 or DNS-01. |
| ServiceNow to MID Server | Instance to MID | ECC queue; MID connects outbound over HTTPS 443 | Signed job payload; MID verifies adapter hash. |
| MID or executor to vault | To vault | HTTPS with mutual TLS; short-lived token | JIT secrets, dynamic SSH certificates. |
| MID to Windows target | To target | WinRM over HTTPS or Kerberos | JEA constrained endpoint preferred. |
| MID to Linux target | To target | SSH with signed certificates | Restricted sudo commands. |
| MID to OpenShift or Kubernetes | To API server | HTTPS with ServiceAccount token | Namespaced role and role binding. |
| MID to load balancer | To device | HTTPS REST (iControl, NITRO) | Token from the vault. |
| CDM to IWS, Rundeck, Ansible (P2) | Instance or MID to scheduler | HTTPS REST or CLI with API token in the vault | Job created with parameters; result by callback or poll. |
| CDM to SIEM | Instance to SIEM | Syslog over TLS or HTTPS | Audit stream. |
| CDM to ITSM | Inside ServiceNow | Native | Change, incident, task. |
| Users to CDM | Browser | HTTPS, SSO with MFA | Catalog, workspace, dashboards. |

---

## 11. Security and threat model

| # | Threat | Mitigation | Requirements |
|---|---|---|---|
| T1 | Stolen credentials from a MID Server, scheduler or script | Vault JIT secrets, per-zone accounts, 15-minute TTL, no secrets in scripts or variables; external schedulers also use a vault or their own secure store | NFR-SEC-04, FR-SRC-012, FR-EXE-002 |
| T2 | Modified or malicious adapter script | Signed, allow-listed, version-controlled adapters; four-eyes approval | FR-ADP-002 to 005, NFR-SEC-03 |
| T3 | Private key exposure in transit, logs or storage | Key on target; PFX only as audited exception; encrypted short-lived temp storage; log redaction | FR-KEY-001 to 003, NFR-SEC-05 |
| T4 | Wrong certificate deployed because of a bad match | Identity matching with confidence, ambiguous to review, name check, live verification, rollback | FR-SRC-004, FR-SAF-004, FR-SAF-010, NFR-REL-02 |
| T5 | Unauthorised or wrongful issuance | Policy checks, approvals, domain allow-lists, CA-side validation, segregation of duties | FR-REQ-002, FR-REQ-003, FR-ADM-001 |
| T6 | Compromised MID Server used to pivot | Outbound-only, zone segmentation, egress allow-list, hardening, minimal privilege | NFR-SEC-02, FR-ORC-004 |
| T7 | Deployment strategy tampered with to redirect a certificate | Versioned, approved strategies, four-eyes, audit, checksum in the job payload | FR-STR-002, FR-ADM-005 |
| T8 | Job payload tampering or replay | Signed payloads; MID validates signature and adapter hash; nonce and expiry | FR-ADP-002, NFR-SEC-03 |
| T9 | Insider misuse | Segregation of duties, tamper-evident audit, time-boxed break-glass | FR-ADM-001, FR-RPT-002 |
| T10 | CA, API or Discovery outage or stale data | Retry, back-off, renewal buffer, freshness checks on source data, alerts on stale sync | FR-CA-007, FR-SRC-001, NFR-AVL-03 |
| T11 | Mass renewal overload | Throttling, concurrency limits, staged rollout | FR-CA-009, FR-ORC-006, FR-ORC-009 |
| T12 | Supply-chain compromise of adapter or product dependencies | Pinned and scanned dependencies, SBOM, signed builds | FR-ADP-005, PRD-014 |
| T13 | Licence or metering data used to leak customer information | Metering carries counts only, no names or secrets | PRD-003, PRD-012 |

---

## 12. Productisation and commercial requirements

This chapter makes CDM sellable: a repeatable product with editions, licensing, distribution, support and a go-to-market. Pricing and market statements are hypotheses to validate with customers and partners (Q6).

### 12.1 Product definition and editions

| Edition | For | Includes |
|---|---|---|
| Trial and POC kit | Evaluation, proof of value in about two weeks | Test CA with landing-area behaviour, sample data and targets, scripted closed-loop demo, limited managed certificates |
| Standard | One ServiceNow instance, one CA, common stacks | Source sync and matching, strategies, closed loop, Windows, Linux and Java adapters, MID executor, vault integration, dashboards, audit |
| Enterprise | Large estates and regulated customers | Standard plus OpenShift and Kubernetes, F5 and NetScaler, IWS, Rundeck and Ansible executors, multi-zone HA, four-eyes, change integration, SIEM export, advanced reports, on-demand rescan |
| Service provider | MSPs and multi-customer operators | Enterprise plus domain separation, per-customer policies and reporting, metering API, white-label |
| Add-ons | Any edition | Additional CAs (ACME, ADCS), database, middleware and network adapters, adapter SDK and marketplace access, premium support |

### 12.2 Product and commercial requirements

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| PRD-001 | Package CDM as one scoped ServiceNow application with semantic versioning, installable and upgradeable without losing configuration, strategies or audit history. | M | P1 | NEW |
| PRD-002 | Editions and feature flags controlled by a licence entitlement. Reaching a limit produces warnings and blocks only new onboarding, never running deployments or renewals. | M | P1 | NEW |
| PRD-003 | Metering: count managed certificates, targets, zones and executors; monthly usage report; counts only, no secrets or names; tamper-evident. | M | P2 | NEW |
| PRD-004 | Domain separation for service providers: data, policies, credentials and reports separated per customer; metering per customer. | S | P3 | NEW |
| PRD-005 | Distribution through the ServiceNow Store or an application repository; meet the certification and store requirements (to be confirmed with the ServiceNow partner programme); private distribution for design partners. | M | P2 | NEW |
| PRD-006 | Compatibility matrix: supported ServiceNow releases (current and two previous), MID Server versions, target operating systems and CA API versions, with automated regression for each. | M | P1 | NEW |
| PRD-007 | Guided setup wizard: connect ServiceNow Discovery data, Sectigo, the vault, the first zone and executor, the first strategy and a dry run. Goal: first verified deployment within one working day. | M | P1 | NEW |
| PRD-008 | Trial and POC kit: test CA, sample targets and data, scripted closed-loop demo with reset. | M | P1 | MOCK |
| PRD-009 | Documentation set versioned with the product: quick start, administrator guide, security guide, adapter guides, API reference, runbooks, release notes. | M | P1 | NEW |
| PRD-010 | Training material for administrators, operators and adapter developers, and demo scripts. | S | P2 | NEW |
| PRD-011 | Supportability: diagnostics bundle without secrets, health-check page, log levels, correlation IDs, support runbook, defined severity levels and response targets. | M | P2 | NEW |
| PRD-012 | Opt-in telemetry of anonymous usage and health metrics, no certificate content or secrets, documented and switchable off. | S | P2 | NEW |
| PRD-013 | Adapter SDK, sample adapter, certification process for partner-built adapters and marketplace listing rules. | S | P3 | NEW |
| PRD-014 | Product security: secure development lifecycle, dependency scanning and SBOM, static and dynamic testing, independent penetration test before each major release, vulnerability disclosure and patch timelines, signed releases. | M | P1 | NEW |
| PRD-015 | Vendor assurance: SOC 2 Type II or ISO 27001 for the product organisation, security whitepaper and standard questionnaire answers. | S | P3 | NEW |
| PRD-016 | Upgrade and migration: backward-compatible data model, migration scripts, ability to roll back an upgrade, no loss of history. | M | P2 | NEW |
| PRD-017 | Documented REST API and events (webhooks, ServiceNow events) and signed extension points (pre and post hooks) for customer integrations. | S | P2 | NEW |
| PRD-018 | White-label for partners: name, logo and notification templates. | S | P2 | NEW |
| PRD-019 | Localisation of portal and notifications. | C | P3 | NEW |
| PRD-020 | Legal and compliance for sale: third-party licence inventory, end-user licence terms, data-processing terms, cryptography export review. | M | P1 | NEW |
| PRD-021 | Sizing guide and reference architectures (small, medium, large; number of MID Servers and executors). | S | P2 | NEW |
| PRD-022 | Customer value dashboard: certificates auto-renewed, confirmed-by-discovery rate, hours saved, outages avoided (estimated), coverage by technology. | M | P1 | NEW |
| PRD-023 | Sales enablement: ROI calculator, demo environment, reference architecture and security review pack. | S | P3 | NEW |

### 12.3 Licensing and pricing hypotheses (to validate)

| Value metric | Idea | Pros | Cons |
|---|---|---|---|
| Per managed certificate per year | Tiered bands | Matches customer value and CA billing habits | Metering must be exact |
| Per target (server, cluster, device) | Tiered bands | Easy to understand | Penalises large estates with few certificates |
| Per zone or executor | Platform fee | Predictable | Weakly linked to value |
| Edition base plus metric | Standard, Enterprise and Service provider bases with certificate bands | Simple sales motion, room to upsell | Needs clear feature fences |
| Add-ons | Extra CAs, premium adapters, SDK, support | Grows revenue per customer | More SKUs to manage |

No price points are proposed here. They must come from customer interviews, partner feedback and competitor checks.

### 12.4 Business case model (illustrative)

Value inputs: number of managed certificates, renewals per certificate per year (shorter validity means more), manual effort per renewal, outage cost, share of certificates covered by an approved strategy.

Illustrative example only: 1,500 certificates with 3 renewals a year is 4,500 renewals. At 1.5 hours each that is 6,750 hours a year. If automation covers 85 percent, about 5,700 hours are saved a year, before counting avoided outages and audit effort. As certificate lifetimes shrink, the number of renewals rises, which increases the value. The product's value dashboard (PRD-022) reports the real numbers for each customer.

### 12.5 KPIs

| KPI | Target |
|---|---|
| Expiry-caused outages on managed certificates | 0 |
| Automatic renewal rate for certificates with a strategy | 95 percent or more |
| Confirmed-by-discovery rate | 98 percent or more |
| Deploy-to-confirm time | 36 hours or less, minutes with on-demand rescan |
| First-attempt deployment success | 98 percent or more |
| Time to first verified deployment for a new customer | 1 working day or less |
| Time to add a new adapter (with the SDK) | To be measured, goal a few weeks |

### 12.6 Go-to-market considerations

- **Segments:** ServiceNow customers that use Sectigo (fastest sale), regulated industries, managed service providers, large estates with shrinking certificate lifetimes.
- **Channels:** ServiceNow Store, direct sales, ServiceNow and Sectigo partners and resellers, managed service providers.
- **Sales motion:** trial kit and two-week proof of value (closed-loop demo), pilot with a design partner, production roll-out with a first strategy per technology.
- **Proof points to build:** a reference customer, the value dashboard, an independent penetration test summary, a compatibility matrix.
- **Differentiation to protect:** the CMDB-driven closed loop, signed adapters, vault security, one product for many technologies.
- **Validation needed:** market size, willingness to pay, competitor comparison, ServiceNow partner terms (Q6).

---

## 13. From POC to product: roadmap

### 13.1 What the POC must still prove

| POC change | Closes | Requirement |
|---|---|---|
| Replace `mock_sectigo.ps1` with a test CA that signs real CSRs, returns real PEM and behaves like a landing area | G1, G6 | FR-CA-010 |
| Add a CMDB-like source (or real PDI data) holding certificate CIs with thumbprint, SAN, location and dates | G9 | FR-SRC-001 |
| Implement identity matching and the landing queue | G9 | FR-SRC-003 to FR-SRC-005 |
| Add a deployment strategy record and derive technology and location from it | G7 | FR-STR-001, FR-ORC-003 |
| Generate key and CSR on the Windows target, install, bind IIS, set the key permission, verify | G2 | AD-WIN-04 to AD-WIN-07 |
| Upgrade the Linux simulator and add a real Linux target with Apache: owner, permission, graceful reload | G8 | AD-LNX-05 to AD-LNX-07 |
| Move WinRM to HTTPS, remove Basic and AllowUnencrypted | G3 | AD-WIN-02 |
| Replace the single admin password with a vault alias; split discovery and deployment accounts | G4 | FR-INV-006, NFR-SEC-04 |
| Replace pasted script text with a registered adapter taking parameters | G5 | FR-ADP-002 to 004 |
| Prove the closed loop: after deployment, a new scan or CMDB read shows the new thumbprint and dates | G9 | FR-LOOP-001 to FR-LOOP-003 |

### 13.2 POC exit criteria

1. A certificate nearing expiry in the (simulated or real) CMDB is matched by identity to a renewed certificate held by the test CA, and it is unique.
2. CDM picks it up by API and deploys it on Windows IIS (store, key permission, HTTPS binding) and on Linux Apache (owner, permission, graceful reload) with no manual step.
3. The live endpoint shows the new thumbprint immediately, and the next scan or CMDB read shows the new certificate with the new dates, so CDM marks "Confirmed by discovery".
4. A forced failure (wrong SAN, service that will not reload) rolls back automatically and is verified.
5. No password or private key appears in any script, flow variable, log or ECC payload.
6. Technology and location come from the strategy and CMDB record; changing the record changes the route without editing the flow.

### 13.3 Roadmap

Durations are indicative and depend on the answers in chapter 16.

| Phase | Duration | Product scope | Commercial scope |
|---|---|---|---|
| P0 POC | Now, 1 to 2 weeks | Fix G1 to G3 and G9; test CA; matching; closed-loop demo on Windows IIS and Linux Apache | Trial kit v0, demo script |
| P1 MVP | 8 to 10 weeks | Sectigo API (sandbox and production), ServiceNow sync, matching, landing queue, strategy registry, Windows IIS and store, Linux Apache and nginx, Java, MID executor, vault, closed loop, manual fallback, dashboards, audit, setup wizard | Documentation v1, penetration test, design-partner pilot, licence entitlement, legal pack |
| P2 Expansion | 8 to 10 weeks | OpenShift and Kubernetes with the service account kit, IWS and Rundeck and Ansible executors, F5 and NetScaler, multi-zone HA, approvals and change, on-demand rescan, four-eyes, ACME | Editions, metering, ServiceNow Store packaging, supportability, adapter SDK beta, training |
| P3 Enterprise | 8 to 12 weeks | Databases, middleware, network devices, ADCS, domain separation, DR and load tests | Service provider edition, marketplace, SOC 2 or ISO 27001 work, sales enablement, localisation |
| P4 Optimise | Ongoing | Shorter certificate lifetimes, crypto-agility and post-quantum readiness, self-service growth | Pricing tuning, partner programme, case studies |
| Deferred | Not scheduled | Apple (macOS, iOS, iPadOS) via MDM, cloud services | Decide after P2 based on demand |

---

## 14. Test and acceptance strategy

| Level | What is tested | Approach |
|---|---|---|
| Unit | Adapter functions, parsing, validation, matching rules, policy engine | Pester (PowerShell), shell test frameworks, ServiceNow script tests |
| Integration | CA connector against the test CA and Sectigo sandbox; ServiceNow CMDB sync; vault; executor | Automated pipeline with the test CA |
| End to end | Match, deploy, verify and rediscovery confirmation on each platform, including failure paths | Lab targets: Windows with IIS, Linux with Apache, Java app, OpenShift or kind, F5 virtual edition |
| Failure injection | Bad certificate, wrong SAN, service will not reload, MID failure mid-job, CA timeout, stale CMDB | Scripted faults; expect rollback, manual fallback or alert |
| Security | Secret and key leakage, log redaction, adapter tampering, privilege boundaries, network exposure | Secret scanning, tamper tests, penetration test before P1 go-live |
| Performance and resilience | Volume, concurrency, sync time, MID failover, disaster recovery | Load and chaos tests |
| Product | Licence limits, upgrade and rollback, multi-tenant separation, setup wizard time | Release checklist |
| User acceptance | Requester, approver, operator and auditor journeys | Scripted UAT with sign-off |

### 14.1 Representative acceptance tests

| ID | Scenario | Expected result |
|---|---|---|
| TC-01 | New certificate for a Windows IIS site | Key on host, CSR signed, bound, key permission set, thumbprint verified on 443, audit complete |
| TC-02 | Renewed certificate for an Apache server waiting in the landing queue | Picked up by API, matched, deployed with correct owner and permission, graceful reload, old certificate backed up |
| TC-03 | SAN mismatch on deployment | Refused before change; no service impact |
| TC-04 | Service fails to reload after install | Automatic rollback, verified, incident created |
| TC-05 | Java keystore update | Chain imported in order, alias correct, application reloaded, verified |
| TC-06 | OpenShift secret update with a failing pod (P2) | Rollout stops; previous Secret restored; verified |
| TC-07 | F5 HA pair deployment (P2) | New object, profile updated, sync confirmed, both units verified |
| TC-08 | Technology or location without a strategy | Status "No strategy" and a manual task; never silent |
| TC-09 | MID Server killed mid-deployment | Job resumes on the peer or rolls back within 5 minutes |
| TC-10 | Unsigned or modified adapter | Execution blocked, alert raised |
| TC-11 | Secret scan of logs, ECC payloads and flow context after a full run | No keys, passwords or PKCS#12 content |
| TC-12 | Requester approves own request | Denied by segregation of duties |
| TC-13 | Closed loop: deployment, then the next Discovery scan | CMDB shows the new thumbprint and dates; state "Confirmed by discovery" |
| TC-14 | Two Sectigo certificates fit one expiring CMDB certificate | Ambiguous; review queue; no automatic deployment |
| TC-15 | Discovery has not rescanned after 36 hours | Alert, live re-probe, escalation, not marked done |
| TC-16 | One-month certificate | Renewal window scales (about 10 days), not 30 |
| TC-17 | Certificate in the CMDB unknown to Sectigo, and Sectigo certificate with no location | Reported as unmanaged and unlocated |
| TC-18 | Deployment through Rundeck or IWS (P2) | Same result envelope; CDM verifies independently |
| TC-19 | Licence limit reached | Warning and no new onboarding; running renewals continue |
| TC-20 | Product upgrade and rollback | Configuration, strategies and audit history preserved |

### 14.2 Phase acceptance

| Phase | Accepted when |
|---|---|
| P0 POC | The exit criteria in 13.2 are met |
| P1 MVP | TC-01 to TC-05, TC-08 to TC-17 pass against the real Sectigo sandbox and a real CMDB; security review and penetration test closed |
| P2 Expansion | TC-06, TC-07, TC-18 to TC-20 pass; multi-zone HA passes TC-09; ServiceNow Store packaging accepted |
| P3 Enterprise | Databases, middleware and network adapters delivered; DR and load tests pass; service provider edition validated |

---

## 15. Risks and dependencies

| # | Risk or dependency | Impact | Mitigation |
|---|---|---|---|
| R1 | The PDI has limits (it can be reclaimed after inactivity) and may lack Integration Hub or Orchestration steps such as the PowerShell action assumed in the plan | POC blocked or non-representative | Confirm plugins (Q3); keep a scripted-REST and MID script fallback; back up update sets |
| R2 | No Sectigo sandbox or API access yet, or tenant behaviour differs from the documentation (key reuse, renewal, landing area) | P1 delayed | Use the test CA meanwhile; request the sandbox now (Q1) |
| R3 | Discovery data quality: thumbprint, SAN or timestamps missing or stale in the CMDB | Matching fails or is ambiguous | Check the data now (Q2); allow adapter and probe data to fill gaps; alert on stale sync |
| R4 | Discovery runs too rarely for the closed loop | Slow confirmation | On-demand rescan (FR-LOOP-005); tune schedule; live probe as interim proof |
| R5 | Vault product undecided | Blocks secure credentials | Start with a local vault; keep the interface neutral (Q4) |
| R6 | A Windows laptop MID Server and loopback targets are unrepresentative | False confidence | Real Linux and a second Windows host early in P1 |
| R7 | Scope creep from the many-technologies requirement | Late delivery | Strict phasing; manual fallback covers the long tail; Apple and cloud deferred |
| R8 | Certificate lifetimes keep shrinking | Higher renewal volume | Daily scheduling, throttling, adaptive windows |
| R9 | Adapter maintenance burden as platforms change | Technical debt, support cost | Contract versioning, tests, ownership per adapter, SDK |
| R10 | Firewall and network approvals for MID Servers or executors per zone | Delays | Raise early; outbound-only design simplifies approval |
| R11 | Overlap with ServiceNow's own certificate features or with CA-native agents | Market positioning | Position as the deployment and verification layer; validate competitors (Q6) |
| R12 | ServiceNow Store certification timing and partner terms | Go-to-market delay | Start partner conversations early; private distribution first |
| R13 | Pricing and market fit unvalidated | Revenue risk | Design-partner pilots, customer interviews (Q6) |
| R14 | Customer MID capacity and separation of discovery and deployment MIDs | Performance and security | Sizing guide; separate MID sets where required (Q15) |
| R15 | Skills across ServiceNow, PKI, Windows, Linux, Java and OpenShift | Quality risk | Pair engineers with platform owners; review gates |

---

## 16. Decisions and open questions

Each has a default that will be used if you do not decide otherwise.

| # | Question | Default if not answered |
|---|---|---|
| Q1 | How does Sectigo deliver the renewed certificate today: API, network agent or landing area? Does the renewal reuse the previous CSR and key, or does Sectigo generate the key and hand over a PKCS#12? Is auto-renew or early issuance configured, and what is the exact Sectigo product and tenant (sandbox available)? | API pickup; key mode A, with mode B as exception |
| Q2 | In your ServiceNow Discovery: which certificate class and fields exist, are thumbprint, serial, SAN and exact validity timestamps stored, how often does the scan run, and can a single target be rescanned on demand? Which locations are discovered (stores, files, endpoints)? | Assume thumbprint, serial, SAN and dates are available; daily scan |
| Q3 | Which ServiceNow licences and plugins are available (Discovery, Integration Hub, Orchestration, the PowerShell step)? Should the ServiceNow certificate-management offering be evaluated as build versus buy? | Build a scoped application |
| Q4 | Which vault: HashiCorp Vault, CyberArk, Azure Key Vault, or the ServiceNow credential store with an external vault? | HashiCorp Vault behind a neutral interface |
| Q5 | Do IWS, Rundeck and the existing OpenShift jobs stay in the picture? Which applications already use them, and can the scripts and role bindings be shared? | CDM treats them as optional executors in P2 |
| Q6 | How do you want to sell CDM: ServiceNow Store, direct, or through partners and managed service providers? Who is the first design-partner customer? What is the preferred pricing metric? | Design-partner pilot first; Store packaging in P2 |
| Q7 | How many targets by technology (Windows IIS, Linux Apache and nginx, Java, OpenShift, F5) and what is the mix of certificate validity (one month, one year, longer)? | Order as in the roadmap |
| Q8 | The original wording said "iOS". Apple is now deferred. Was Cisco IOS meant? | Cisco IOS as network devices in P3 |
| Q9 | Are exceptions to target-side key generation acceptable (appliances or CA-delivered PKCS#12)? | Yes, only under FR-KEY-003 |
| Q10 | How many network zones, where do MID Servers and executors sit, and what is the firewall change lead time? | Three zones: DMZ, internal, containers |
| Q11 | Approvals and change: use ServiceNow Change? May non-production deploy without approval? | ServiceNow Change; non-production auto-approved |
| Q12 | Which compliance regimes apply (PCI DSS, ISO 27001, SOC 2, HIPAA, others)? | ISO 27001 and SOC 2 mapping |
| Q13 | What defines POC success, by when, and who is the demo audience? What is the product name? | POC exit criteria in 13.2; working name CDM |
| Q14 | The screenshots are cut off: data1.jpeg ends mid-sentence and data3.jpeg stops at item 9. Can you share the remaining text? | Manual-task interpretation and no further principles |
| Q15 | Will deployment use the same MID Servers as Discovery, or a separate MID set with separate accounts (principle 1)? Will production MID Servers run on Windows or Linux? | Separate accounts; Linux MIDs for Linux zones, Windows where WinRM is needed |
| Q16 | Which other CAs will be needed later (ACME CAs, internal ADCS, others)? | Sectigo first; ACME in P2, ADCS in P3 |

---

## Appendix A: Adapter contract (draft)

Every adapter, run by any executor, implements the same operations and returns the same envelope. Inputs are typed parameters, never script text.

```json
{
  "request": {
    "job_id": "JOB0012345",
    "operation": "install",
    "adapter": {"id": "windows-iis", "version": "1.3.0", "sha256": "<hash>"},
    "target": {"id": "CI0009876", "host": "app01.example.com", "zone": "internal", "technology": "windows"},
    "binding": {"service": "iis", "site": "Default Web Site", "port": 443, "sni": "app.example.com", "store": "LocalMachine\\My"},
    "certificate": {"pem_chain": "<public certificate and chain only>", "thumbprint": "<sha256>"},
    "key_mode": "A",
    "credential_alias": "cdm/internal/windows/deploy",
    "timeout_seconds": 300
  },
  "response": {
    "job_id": "JOB0012345",
    "status": "success",
    "error_code": null,
    "evidence": {
      "thumbprint_before": "...",
      "thumbprint_after": "...",
      "presented_san": ["app.example.com"],
      "not_after": "2027-03-19T00:00:00Z",
      "key_acl": ["IIS APPPOOL\\app"]
    },
    "cleanup": {"temp_files_removed": true, "session_closed": true}
  }
}
```

`operation` is one of precheck, backup, generate_csr, install, activate, verify, rollback, cleanup, discover. `status` is one of success, failed, rolled_back, manual_required.

## Appendix B: Deployment strategy (draft example)

```json
{
  "strategy_id": "STR-000123",
  "version": 3,
  "status": "approved",
  "binding": {
    "certificate_identity": {"common_name": "app.example.com", "san": ["app.example.com", "www.example.com"]},
    "location": {"host": "app01.example.com", "service": "apache", "port": 443, "cert_path": "/etc/pki/tls/certs/app.crt", "key_path": "/etc/pki/tls/private/app.key"}
  },
  "adapter": {"id": "linux-apache", "version": "1.2.0"},
  "zone": "internal",
  "executor": "mid",
  "credential_alias": "cdm/internal/linux/deploy",
  "key_mode": "A",
  "file_owner": {"cert": "root:root 0644", "key": "root:apache 0640"},
  "activation": {"method": "graceful-reload", "pre_test": "apachectl configtest"},
  "verification": {"probe": "tls", "expect": ["thumbprint", "san", "chain", "expiry"], "confirm_by_discovery": true, "confirm_timeout_hours": 36},
  "rollback": {"method": "restore-backup"},
  "window": "CHG-standard",
  "owner_group": "web-platform",
  "notify": ["web-platform@example.com"]
}
```

## Appendix C: Example policy (draft)

```json
{
  "policy_id": "POL-PROD-WEB",
  "min_key": {"rsa": 3072, "ecdsa": ["P-256", "P-384"]},
  "max_validity_days": 200,
  "allowed_ca": ["sectigo-prod"],
  "allowed_domains": ["*.example.com"],
  "wildcard": {"allowed": false, "approval": "pki_admin"},
  "approval": {"production": "change_manager", "non_production": "auto"},
  "renewal": {"start_before_days_max": 30, "start_before_fraction_of_lifetime": 0.33, "floor_days": 3},
  "key_reuse": false,
  "require_strategy": true,
  "require_verification": true,
  "require_discovery_confirmation": true,
  "rollback_on_failure": true
}
```

## Appendix D: Sectigo Certificate Manager API (indicative)

The connector uses the Sectigo Certificate Manager REST API. The list below is indicative and must be verified against the current Sectigo documentation and your tenant before implementation (Q1).

| Operation | Indicative endpoint | Notes |
|---|---|---|
| Authentication | Headers: login, password (or API key), customerUri | Stored as vault aliases only (FR-SRC-012) |
| List and status | `GET /api/ssl/v1` (filters) | Used to build the landing queue and for reconciliation |
| Collect | `GET /api/ssl/v1/collect/{sslId}?format=...` | Format selects PEM with chain or other encodings; issuance can be asynchronous |
| Enroll | `POST /api/ssl/v1/enroll` | CSR, certificate type or profile ID, term, external requester, SAN list |
| Renew | `POST /api/ssl/v1/renewById/{sslId}` | A new CSR is preferred (FR-KEY-006); behaviour for key reuse to be confirmed |
| Revoke | `POST /api/ssl/v1/revoke/{sslId}` | Reason code required |

## Appendix E: ServiceNow data needed from Discovery and the CMDB (indicative)

Field names differ by release and by whether the certificate application is installed. Confirm the exact class and fields in your instance (Q2).

| Data | Needed for |
|---|---|
| Certificate CI: common name, subject and issuer DN | Matching rules M1, M2 |
| Thumbprint or fingerprint (SHA-1 and SHA-256), serial number | M1, exact identity |
| SAN set | M2 lineage and name check |
| Valid from and valid to (exact UTC) | M2 order, expiry, closed-loop confirmation |
| Key algorithm and size, signature algorithm | Policy checks |
| Relationship to the server, application or service (uses and used by) | Location, bindings |
| Store, path or port where the certificate was found | Deployment location |
| Discovery source and last-scanned timestamp | Freshness and the confirmation rule (FR-LOOP-002) |

## Appendix F: Source traceability

| Source | Main requirements it drives |
|---|---|
| Problem statement (PS), latest message | FR-SRC, FR-STR, FR-LOOP, FR-EXE, FR-REQ-005, FR-SAF-009, FR-KEY-009, AD-WIN-06, AD-WIN-07, AD-LNX-05 to AD-LNX-07, AD-K8S-02, chapters 2 and 4 |
| Promp.md.txt (PLAN) | FR-CA-002, FR-ORC-002, FR-ORC-003, FR-ADP-006, AD-WIN-12, chapter 13 |
| POC_SETUP_STATUS.md (SETUP) | FR-CA-004, NFR-SEC-01, AD-WIN-02, findings G3 and G4 |
| mock_sectigo.ps1 (MOCK) | FR-CA-010, PRD-008, finding G1 |
| data1.jpeg (D1) | FR-INV-004 to 006, FR-ADP-001, FR-ADP-006, FR-NTF-003, FR-NTF-004, NFR-PRT-01 |
| data2.jpeg (D2) | FR-KEY-001 to 003, FR-SRC-012, FR-ORC-004, FR-SAF-008, NFR-SEC-01 to 05, NFR-AVL-01, NFR-AVL-02, FR-ADM-006 |
| data3.jpeg (D3) | FR-ADP-002 to 005, FR-SAF-001 to 007, FR-ORC-009, FR-ADM-005, NFR-SEC-03 |
