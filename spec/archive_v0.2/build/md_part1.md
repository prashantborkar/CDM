# Certificate Deployment Manager (CDM): Product Requirements and Specification

| Item | Detail |
|---|---|
| Version | 0.2 (draft for review). Supersedes v0.1. |
| Date | 2026-09-21 |
| Status | Draft. Decisions needed are in chapter 16. |
| Based on | Your problem statement (latest message), Promp.md.txt, POC_SETUP_STATUS.md, mock_sectigo.ps1, data1.jpeg, data2.jpeg, data3.jpeg |
| Format | Markdown only, no images. Flows are drawn as text diagrams so they render everywhere. |

> Written for: you and the team who will decide, build and later sell CDM. It is a product specification, not only an internal POC note.

**Conventions.** Requirement IDs: `FR-<area>-<nnn>` functional, `AD-<platform>-<nn>` adapter, `NFR-<area>-<nn>` non-functional, `PRD-<nnn>` product and commercial. **Pri:** M = Must, S = Should, C = Could. **Phase:** P1 = MVP, P2 = expansion, P3 = enterprise and commercial hardening (P0 = the existing POC). **Src:** PS = your problem statement, PLAN = Promp.md.txt, SETUP = POC_SETUP_STATUS.md, MOCK = mock_sectigo.ps1, D1/D2/D3 = data1/2/3.jpeg, NEW = added by this analysis.

## Contents

- [0. Summary at a glance](#0-summary-at-a-glance)
- [1. Introduction](#1-introduction)
- [2. Problem statement and product opportunity](#2-problem-statement-and-product-opportunity)
- [3. Analysis of the POC folder](#3-analysis-of-the-poc-folder)
- [4. Solution concept](#4-solution-concept)
- [5. Architecture](#5-architecture)
- [6. Functional requirements](#6-functional-requirements)
- [7. Platform adapter specifications](#7-platform-adapter-specifications)
- [8. Non-functional requirements](#8-non-functional-requirements)
- [9. Data model and lifecycle](#9-data-model-and-lifecycle)
- [10. External interfaces](#10-external-interfaces)
- [11. Security and threat model](#11-security-and-threat-model)
- [12. Productisation and commercial requirements](#12-productisation-and-commercial-requirements)
- [13. From POC to product: roadmap](#13-from-poc-to-product-roadmap)
- [14. Test and acceptance strategy](#14-test-and-acceptance-strategy)
- [15. Risks and dependencies](#15-risks-and-dependencies)
- [16. Decisions and open questions](#16-decisions-and-open-questions)
- [Appendices A to F](#appendix-a-adapter-contract-draft)

---

## 0. Summary at a glance

**The problem in one paragraph.** A company runs many applications on many servers and technologies. Every certificate has a validity, from one month to a year or more, and must be renewed before it expires. The issuing CA (Sectigo) can issue the renewed certificate early and keep it ready in a landing area, but it does not know where the old certificate is installed. ServiceNow Discovery and the CMDB know exactly where each certificate lives, when it expires and on which server, but they only scan and report: they cannot issue or deploy anything. Nobody joins the two, so renewals are manual, late or missed.

**The product in one paragraph.** CDM is the missing link. It reads the certificate footprint from ServiceNow (location, thumbprint, SAN, dates) and from Sectigo (issued and renewed certificates), matches them by certificate identity, picks up the new certificate from Sectigo by API, and deploys it through the MID Server that already has downstream access, using a technology-specific, signed adapter (Windows IIS, Linux Apache, Java and more). It verifies the result immediately, and the next day the ServiceNow Discovery scan sees the new certificate with the new dates, which proves the deployment worked. That is a closed loop.

```text
      Sectigo (issues)                                ServiceNow Discovery + CMDB (knows where)
      knows WHAT was issued                           knows WHERE it is, when it expires
      cannot know WHERE it is installed               cannot issue or deploy
                 \                                            /
                  \_____________  CDM  ______________________/
                     match by identity, pick up by API,
                     deploy via MID Server + signed adapter,
                     verify now, confirm by next-day rescan
                                   |
                                   v
             Windows/IIS   Linux/Apache   Java   OpenShift   F5   ...
```

**What is in scope now.** Windows (IIS and certificate store), Linux (Apache, nginx), Java keystores in the first release; OpenShift and Kubernetes, F5 and external schedulers (IWS, Rundeck) next; databases and network devices later. **Deferred for now, as you asked:** Apple (macOS, iOS) and cloud services. They stay out of the roadmap but the design does not block them (section 7.9).

**What changed compared with v0.1.** (1) The product is now defined by your two-source model (Sectigo plus ServiceNow) and the closed-loop confirmation by rediscovery. (2) API is the preferred way to pick up certificates. (3) A deployment strategy is the unit of automation, as in the OpenShift and Rundeck/IWS pattern you described. (4) External schedulers are supported as executors next to the MID Server. (5) Apple and cloud are deferred and Java moves into the MVP. (6) A full productisation chapter (packaging, licensing, distribution, support, go-to-market) was added so the product can be sold.

**Requirement counts.** {{COUNTS}}

> **Please answer first (chapter 16):** Q1 how Sectigo delivers the renewed certificate and key today (API, network agent or landing area), Q2 whether ServiceNow Discovery already stores thumbprint and SAN for your certificate CIs, Q3 licences and plugins, Q4 vault, Q5 whether IWS or Rundeck stays in the picture, and Q6 how you want to sell CDM (ServiceNow Store, direct or through partners).

---

## 1. Introduction

### 1.1 Purpose

This document specifies the requirements for the Certificate Deployment Manager (CDM): a secure, generic, sellable product that connects the certificate source of truth for issuance (Sectigo) with the source of truth for location (ServiceNow CMDB and Discovery) and automatically deploys and verifies renewed certificates on many technologies. It is written to be reviewed and corrected before implementation, and to serve later as the basis for product documentation and sales material.

### 1.2 Scope

**In scope**

- Reading certificate data from ServiceNow (CMDB, Discovery) and Sectigo (API), matching certificates by identity, and detecting renewal candidates and gaps.
- Picking up issued or renewed certificates from Sectigo, with API as the preferred method.
- Deployment strategies, executors (MID Server first, external schedulers next) and technology adapters.
- Windows (certificate store, private key permission, IIS HTTPS binding), Linux (Apache, nginx: key, owner, file permission, graceful reload), Java (keystores) in the MVP; OpenShift or Kubernetes, F5 and NetScaler next; databases, middleware and network devices later.
- Pre-check, backup, rollback, live verification, cluster awareness, and confirmation by the next ServiceNow Discovery rescan.
- Secure credentials and keys: vault, no permanent private keys on MID Servers, network zones, signed adapters.
- Manual fallback, notifications, audit, reporting, administration.
- Productisation: editions, licensing, distribution, support, documentation, go-to-market (chapter 12).

**Deferred by decision (kept out of the roadmap for now)**

- Apple platforms (macOS, iOS, iPadOS) through MDM.
- Cloud services (Azure, AWS, GCP certificate services).

**Out of scope**

- Operating a CA. CDM consumes CAs.
- Replacing ServiceNow Discovery. CDM consumes Discovery results.
- Code-signing, document-signing, S/MIME and SSH certificate workflows (not prevented later).
- A general privileged-access-management or endpoint-management product.

### 1.3 Audience

Product owner, architects, ServiceNow developers, PKI and security engineers, platform teams (Windows, Linux, Java, OpenShift), and later product, sales and support staff.

### 1.4 Definitions

| Term | Meaning |
|---|---|
| CA | Certificate authority that issues certificates. Sectigo is the first one. |
| Landing area / landing queue | Where a certificate that the CA has issued or renewed waits until it is deployed. In CDM it is the queue of issued certificates that are not yet deployed. The problem statement calls the CA-side counterpart the network agent or landing agent (to be confirmed, Q1). |
| Discovery | ServiceNow Discovery and certificate scanning that finds certificates, their location, expiry, thumbprint and server, and stores them as CIs in the CMDB. |
| CMDB | ServiceNow Configuration Management Database. |
| CDM | Certificate Deployment Manager, this product. |
| MID Server | ServiceNow agent inside the customer network. It has downstream access to servers and talks to the instance by outbound HTTPS only (ECC queue). |
| Executor | The component that actually runs a deployment job: a MID Server by default, or an external scheduler such as IBM Workload Scheduler (IWS) or Rundeck. |
| Adapter | A signed, versioned, technology-specific deployment component (for example Windows IIS, Linux Apache, Java) behind one contract. |
| Deployment strategy | The recorded, approved way to deploy one certificate at one location: adapter, location, credential alias, key mode, activation method, verification, rollback. |
| Binding | The link between a certificate and a place where it is used: server, service, port, store path or secret. |
| Identity | The attributes that make a certificate unique: thumbprint (fingerprint), serial and issuer, common name, SAN set, exact validity timestamps. |
| Closed loop | Deploy, verify now, then confirm by the next Discovery rescan that the new certificate is seen at the location. |
| CSR | Certificate signing request. Contains the public key, never the private key. |
| PKCS#12 (PFX) | Password-protected bundle of certificate and private key. |
| Zone | A network segment with its own MID Servers (for example DMZ, internal, container platform). |
| JIT credential | Credential fetched from the vault just in time, short-lived, automatically revoked. |
| DCV | Domain control validation by the CA. |
| SAN | Subject Alternative Name: names a certificate is valid for. |
| VIP | Virtual IP of a load balancer or cluster. |
| PDI | ServiceNow Personal Developer Instance used for the POC. |

---

## 2. Problem statement and product opportunity

### 2.1 The problem

The problem statement, cleaned up and made explicit:

1. The company runs a large number of applications on different servers and technologies.
2. Every certificate has a validity: some last one month, others one year or more. Before the end of that validity each one must be renewed and the new certificate must be installed where the old one was.
3. The sender and the receiver of a certificate each have authority: the issuing CA decides what is issued, and the receiving server decides what it presents and trusts. Both sides must end up consistent.
4. The issuing CA (Sectigo) has an easy renewal capability. It can issue the certificate before it expires and hold it ready (the landing area, delivered for example through a network agent or landing agent). Sectigo knows what it issued but not where it is used.
5. ServiceNow Discovery scans the infrastructure and knows, for every certificate, where it is, when it expires and on which server. Discovery is only a scanning tool: it cannot issue or deploy a certificate.
6. So the two systems each hold half of the answer. Today the renewal is done about one month before expiry by hand, joining what Sectigo has issued with what ServiceNow knows about location.

### 2.2 Two systems, each half the answer

| | Sectigo (issuing CA) | ServiceNow Discovery and CMDB | CDM (this product) |
|---|---|---|---|
| Knows | What was issued: name, thumbprint, serial, SAN, validity, order, status | Where each certificate is: server, store or path, binding, expiry, thumbprint, SAN, discovery timestamps | Both, plus intent, strategy, job history |
| Can do | Issue and renew early, keep the new certificate ready, revoke | Scan on a schedule, alert on expiry, relate certificates to servers | Match, pick up, deploy, verify, confirm, report |
| Cannot do | Know where the certificate is installed | Issue a certificate or deploy one | Replace the CA or Discovery |
| Access to servers | Only through an agent, if installed | Through MID Servers with downstream credentials | Through MID Servers and executors, with vault credentials |

### 2.3 The gap

```text
 Day -30 (renewal window)                                   Today, without CDM

 ServiceNow CMDB:  "Cert X, thumbprint T1, SAN a.example.com,   Someone opens both tools,
                    server app01, IIS binding :443, expires D"   compares names and dates by hand,
                                                                downloads the certificate,
 Sectigo:          "Cert X' issued, thumbprint T2, SAN a.example.com,   remotes into the server,
                    valid from D-30 to D+365, ready in landing area"   installs and binds it,
                                                                and hopes nothing was missed.
 Nobody links T1 (where it is) to T2 (the replacement) and deploys it.
```

### 2.4 What the tool must do (core behaviour)

This is your description turned into the product's core behaviour.

1. **Access both systems.** CDM can read from ServiceNow and from Sectigo.
2. **Use the shared identity.** Every certificate has a footprint (fingerprint or thumbprint), SAN, exact timestamps and a name. That information exists in both ServiceNow and Sectigo. CDM picks it up from ServiceNow, and treats the certificate as unique by that identity.
3. **Find the replacement in Sectigo.** For a certificate that is nearing expiry in ServiceNow, CDM finds the matching renewed certificate at Sectigo and picks it up (by API).
4. **Deploy where it lives.** ServiceNow knows the certificate name and location, and Discovery is done by a MID Server that has access downstream. CDM goes there, through the MID Server, and deploys the certificate once more (the new one).
5. **Confirm by rediscovery.** The next day the ServiceNow Discovery scan runs again. If it now finds the new certificate at that location, with the new dates and thumbprint, the deployment is proven. CDM records that and closes the case. If not, CDM alerts.
6. **Support many technologies.** Not one technology: each has its own way (see 2.5, 4.3 and chapter 7).

### 2.5 The reference pattern that already exists (OpenShift with a scheduler)

You described how automatic deployment was already done for OpenShift with Rundeck and a scheduler. It is a useful pattern, and CDM generalises it.

| Existing pattern (as described) | What it shows | How CDM generalises it |
|---|---|---|
| OpenShift: a service account and its role binding are created (a standard) and handed over | Least-privilege, standard access for the deployer | Ship a standard, least-privilege service account and role binding manifest for OpenShift and Kubernetes (AD-K8S-02, FR-EXE-004) |
| The scheduler (IWS) goes to Sectigo and asks: is there a new certificate? | Pick-up is driven by a poll of the CA | CDM polls the Sectigo API (FR-SRC-002) and builds a landing queue |
| When a new certificate arrives, the scheduler checks whether a deployment strategy is in place | Automation only where a strategy exists | Deployment strategy is a first-class object; no strategy means no silent action (FR-STR-001 to FR-STR-003) |
| If yes, a job is written and a script is provided to run | Job plus script per application | A signed, versioned adapter takes typed parameters; no free-text script (FR-ADP-002 to FR-ADP-004) |
| The scheduler runs the script with the location, an ID and a password | Credential handed to the scheduler | Credentials are vault aliases, resolved just in time, per zone (NFR-SEC-04); a scheduler can still be the executor (FR-EXE-002) |

**Difference.** The existing pattern is built application by application. CDM is one governed product that does the same across Windows, Linux, Java, OpenShift and more, with one inventory, one match logic, one audit trail and one verification method.

### 2.6 How to pick up the certificate: methods compared

There are several ways to get the renewed certificate: API, a network agent, and others. Your conclusion was that API is best. The analysis agrees.

| Method | How it works | Strengths | Weaknesses | Decision |
|---|---|---|---|---|
| **API (recommended)** | CDM calls the Sectigo REST API to list, match and collect the certificate | Central, authenticated, auditable, works for every technology, no software on servers, easy to match by identity, fits the vault model | Needs API access and credentials; must be rate-limit aware | **Default acquisition method (FR-SRC-002)** |
| Network agent or landing agent | An agent on or near the server receives the issued certificate and hands it over | Close to the target; can install locally | Agent to deploy and maintain per technology and zone; different behaviour per platform; harder to audit centrally; more attack surface | Supported as a pluggable connector where it already exists (FR-SRC-009) |
| Webhook or event from the CA | The CA notifies CDM when a certificate is issued | Fast, no polling | Not available for every CA or tenant; still needs an API to collect | Optional accelerator |
| Protocol enrolment (ACME, SCEP, EST) | The target enrols directly with the CA | Very common for automation, key never leaves the target | Needs client support per target; less central control | Optional for eligible targets (FR-CA-005) |
| File drop or manual upload | A person places the file | Always possible | Manual, error-prone | Last-resort and the manual fallback path |

### 2.7 Product vision, customers and differentiation

**Vision.** No certificate outage, ever, without an army of scripts: a certificate that is issued is found, matched, deployed and proven in place automatically, on every technology, with a full audit trail.

**Positioning statement.** For organisations that run ServiceNow Discovery and use Sectigo, CDM is the certificate deployment layer that turns discovered locations and issued certificates into verified renewals, without adding agents to servers or replacing existing tools.

**Target customers**

| Segment | Profile | Why they buy |
|---|---|---|
| Enterprises on ServiceNow with Sectigo | Large estates, mixed technologies, CMDB already populated by Discovery | They already own both halves; CDM connects them |
| Managed service providers | Run certificates for several customers | Multi-tenant automation and per-customer reporting |
| Regulated industries | Banks, insurance, healthcare, public sector | Audit, key hygiene, segregation of duties, evidence for auditors |
| Organisations with shrinking certificate lifetimes | Any with more than a few hundred certificates | Manual renewal no longer scales when validity drops to months |

**Jobs to be done.** "Tell me which certificates will expire and where they are." "Get the replacement on the right server without an outage." "Prove it worked." "Show the auditor."

**Differentiators**

1. **CMDB-driven and closed loop**: location comes from Discovery, and confirmation comes from the next scan, not from trust in a script's exit code.
2. **ServiceNow-native**: request, approval, change, incident, CMDB and audit all live in one platform the customer already runs.
3. **One product, many technologies**: signed adapters behind one contract, shipped for the common stacks and extensible.
4. **Secure by design**: vault credentials, no permanent keys on MID Servers, allow-listed signed adapters, zone segmentation.
5. **Fits existing tools**: uses MID Servers, or hands the job to IWS, Rundeck or Ansible if that is what the customer already runs.

**Competitive landscape (to be validated before any sales use).** Dedicated certificate-lifecycle products (for example those from CyberArk/Venafi, Keyfactor, AppViewX, DigiCert), CA-native agents (Sectigo's own), ServiceNow's own certificate features, and in-house scripts with schedulers. CDM does not compete on being a CA or a scanner; it competes on being the deployment and verification layer inside the customer's existing ServiceNow and Sectigo investment.

---

## 3. Analysis of the POC folder

The folder `C:\Users\riyaa\Downloads\POC` contains six items. All were read; the three images were read visually.

| File | What it contains | How it is used here |
|---|---|---|
| Promp.md.txt | The original POC plan: one Windows laptop simulates two environments (Windows certificate store and a mock Linux folder). ServiceNow PDI, MID Server, WinRM, a Sectigo REST Message, and a Flow Designer flow with an If and Else If fork on a flow variable (Windows or RHEL), plus the Windows and Linux-simulator PowerShell scripts and prerequisites. | Functional baseline and POC scope (PLAN) |
| POC_SETUP_STATUS.md | Result of the local setup on 2026-07-27: Java 17, WinRM on 5985 with Basic and AllowUnencrypted, network profile Private, folders, URL ACL for port 8080. Manual steps left: create the PDI, download the MID Server, supply the Windows password. | Current environment and POC-only shortcuts to remove (SETUP) |
| mock_sectigo.ps1 | A PowerShell HttpListener on `http://localhost:8080/sectigo/` returning one fixed fake certificate string for every request. | Basis for the test-CA requirement and finding G1 (MOCK) |
| data1.jpeg | AI-assistant guidance: discovery versus deployment; MID Servers give network-local execution, not automatic access everywhere; endpoint discovery needs no login while host-level discovery does; deployment is a separate higher-privilege function; strongest design is ServiceNow and Sectigo orchestration with vault credentials, zone-specific MID Servers and separate adapters for IIS, Linux, Java, F5, Kubernetes and others. The last bullet is cut off ("For systems that cannot safely support automated deployment, the same workflow should create and ..."). | Architecture principles (D1). Read as "create and assign a manual task" (Q14). |
| data2.jpeg | Principles 1 to 5 (start of 6): discovery and deployment separation; no permanent private keys on the MID Server; vault-integrated credentials; network segmentation; high availability. | Security principles (D2) |
| data3.jpeg | Principles 6 to 9: technology allow-listing; pre-check and rollback; post-deployment verification; cluster awareness. | Safety principles (D3). The screenshot ends at item 9 (Q14). |

> The screenshots are AI-assistant guidance, not a standard. Each principle was checked against common PKI and ServiceNow practice before it became a requirement.

### 3.1 What the POC proves today

One flow: fetch a certificate from a CA-like API through the MID Server, then route by a technology value to a technology-specific script. The Windows branch writes the payload to `C:\temp\cert_stage` and runs `Import-Certificate` into `Cert:\LocalMachine\My`. The RHEL branch writes `app_server.crt` into a mock folder.

```text
 ServiceNow PDI                     Windows laptop (the only machine)
 Flow Designer                      +--------------------------------------------------+
   -> REST Message  --ECC queue-->  | MID Server ---GET---> mock_sectigo.ps1 :8080     |
   -> If/Else If on variable        |     |                                            |
      (Windows | RHEL)              |     +--WinRM 127.0.0.1:5985 (HTTP, Basic)        |
                                    |            |-> Cert:\LocalMachine\My  (Env A)    |
                                    |            |-> C:\mock_linux_server\...  (Env B) |
                                    +--------------------------------------------------+
```

### 3.2 Principles from the screenshots mapped to requirements

| # | Principle (source) | Where it is specified |
|---|---|---|
| 1 | Discovery and deployment separation: different credentials, roles and workflow permissions (D1, D2) | FR-INV-006, FR-ADM-001, NFR-SEC-04 |
| 2 | No permanent private keys on the MID Server; encrypted temporary storage only where unavoidable, then secure clean-up (D2) | FR-KEY-001 to FR-KEY-003, FR-SAF-008, NFR-SEC-05 |
| 3 | Vault-integrated credentials; nothing in scripts, workflow variables or config files (D2) | FR-CA-003, FR-SRC-012, NFR-SEC-01, NFR-SEC-04 |
| 4 | Network segmentation: MID Servers per zone (D2) | FR-ORC-004, NFR-SEC-02 |
| 5 | High availability: more than one MID Server where critical (D2) | NFR-AVL-01, NFR-AVL-02, FR-ADM-006 |
| 6 | Technology allow-listing: only approved, signed, version-controlled scripts and adapters (D3) | FR-ADP-002 to FR-ADP-005, NFR-SEC-03 |
| 7 | Pre-check and rollback (D3) | FR-SAF-001 to FR-SAF-003 |
| 8 | Post-deployment verification of SAN, chain, expiry, thumbprint (D3) | FR-SAF-004, FR-SAF-005, FR-LOOP-001 to FR-LOOP-004 |
| 9 | Cluster awareness: node by node, remove from rotation, validate each node and the VIP (D3) | FR-SAF-006, FR-SAF-007, FR-ORC-009 |
| 10 | Endpoint discovery needs no login; host-level discovery needs credentials (D1) | FR-INV-004, FR-INV-005 |
| 11 | Separate adapters for IIS, Linux, Java, F5, Kubernetes and others (D1) | FR-ADP-006, chapter 7 |
| 12 | Manual task when a system cannot safely support automation (D1, inferred) | FR-NTF-003, FR-NTF-004 |

### 3.3 Findings in the current POC

Gaps between the POC as built and a production-grade product. Several are deliberate POC shortcuts. Each is resolved by a requirement.

| ID | Finding | Why it matters | Resolved by |
|---|---|---|---|
| G1 | `mock_sectigo.ps1` returns a fixed string containing literal backslash-n text and fake data for any path and method. | It is not a valid PEM certificate, so `Import-Certificate` on the Windows branch is expected to fail. | FR-CA-010 |
| G2 | The flow moves only a public certificate: no CSR, no private key handling. | A certificate imported without its private key cannot serve TLS on Windows. | FR-KEY-001, AD-WIN-04, AD-WIN-05 |
| G3 | WinRM over HTTP 5985 with Basic and AllowUnencrypted true; network profile changed to Private. | Acceptable on loopback in a POC only. | AD-WIN-02, NFR-SEC-01 |
| G4 | One Windows administrator account, password stored in a ServiceNow credential, does everything. | Violates separation and least privilege. | FR-INV-006, FR-ADM-001, NFR-SEC-04 |
| G5 | The REST response is pasted into a PowerShell here-string in the flow step. | Script injection risk; no allow-list, versioning or signing. | FR-ADP-002 to FR-ADP-005 |
| G6 | REST Message endpoint is a placeholder (`https://sectigo.com`), the mock listens on `http://localhost:8080/sectigo/`; no authentication, certificate types or profiles. | The CA connector must be configurable per environment with vault credentials. | FR-CA-002 to FR-CA-004 |
| G7 | The target technology is a hand-edited flow variable. | Routing must come from the CMDB and strategy. | FR-ORC-003, FR-STR-001 |
| G8 | The Linux simulation is a bare file write. | No permissions, ownership, reload, backup, rollback or verification. | AD-LNX-05 to AD-LNX-12, FR-SAF |
| G9 | The POC has no ServiceNow-side source of certificate location and no rediscovery check. | It cannot prove the core behaviour in 2.4 (match, deploy, confirm by next scan). | FR-SRC, FR-LOOP |

---

## 4. Solution concept

### 4.1 The closed-loop renewal

```text
 DAY 0
 [1] ServiceNow Discovery/CMDB:  cert X expires soon   (thumbprint T1, SAN, server, path/binding)
        |
        v   CDM reads the CMDB (API)
 [2] CDM: is there a renewed certificate for this identity at Sectigo?   (API)
        |  yes: cert X' (thumbprint T2, same CN + SAN, later validity)   -> lands in the landing queue
        v
 [3] CDM: match is unique?  approved deployment strategy exists?  policy and change window ok?
        |  no strategy or ambiguous match  ->  review or manual task, never a silent skip
        v
 [4] CDM -> executor (MID Server in the target's zone) -> signed adapter for the technology
        pre-check -> backup -> install -> key permission / owner / bind -> reload (not restart)
        |
        v
 [5] Verify NOW on the live endpoint: presented thumbprint = T2, SAN, chain, expiry
        |  fail -> automatic rollback + alert
        v
     state: "Deployed, awaiting rescan"

 DAY +1
 [6] ServiceNow Discovery scans again
        |
        v
 [7] CMDB now shows T2 with new dates at that location
        |
        v
 [8] CDM: observed T2 == deployed T2 ?   yes -> "Confirmed by discovery", close, report
                                         no  -> alert, re-probe, escalate (not silently done)
```

### 4.2 Certificate identity and matching

The certificate is unique by its identity. Each source describes it with overlapping attributes; CDM normalises them.

| Attribute | In ServiceNow (Discovery, CMDB) | In Sectigo | Use in matching |
|---|---|---|---|
| Thumbprint (fingerprint), SHA-1 and SHA-256 | Yes (field names to be confirmed for your release, Q2) | Yes | Exact identity of one certificate |
| Serial number plus issuer | Yes | Yes | Exact identity, second key |
| Common name and subject DN | Yes | Yes | Lineage between old and renewed certificate |
| SAN set | Yes | Yes | Lineage; must be equal or an approved superset |
| Validity timestamps (not before, not after), exact UTC | Yes | Yes | Order in time; renewed has later dates |
| Key algorithm and size | Yes | Yes | Policy check |
| Location (host, store, path, binding, port) | **Yes, only here** | No | Where to deploy |
| Order ID, certificate ID, status, profile | No | **Yes, only here** | How to collect and renew |

**Matching rules**

| Rule | Description | Outcome |
|---|---|---|
| M1 | Same thumbprint in both sources | Same certificate. Link the CMDB CI to the Sectigo record. |
| M2 | Renewal lineage: same common name, same SAN set (or approved superset), same issuer and profile, later not-before and later not-after than the certificate in the CMDB, Sectigo order lineage where available | The Sectigo certificate is the replacement candidate (landing queue). |
| M3 | More than one candidate, or SAN differs unexpectedly | Ambiguous. Send to the review queue. Never deploy automatically. |
| M4 | Certificate in the CMDB unknown to Sectigo | Unmanaged or from another CA. Report. Optionally request issuance. |
| M5 | Certificate at Sectigo with no location in the CMDB | Unlocated. Report. Cannot be deployed until a location or strategy exists. |
| M6 | All timestamps compared in UTC with a small skew tolerance | Avoids false mismatches. |

### 4.3 Deployment strategy: the unit of automation

A strategy says how one certificate is deployed at one place. It is what the existing OpenShift and scheduler pattern calls "a deployment strategy in place".

| Field | Meaning |
|---|---|
| Binding | Which certificate identity and which location (host, service, port, store or path) |
| Adapter and version | Which signed adapter, for example `windows-iis` 1.3.0 |
| Zone and executor | Which network zone and which executor runs it |
| Credential alias | A vault path, never a secret |
| Key mode | A, B or C (4.4) |
| Activation | Hitless reload (preferred) or restart, and when |
| Verification | Endpoint probe details and the discovery confirmation rule |
| Rollback | How to return to the previous certificate |
| Window and owner | Change window, notification group |

Rules: a certificate is deployed automatically only if an approved strategy exists. Without one, CDM raises a manual task or alert (FR-STR-003). Strategies are versioned, tested with a dry run and audited.

### 4.4 Key handling modes

The certificate is useless on most platforms without its private key. There are three ways to keep the key and the certificate together, and the security principle (no permanent private keys on the MID Server) applies to all of them.

| Mode | How | When to use | Notes |
|---|---|---|---|
| **A. Key generated on the target (recommended)** | CDM (through the adapter) creates the key and CSR on the server, the CA signs it, CDM installs the certificate against the pending key | Windows, Linux, F5, Java where CDM controls issuance | Key never leaves the server. Requires CDM to start the issuance (or a CA renewal that reuses the same CSR, to be confirmed with Sectigo, Q1). |
| B. CA-delivered PKCS#12 | The CA generates the key and delivers a password-protected PFX; CDM carries it through an encrypted, short-lived path, imports it and wipes it | When renewal is CA-initiated and delivers the key, or the platform cannot produce a CSR | Exception path under FR-KEY-003. Password from the vault. Auditing is mandatory. |
| C. Reuse of the existing key | The renewed certificate is issued for the same public key; the certificate is paired with the key already on the server (for example on Windows by repairing the store link, on Linux by replacing only the certificate file) | When policy allows key reuse and the CA supports it | Weaker hygiene; needs a policy exception (FR-KEY-006). |

### 4.5 Executors

The executor is what actually touches the server.

| Executor | Description | Phase |
|---|---|---|
| MID Server (default) | Already used by Discovery, has downstream access, connects outbound only | P1 |
| External scheduler | IBM Workload Scheduler (HCL Workload Automation), Rundeck, Ansible Automation Platform: CDM creates the job with parameters (location, credential alias, adapter id), the tool runs it and reports the result back | P2 |
| In-cluster executor | An OpenShift or Kubernetes job or agent using a standard service account and role binding | P2 |
| Lightweight outbound agent | Small agent for networks where a MID Server is not available | P3 |

Whatever the executor, the adapter contract and the result envelope are identical (Appendix A), and CDM verifies the result independently.

### 4.6 Discovery integration

CDM does not replace ServiceNow Discovery. It uses it in two ways: as the source of location and expiry (start of the loop) and as the independent proof that the deployment worked (end of the loop). Where Discovery cannot reach a target, the adapter's own `discover` operation and an optional endpoint probe fill the gap. On-demand rescan of a single target after deployment is a Should (FR-LOOP-005) to shorten confirmation from a day to minutes.

### 4.7 Scope decisions

- Apple (macOS, iOS, iPadOS) and cloud services are deferred. The adapter contract, the executor model and the strategy model are generic so they can be added without redesign (section 7.9).
- The MVP focuses on the technologies you named as examples: Windows (certificate store, private key permission, IIS HTTPS binding), Linux with Apache (key, owner, file permission, configuration reload instead of restart) and Java applications.
- OpenShift, Rundeck and IWS are treated as an existing pattern to generalise and integrate with, in phase 2.

---

## 5. Architecture

### 5.1 Context

```text
                     +-------------------------------- ServiceNow instance ---------------------------------+
   People            |  Discovery + CMDB  |  CDM application                                               |
 requester,          |  (where, expiry)   |  Source sync + matching | Strategy registry | Orchestrator     |
 approver,           |                    |  Policy | Adapter registry (signed) | Verification | Audit      |
 PKI admin,          |                    |  Credential broker (aliases only) | Notifications | Reports    |
 auditor             +---------+-------------------------------+----------------+-------------------------+
                               |                               |                |
                  API (preferred)                     vault (JIT secrets)   ECC queue (outbound 443)
                               |                               |                |
                          Sectigo CA                     Secrets vault     MID Servers per zone / executors
                          (+ ACME, ADCS later)           (+ HSM, KMS)      (IWS, Rundeck, Ansible optional)
                                                                                |
                                     Windows/IIS   Linux/Apache,nginx   Java   OpenShift/K8s   F5   DB ...
                                     (Apple and cloud: deferred)
```

### 5.2 Logical layers

Each layer talks only to the layer below.

| Layer | Components |
|---|---|
| Presentation | Catalog and request forms, owner portal, expiry and closed-loop dashboard, approver workspace, auditor reports |
| Orchestration | Request handler, approval and change gate, lifecycle state machine, scheduler (poll, expiry, rescan check), retry, timeout and rollback |
| Domain services | Source sync and matcher, strategy registry, policy engine, adapter router, credential broker, notification service, inventory |
| Integration | ServiceNow Discovery and CMDB connector, Sectigo and other CA connectors, vault connector, executor connectors (MID, IWS, Rundeck, Ansible), OpenShift and Kubernetes API connector, ITSM and SIEM connectors |
| Adapters (signed, versioned) | Windows IIS and store, Linux Apache and nginx, Java keystore, OpenShift and Kubernetes, F5 and NetScaler, databases, network devices |
| Cross-cutting | Security (RBAC, MFA, least privilege), secrets handling, audit trail, observability, compliance |

### 5.3 Deployment architecture and security zones

```text
 ServiceNow cloud (customer controlled)                                   Vault + HSM/KMS
   CDM app, signed adapter registry, credential ALIASES, audit           dynamic secrets, key custody
        ^   outbound-initiated TLS 443 only                                    ^  mTLS, JIT, TTL <= 15 min
 -------|------------------------------------------------------------------------|-----------------------
 +------+----------------+      +--------------------------+       +-------------+----------------+
 | Zone A: DMZ           |      | Zone B: internal / DC    |       | Zone C: containers           |
 | MID-DMZ-01            |      | MID-INT-01  MID-INT-02   |       | MID-CNT-01 / in-cluster job  |
 | discovery acct (ro)   |      | (HA pair)                |       | service account + role bind  |
 | deployment acct (rw)  |      | discovery acct / deploy  |       |                              |
 | web servers, LBs      |      | Windows, Linux, Java, DB |       | OpenShift / Kubernetes       |
 +-----------------------+      +--------------------------+       +------------------------------+
```

Controls: outbound-only connections, one MID set per zone, separate discovery and deployment accounts, JIT credentials, no permanent private keys on any MID Server, signed and allow-listed adapters, full audit stream to the SIEM.

### 5.4 Components

| Component | Responsibility | Runs on |
|---|---|---|
| Source sync and matcher | Reads CMDB and Sectigo, normalises identity, applies matching rules M1 to M6, builds the landing queue | ServiceNow |
| Strategy registry | Stores approved deployment strategies | ServiceNow |
| Orchestrator | State machine, workflow, retries, concurrency, scheduling | ServiceNow (Flow Designer and scripted actions) |
| Policy engine | Key size, algorithms, validity, allowed CAs and domains, approvals, windows | ServiceNow |
| Adapter registry and router | Approved signed adapters; chooses adapter from strategy, technology, zone | ServiceNow |
| Credential broker | Turns aliases into JIT secrets, never stores them | ServiceNow plus vault connector |
| CA connectors | List, collect, renew, revoke, status per CA | ServiceNow (REST) or MID Server |
| Executors | Run adapters: MID Server, IWS, Rundeck, Ansible, in-cluster job | Customer network |
| Adapters | Pre-check, backup, key, install, activate, verify, rollback, discover | Executor (signed) |
| Verification and loop | Endpoint verification and rediscovery confirmation | ServiceNow plus MID |
| Notification and manual tasks | Owner notifications, manual fallback, incidents | ServiceNow |
| Audit and reporting | Tamper-evident audit, dashboards, SIEM export | ServiceNow plus SIEM |

### 5.5 Technology baseline

- Platform: ServiceNow scoped application, Flow Designer and scripted actions, MID Server (Java 17 or as required by the instance release).
- Adapters: PowerShell (Windows), POSIX shell and OpenSSL (Linux), keytool (Java), Kubernetes and OpenShift API, vendor REST APIs (load balancers).
- CAs: Sectigo Certificate Manager REST API first; ACME (RFC 8555) and Microsoft ADCS later.
- Transport: WinRM over HTTPS or Kerberos, SSH with certificates, Kubernetes API over TLS, REST over TLS 1.2 or higher.
- Adapters kept in source control with CI, tests and signed releases.

### 5.6 Key design decisions

| # | Decision | Rationale |
|---|---|---|
| DD-1 | CDM is the join between Sectigo (issuance) and ServiceNow (location); it does not replace either. | Matches the actual gap and the customer's existing investments. |
| DD-2 | Match by certificate identity (thumbprint, serial, SAN, timestamps), not by name alone. | The certificate is unique by identity; names repeat across renewals. |
| DD-3 | API is the default acquisition method; agents and others are pluggable connectors. | Central, auditable, no software on servers (2.6). |
| DD-4 | A deployment strategy must exist before anything is deployed automatically. | Prevents silent or unsafe actions; mirrors the existing pattern. |
| DD-5 | Platform logic lives only in signed adapters behind one contract; executors are interchangeable. | Generic product, and works with MID or a scheduler. |
| DD-6 | Verification is against the live endpoint and confirmed by the next Discovery rescan. | A successful copy is not a successful deployment. |
| DD-7 | Keys stay on the target where possible; PFX transport is an audited exception. | Principle 2 (no permanent keys on the MID Server). |
| DD-8 | Anything without a safe adapter or strategy goes to a manual task, still verified automatically. | Full coverage without unsafe automation. |
| DD-9 | Discovery and deployment use separate credentials and workflows. | Principle 1. |
