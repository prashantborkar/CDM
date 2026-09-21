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

**Requirement counts.** 121 functional requirements (P1 MVP: 80, P2: 32, P3: 9; Must: 80, Should: 34, Could: 7), 46 platform adapter requirements, 20 non-functional requirements, 23 product and commercial requirements, 16 open questions with defaults, 20 acceptance tests.

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


---

## 6. Functional requirements

Requirements are grouped by area. Each row: ID, requirement, priority, phase, source.

### 6.1 Source integration and matching (SRC)

The core of the product: reading ServiceNow and Sectigo, matching identities, building the landing queue.

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-SRC-001 | Read certificate CIs and their relationships (host, store or path, binding, port, expiry, thumbprint, SAN, discovery timestamps) from the ServiceNow CMDB populated by Discovery, using supported ServiceNow APIs. Sync is incremental and at least daily; frequency is configurable. | M | P1 | PS |
| FR-SRC-002 | Read issued, renewed and pending certificates from Sectigo through its API (preferred method): identity fields, status, order or certificate ID, validity, and collect the certificate and chain. Incremental by a since-timestamp; poll interval configurable (default 15 minutes). | M | P1 | PS |
| FR-SRC-003 | Maintain one normalised Certificate record that links the CMDB CI and the Sectigo record by identity (thumbprint, serial and issuer, common name, SAN set, exact UTC timestamps). | M | P1 | PS |
| FR-SRC-004 | Apply matching rules M1 to M6 (section 4.2) with a recorded confidence. An ambiguous match is sent to a review queue and is never deployed automatically. | M | P1 | PS, NEW |
| FR-SRC-005 | Detect renewal candidates: certificates expiring within their renewal window in the CMDB for which Sectigo holds a newer certificate for the same identity. Place them in the landing queue. | M | P1 | PS |
| FR-SRC-006 | Detect gaps: expiring in the CMDB but no renewed certificate at Sectigo (raise a renewal request or alert); in the CMDB but unknown to Sectigo (unmanaged); at Sectigo but with no CMDB location (unlocated). | M | P1 | PS |
| FR-SRC-007 | Handle location drift: if Discovery finds the same certificate at additional locations, treat each as a binding and report the drift. | S | P2 | NEW |
| FR-SRC-008 | Compare and store all timestamps in UTC with a configurable skew tolerance. | M | P1 | PS |
| FR-SRC-009 | Provide pluggable acquisition connectors: API (default), Sectigo network or landing agent, webhook, file drop, manual upload (section 2.6). | S | P2 | PS |
| FR-SRC-010 | Define source-of-truth rules: CMDB owns location and observed state; Sectigo owns issuance and entitlement; CDM owns intent, strategy and job history. Conflicts are logged and shown. | M | P1 | NEW |
| FR-SRC-011 | Support several Sectigo accounts or organisations and separate sandbox and production profiles. | S | P2 | NEW |
| FR-SRC-012 | Credentials for Sectigo and any external ServiceNow or executor access are vault aliases, never stored in REST Messages, scripts or flow variables. | M | P1 | D2 |

### 6.2 Inventory (INV)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-INV-001 | Maintain a central inventory of certificates: common name, SANs, serial, SHA-256 thumbprint, issuer, validity dates, key algorithm and size, owner group, environment, lifecycle state. | M | P1 | NEW |
| FR-INV-002 | Link each certificate to one or more bindings (server, service, port, store or path, secret) so the deployment target is known without human input. | M | P1 | PS |
| FR-INV-003 | Seed and correct the inventory by CSV import and REST API. | M | P1 | NEW |
| FR-INV-004 | Optional endpoint probe: TLS scan of host and port ranges from a MID Server, recording the presented chain. Requires no server login. Used to fill gaps where Discovery does not reach. | S | P2 | D1 |
| FR-INV-005 | Optional host-level discovery through the adapter `discover` operation with read-only credentials, for targets Discovery cannot reach. | S | P2 | D1, D2 |
| FR-INV-006 | Discovery and deployment use different credentials, roles and workflow permissions. No account holds both. | M | P1 | D1, D2 |
| FR-INV-007 | Compute days to expiry and flag at configurable thresholds (default 90, 60, 30, 14, 7 and 1 days), scaled for short-lived certificates (FR-REQ-005). | M | P1 | NEW |
| FR-INV-008 | Report weak or non-compliant certificates: SHA-1, RSA below 2048, self-signed, wildcard misuse, no owner. | C | P3 | NEW |
| FR-INV-009 | Represent targets as CMDB configuration items with technology, environment, zone, cluster and owner attributes. | M | P1 | PS |

### 6.3 Request, approval and renewal (REQ)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-REQ-001 | Provide a catalog request for new certificates and manual renewals: common name, SANs, targets, owner, environment, validity, CA profile, justification. | M | P1 | NEW |
| FR-REQ-002 | Validate every request and every automatic deployment against policy before any change: allowed domains, key algorithm and size, maximum validity, allowed CA, wildcard rules. | M | P1 | NEW |
| FR-REQ-003 | Configurable approval per policy: auto-approve low risk; manager or PKI admin approval for wildcard or production. A requester cannot approve their own request. | M | P1 | NEW |
| FR-REQ-004 | Integrate with change management: production deployments require an approved change and run inside its window. | S | P2 | NEW |
| FR-REQ-005 | Adaptive renewal window: start renewal when remaining lifetime is at most the smaller of 30 days and 33 percent of the total lifetime, with a floor of 3 days (so a one-month certificate starts at about 10 days, a one-year certificate at 30 days). All values are configurable per policy. | M | P1 | PS |
| FR-REQ-006 | Revocation request with mandatory reason and approval; calls the CA, updates inventory and bindings. | S | P2 | NEW |
| FR-REQ-007 | Each request has a unique ID and visible state history. | M | P1 | NEW |
| FR-REQ-008 | Bulk requests from CSV with per-item status. | S | P2 | NEW |
| FR-REQ-009 | Emergency replacement path with post-hoc approval and elevated audit. | C | P3 | NEW |

### 6.4 CA integration (CA)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-CA-001 | Define a CA connector interface (list, collect, enroll, renew, revoke, status, list profiles) so CAs are pluggable. | M | P1 | NEW, D1 |
| FR-CA-002 | Implement the Sectigo connector on the Sectigo Certificate Manager REST API: list and collect issued certificates and chain in PEM, enroll with CSR, renew, revoke. Endpoints per current Sectigo documentation (Appendix D). | M | P1 | PLAN, PS |
| FR-CA-003 | CA credentials (login, password or API key, customer URI) are stored only as vault aliases. | M | P1 | D2 |
| FR-CA-004 | CA profiles carry an environment (sandbox or production). A sandbox certificate can never be deployed to a production target. | M | P1 | SETUP |
| FR-CA-005 | ACME connector (RFC 8555) with HTTP-01 and DNS-01 challenges for eligible targets and domains. | S | P2 | NEW |
| FR-CA-006 | Microsoft ADCS and private CA connector. | S | P3 | NEW |
| FR-CA-007 | Handle asynchronous issuance: pending validation, polling with back-off, optional webhook, timeout and escalation. | M | P1 | NEW |
| FR-CA-008 | Validate every certificate collected: public key matches the expected key or CSR, names match the identity, chain builds to a trusted root, validity is correct. Reject otherwise. | M | P1 | NEW |
| FR-CA-009 | Respect CA rate limits and quotas by queuing and throttling. | S | P2 | NEW |
| FR-CA-010 | Provide a test CA (replacing the fixed-string mock) that signs real CSRs, returns real PEM with correct content types and a landing-area behaviour. It must be impossible to enable in production. | M | P1 | MOCK |
| FR-CA-011 | Ability to trigger renewal at Sectigo for a certificate identity when none is waiting in the landing area, subject to policy. | S | P2 | PS |

### 6.5 Key and CSR management (KEY)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-KEY-001 | Prefer key mode A (section 4.4): generate private keys on the target or in an HSM, TPM or KMS. Only the CSR travels. | M | P1 | D2 |
| FR-KEY-002 | No permanent private key is stored on a MID Server, in ServiceNow tables, logs, ECC payloads or flow variables. | M | P1 | D2 |
| FR-KEY-003 | Where key transport is unavoidable (mode B), use a password-protected PKCS#12 with a one-time password from the vault, in encrypted temporary storage with a short life (default 15 minutes), then secure deletion. Deletion is verified and audited. | M | P1 | D2 |
| FR-KEY-004 | Key policy: RSA 3072 default (2048 minimum), ECDSA P-256 or P-384 where supported; non-exportable where the platform allows. | M | P1 | NEW |
| FR-KEY-005 | Support HSM or KMS-backed keys (PKCS#11) for critical services. | S | P3 | NEW |
| FR-KEY-006 | New key pair on every renewal by default. Key reuse (mode C) needs an approved policy exception and is reported. | M | P1 | NEW |
| FR-KEY-007 | Detect and report weak key parameters. | S | P2 | NEW |
| FR-KEY-008 | Check each CSR against policy (names, algorithm, size) before submission. | M | P1 | NEW |
| FR-KEY-009 | Pair the collected certificate with its private key safely per platform: certreq accept or store repair on Windows, key path and permissions on Linux, alias import on Java. Refuse installation if the certificate does not match the key. | M | P1 | PS |

### 6.6 Deployment strategy (STR)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-STR-001 | A deployment strategy defines, per binding: adapter and version, location, zone, executor, credential alias, key mode, activation method, verification, rollback, window and owner (section 4.3). | M | P1 | PS |
| FR-STR-002 | Strategies are versioned, approved (four-eyes from P2) and audited. A certificate is deployed automatically only when an approved strategy exists. | M | P1 | PS, D3 |
| FR-STR-003 | With no strategy, or an ambiguous one, CDM sets the status "No strategy", creates a manual task or alert for the owner, and never skips silently. | M | P1 | PS |
| FR-STR-004 | Strategy templates per technology (IIS, Apache, nginx, Tomcat, OpenShift secret or route) and inheritance (organisation, application, binding). | S | P2 | NEW |
| FR-STR-005 | Assisted onboarding: suggest a strategy from the CMDB relationships and host type, and offer a wizard. | S | P2 | NEW |
| FR-STR-006 | Dry-run a strategy against a target (pre-check only) before enabling automation. | M | P1 | NEW |
| FR-STR-007 | Import and export strategies as JSON or YAML for source control and GitOps. | S | P2 | NEW |
| FR-STR-008 | Estate simulation: report what would be deployed where if every expiring certificate renewed today. | C | P3 | NEW |

### 6.7 Orchestration and lifecycle (ORC)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-ORC-001 | Implement the lifecycle state machine (chapter 9). Transitions are enforced server-side; illegal transitions are rejected and audited. | M | P1 | NEW |
| FR-ORC-002 | Execute each deployment as the workflow in 4.1. Steps are idempotent and resumable after MID or instance restarts. | M | P1 | PLAN, NEW |
| FR-ORC-003 | Derive technology, zone and adapter from the strategy and the CMDB record, never from a hand-edited variable. | M | P1 | PLAN, PS |
| FR-ORC-004 | Dispatch jobs only to executors that belong to the target's zone. | M | P1 | D2 |
| FR-ORC-005 | Timeouts and retries with exponential back-off for transient errors. Permanent failure triggers rollback and an incident. | M | P1 | NEW |
| FR-ORC-006 | Concurrency limits per zone, adapter and cluster (default 5) and a per-target lock so jobs never overlap. | S | P2 | NEW |
| FR-ORC-007 | Schedule deployments in change windows with deferral and re-queue. | S | P2 | NEW |
| FR-ORC-008 | Dry-run mode that performs pre-checks only and reports what would change. | M | P1 | NEW |
| FR-ORC-009 | Staged rollout for multi-target deployments: canary first, then waves, stop on first failure. | S | P2 | D3 |
| FR-ORC-010 | Authorised cancellation before deployment starts. After start, only a safe abort with rollback. | M | P1 | NEW |

### 6.8 Adapter framework (ADP)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-ADP-001 | One adapter contract with operations: precheck, backup, generate_csr, install, activate, verify, rollback, cleanup, discover. Each returns a structured JSON result (Appendix A). | M | P1 | D1, NEW |
| FR-ADP-002 | An adapter registry holds technology, version, SHA-256 signature and approval status. Only approved, signed versions may run (allow-list). | M | P1 | D3 |
| FR-ADP-003 | Executors run only registered adapters. Free-text script execution from flow variables is disabled. | M | P1 | D3 |
| FR-ADP-004 | Adapter inputs are typed, validated and passed as parameters, never concatenated into script text. Certificate content is validated as PEM before use. | M | P1 | NEW |
| FR-ADP-005 | Adapters are version controlled with peer review, automated tests and signed releases, promoted dev, test, production. | M | P1 | D3 |
| FR-ADP-006 | Deliver adapters in phases: P1 Windows (store and IIS), Linux (Apache, nginx), Java, manual; P2 OpenShift and Kubernetes, F5 and NetScaler; P3 databases, middleware, network devices. Apple and cloud are deferred. | M | P1 | D1, PS |
| FR-ADP-007 | Adapters declare capabilities (CSR on target, cluster aware, rollback, hitless activation). The router uses them, for example to force manual fallback when rollback is impossible. | S | P2 | NEW |
| FR-ADP-008 | Provide an adapter template, linter, test harness and documentation (adapter SDK). | S | P2 | NEW |
| FR-ADP-009 | Map adapter errors to a catalogue of error codes with remediation hints. | M | P1 | NEW |
| FR-ADP-010 | Several adapters per technology, chosen by service type (for example Apache versus nginx). | C | P3 | NEW |

### 6.9 Executors (EXE)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-EXE-001 | The MID Server is the default executor. | M | P1 | PS |
| FR-EXE-002 | External executor connectors: IBM Workload Scheduler (HCL Workload Automation), Rundeck, Ansible Automation Platform. CDM creates the job with parameters (location, credential alias reference, adapter id) and receives the result by callback or poll. The external tool resolves the credential from the customer's own store. | S | P2 | PS |
| FR-EXE-003 | Every executor implements the same adapter contract and result envelope, and CDM verifies the result independently. | M | P1 | NEW |
| FR-EXE-004 | Ship a standard, least-privilege service account, role and role binding manifest for OpenShift and Kubernetes, with documentation. Tokens are short-lived. | S | P2 | PS |
| FR-EXE-005 | Executor selection by strategy and zone, with failover across the MID set. | M | P1 | D2 |
| FR-EXE-006 | Lightweight outbound-only agent for networks without a MID Server. | C | P3 | NEW |

### 6.10 Deployment safety (SAF)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-SAF-001 | Pre-check before any change: target reachable, credential valid, permissions, disk space, service state, current certificate identified, cluster peers healthy, change window open. | M | P1 | D3 |
| FR-SAF-002 | Back up the current certificate and configuration reference (thumbprint, binding, config version) as a rollback point before replacing anything. Keys stay in place; nothing secret is copied into ServiceNow. | M | P1 | D3 |
| FR-SAF-003 | Roll back automatically when activation or verification fails. The rollback itself is verified. | M | P1 | D3 |
| FR-SAF-004 | Verify against the live endpoint: presented thumbprint equals expected, SAN covers all names, chain complete and trusted, not expired, protocol and cipher unchanged. Run from a MID Server in the target's zone. | M | P1 | D3 |
| FR-SAF-005 | A failed verification is never ignored. It requires rollback or an approved, audited exception. | M | P1 | D3 |
| FR-SAF-006 | Cluster awareness: node by node, drain or remove from rotation, restart, health-check, re-add. Validate each node and the VIP. Abort and roll back on first failure. | S | P2 | D3 |
| FR-SAF-007 | Confirm high-availability pair synchronisation after deployment (F5 device group, Windows failover cluster, Kubernetes replicas). | S | P2 | D3 |
| FR-SAF-008 | Secure clean-up: staging files, temporary key material and sessions are removed and confirmed. Evidence is audited. | M | P1 | D2 |
| FR-SAF-009 | Adapters declare whether activation is hitless (reload) or needs a restart. Reload is preferred over restart. Policy can require a change window for restarts. | M | P1 | PS |
| FR-SAF-010 | Refuse to deploy when the certificate names do not match the binding's expected names. | M | P1 | NEW |

### 6.11 Closed-loop confirmation (LOOP)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-LOOP-001 | After a successful deployment and live verification, set the state "Deployed, awaiting rescan". | M | P1 | PS |
| FR-LOOP-002 | Read the ServiceNow CMDB after the next Discovery or certificate scan of the target and check that the CI at the binding location now shows the new thumbprint, validity dates and expiry (timestamps not earlier than the deployment). | M | P1 | PS |
| FR-LOOP-003 | When the observed thumbprint and dates equal the deployed certificate, set "Confirmed by discovery", write the audit record and close the request. | M | P1 | PS |
| FR-LOOP-004 | If not confirmed within a configurable time (default 36 hours), alert the owner, re-probe the live endpoint and escalate. Never mark the request done. | M | P1 | PS |
| FR-LOOP-005 | Request an on-demand rescan of one target right after deployment where ServiceNow allows it, to shorten confirmation to minutes. | S | P2 | NEW |
| FR-LOOP-006 | Relate the old certificate CI to the new one ("replaced by") and let Discovery retire the old CI. | M | P1 | NEW |
| FR-LOOP-007 | Report deploy-to-confirm time and the count of unconfirmed deployments as KPIs. | S | P2 | NEW |
| FR-LOOP-008 | Use the live probe result to tell a deployment failure apart from Discovery lag. | M | P1 | NEW |

### 6.12 Notifications and manual fallback (NTF)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-NTF-001 | Notify owner groups and PKI admins on expiry thresholds, landing queue arrivals, approvals needed, deployment success or failure, rollback and unconfirmed deployments. | M | P1 | NEW |
| FR-NTF-002 | Channels: email (M); Teams or Slack and ServiceNow mobile (S); paging for critical services (C). | M | P1 | NEW |
| FR-NTF-003 | Manual fallback: when there is no approved adapter or strategy, policy forbids automation, or a prerequisite fails, create a task for the owner group with step-by-step instructions, the certificate package (and CSR if needed) and required evidence fields. | M | P1 | D1 |
| FR-NTF-004 | Manual tasks have SLA timers and escalation. Completion triggers automated verification and the same closed-loop confirmation. | M | P1 | D1 |
| FR-NTF-005 | Create an incident automatically for failed deployments or rollbacks, linked to job evidence. | S | P2 | NEW |
| FR-NTF-006 | Notification templates are configurable and never contain secrets or key material. | S | P2 | NEW |

### 6.13 Reporting and audit (RPT)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-RPT-001 | Dashboard: certificates by state, expiring in 7, 30, 60 and 90 days, landing queue size, unconfirmed deployments, failed deployments, automation coverage, renewal lead time. | M | P1 | NEW |
| FR-RPT-002 | Tamper-evident audit trail for every action: who, what, when, target, adapter and version, job ID, result, thumbprint before and after. Exportable to a SIEM. | M | P1 | NEW |
| FR-RPT-003 | Compliance reports: inventory export, policy exceptions, unmanaged and unlocated certificates. | S | P2 | NEW |
| FR-RPT-004 | Team scorecards and automation coverage by technology. | S | P2 | NEW |
| FR-RPT-005 | Scheduled report delivery. | C | P3 | NEW |
| FR-RPT-006 | Configurable audit retention (default 13 months online, then archive per policy). | M | P1 | NEW |

### 6.14 Administration (ADM)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-ADM-001 | Role-based access with segregation of duties: requester, approver, PKI admin, deployment operator, discovery operator, adapter publisher, auditor. Least privilege. | M | P1 | D1, D2 |
| FR-ADM-002 | Configuration registry for zones, executors, CA profiles, policies, strategies, adapters and thresholds. All changes versioned and audited. | M | P1 | NEW |
| FR-ADM-003 | Separate development, test and production instances with controlled promotion. | M | P1 | NEW |
| FR-ADM-004 | SSO and MFA for privileged actions, and a time-boxed break-glass procedure. | S | P2 | NEW |
| FR-ADM-005 | Adapter and strategy approval requires a second person (four-eyes). | S | P2 | D3 |
| FR-ADM-006 | Health monitoring and alerts for MID Servers (heartbeat, version, HA state), executors, CA connectors, ServiceNow integration and the vault. | M | P1 | D2 |
| FR-ADM-007 | Domain separation for business units or customers (see PRD-004). | C | P3 | NEW |

---

## 7. Platform adapter specifications

Each platform has its own adapter with the same contract (FR-ADP-001). Commands and paths are indicative and must be confirmed in adapter design. Priority follows your examples: Windows IIS, Linux with Apache, Java in the MVP.

### 7.1 Windows: certificate store, private key permission, IIS binding (adapter WIN, P1)

| ID | Aspect | Specification |
|---|---|---|
| AD-WIN-01 | Scope | Windows Server 2016, 2019, 2022 and 2025. Certificate store, IIS, RDP listener, WinRM HTTPS listener, SQL Server, services bound with netsh http. Exchange and ADFS in P3. |
| AD-WIN-02 | Transport | WinRM over HTTPS (5986) with a certificate-authenticated listener, or Kerberos in a domain. HTTP, Basic and AllowUnencrypted are forbidden outside the POC. A constrained JEA endpoint exposing only approved cmdlets is preferred. |
| AD-WIN-03 | Accounts | Separate read-only discovery account and scoped deployment account, gMSA or vault-rotated. Never a domain administrator. |
| AD-WIN-04 | Key and CSR | Mode A: `certreq -new` with an INF: key in `Cert:\LocalMachine\My` request store, non-exportable, 3072-bit, SANs from the identity. Only the CSR leaves the host. |
| AD-WIN-05 | Install and store | `certreq -accept` binds the issued certificate to its private key in `Cert:\LocalMachine\My`. Mode B: PFX import (`Import-PfxCertificate`, non-exportable) under FR-KEY-003. Mode C: pair with the existing key (store repair). Intermediates go to the intermediate CA store; roots are managed by Group Policy, not CDM. |
| AD-WIN-06 | Private key permission | Grant read access on the private key only to the identity that needs it (IIS application pool identity or the service account), remove everything else, and record the ACL in the evidence. |
| AD-WIN-07 | IIS HTTPS binding | Update the HTTPS binding of each site to the new thumbprint, including SNI and the certificate store name. Also RDP listener, SQL Server, WinRM HTTPS listener, netsh http sslcert where the strategy says so. |
| AD-WIN-08 | Backup | Record the previous thumbprint and every binding that uses it. The old certificate stays in the store (archived) for a retention period (default 30 days). |
| AD-WIN-09 | Verify | TLS handshake with SNI to host and port from the zone MID Server. Compare thumbprint, chain (Windows chain engine), SAN and expiry. |
| AD-WIN-10 | Rollback | Re-apply the previous thumbprint to each binding, restart only if needed, verify. Remove the failed certificate. |
| AD-WIN-11 | Discover | Enumerate `Cert:\LocalMachine\My` and web-hosting stores: subject, SAN, thumbprint, expiry, has-private-key flag, bindings. |
| AD-WIN-12 | POC continuity | The POC path (`Import-Certificate` into `Cert:\LocalMachine\My`) is the reference and is extended with key pairing, permission and binding steps. |

### 7.2 Linux with Apache and nginx (adapter LNX, P1)

| ID | Aspect | Specification |
|---|---|---|
| AD-LNX-01 | Scope | RHEL, Rocky, Alma 8 and later; Ubuntu LTS 20.04 and later; Debian 11 and later; SUSE 15. Services: Apache (httpd, apache2), nginx, HAProxy, Postfix, Dovecot, generic file-based TLS. |
| AD-LNX-02 | Transport | SSH from the zone MID Server (or executor) using short-lived signed SSH certificates from the vault, or a vault-brokered key. No password authentication. Host keys pinned. |
| AD-LNX-03 | Privilege | A dedicated deployment user. sudo rules limited to named commands (install, service reload, config test, restorecon). |
| AD-LNX-04 | Key and CSR | Mode A: `openssl req -new` with a 3072-bit key created under umask 077 in `/etc/pki/tls/private` (RHEL family) or `/etc/ssl/private` (Debian family). Only the CSR is returned. |
| AD-LNX-05 | Install, owner and permission | Write certificate and chain to a versioned file and switch an atomic "current" symlink. Certificate mode 0644. Private key owned by root with the service group (for example apache or ssl-cert), mode 0640 or 0600. |
| AD-LNX-06 | SELinux and AppArmor | `restorecon` on written paths and check the context; confirm the AppArmor profile allows the new path. |
| AD-LNX-07 | Configuration reload, not restart | Test the configuration, then reload gracefully: `apachectl configtest` then `apachectl graceful` or `systemctl reload httpd`; `nginx -t` then `systemctl reload nginx`; `haproxy -c` then reload. Restart only if reload is unsupported (FR-SAF-009). |
| AD-LNX-08 | Backup | Copy the previous certificate, key reference and config file into a root-only backup directory keyed by job ID. |
| AD-LNX-09 | Verify | `openssl s_client` with `-servername` from the zone MID Server. Compare fingerprint, SAN, chain and expiry. |
| AD-LNX-10 | Rollback | Flip the symlink back, reload, verify. |
| AD-LNX-11 | Trust stores | `update-ca-trust` or `update-ca-certificates` only for private CA roots and only after explicit approval. |
| AD-LNX-12 | Simulator | The mock folder (`C:\mock_linux_server`) is upgraded to enforce naming, simulated permissions, a reload stub and a verify stub, and a real Linux target (WSL, VM or container) is added in P1. |

### 7.3 Java applications and keystores (adapter JVA, P1)

| ID | Aspect | Specification |
|---|---|---|
| AD-JVA-01 | Scope | JKS and PKCS#12 keystores and truststores for Tomcat, JBoss and WildFly, WebLogic, WebSphere Liberty, Spring Boot, Kafka and similar. |
| AD-JVA-02 | Access | Through the Windows or Linux adapter (SSH or WinRM). The keystore path and alias come from the strategy. |
| AD-JVA-03 | Key and CSR | `keytool -genkeypair` (3072-bit) and `-certreq` (mode A). The keystore password comes from the vault and never appears on a visible command line (protected file or environment). |
| AD-JVA-04 | Install | `keytool -importcert` of the chain in order (root, intermediates, leaf), or import of the PKCS#12 in mode B. Prefer PKCS#12; flag JKS for migration. Set file owner and permission as for Linux or Windows. |
| AD-JVA-05 | Backup and rollback | Timestamped, checksummed keystore copy. Rollback restores it and reloads or restarts. |
| AD-JVA-06 | Activate and verify | Connector reload or service restart per product; prefer hot reload where supported. Verify with `s_client` and `keytool -list -v`. |

### 7.4 OpenShift and Kubernetes (adapter K8S, P2)

| ID | Aspect | Specification |
|---|---|---|
| AD-K8S-01 | Scope | OpenShift 4, upstream Kubernetes, AKS, EKS, GKE clusters. Routes and Ingress, Istio or Gateway API, workloads that mount TLS Secrets. |
| AD-K8S-02 | Access, service account and role binding | Kubernetes API over TLS with a ServiceAccount and short-lived tokens. RBAC limited to named namespaces and verbs (secrets get, create, update by label; deployments get and patch for restart; routes or ingresses get and patch). CDM ships a standard Role and RoleBinding manifest. No cluster-admin. This is the same "service account and role binding" standard used in the existing OpenShift pattern. |
| AD-K8S-03 | Modes | Push mode: CDM writes the `kubernetes.io/tls` Secret (or OpenShift route certificate). Delegated mode: cert-manager owns issuance and renewal and CDM inventories and monitors. |
| AD-K8S-04 | Key and CSR | Delegated: cert-manager creates the key in-cluster. Push: an ephemeral job creates key and CSR; the key exists only as Secret data. Encryption at rest with a KMS provider is required. |
| AD-K8S-05 | Install | Apply the Secret (`tls.crt` = leaf plus chain, `tls.key`) annotated with thumbprint and job ID. Keep the previous revision as a labelled Secret. |
| AD-K8S-06 | GitOps | If Argo CD or Flux manages the cluster, open a pull request or update the sealed secret instead of writing directly, to avoid drift. |
| AD-K8S-07 | Activate | Ingress controllers and routers normally reload on Secret change. For pods mounting the Secret, run a rollout restart honouring PodDisruptionBudgets and readiness gates. |
| AD-K8S-08 | Verify and rollback | Probe the route or ingress host with SNI from the zone; compare thumbprint, SAN, chain, expiry. Rollback restores the previous Secret and restarts. |
| AD-K8S-09 | Discover | List `kubernetes.io/tls` Secrets (parse the certificate only), cert-manager Certificate resources and route and ingress TLS hosts. |
| AD-K8S-10 | Schedulers | The job may be run by Rundeck or IWS with the service account, as in the existing pattern (FR-EXE-002). |

### 7.5 Load balancers and firewalls (adapter LBX, P2 for F5 and NetScaler, P3 for others)

| ID | Aspect | Specification |
|---|---|---|
| AD-LBX-01 | Scope | F5 BIG-IP (TMOS 14 and later) and Citrix NetScaler in P2; Palo Alto, Fortinet, Cisco, A10 in P3. |
| AD-LBX-02 | Access | Vendor REST API (iControl REST, NITRO) over HTTPS from the zone MID Server. Token or service account from the vault. Management-plane ACL allows only MID addresses. |
| AD-LBX-03 | Key and CSR | Generated on the device (FIPS HSM if present); the key stays on the device. |
| AD-LBX-04 | Install | Import certificate and chain as a new, versioned object. Never overwrite the existing one. |
| AD-LBX-05 | Activate | Update the client-SSL profile to the new object, sync the device group, save the configuration. |
| AD-LBX-06 | Verify and rollback | Probe every VIP and each TLS pool member; confirm the standby synchronised. Rollback points the profile back to the previous object and syncs. |

### 7.6 Databases and middleware (P3)

SQL Server (Windows adapter plus service restart), PostgreSQL (`ssl_cert_file` plus reload), Oracle (wallet, `orapki`), MQ and Kafka (keystore). Restarts require a change window (FR-SAF-009).

### 7.7 Network devices (P3)

Routers, switches, printers and appliances through SCEP or EST enrolment or vendor CLI over SSH. If "iOS" in the original request meant Cisco IOS, this is where it would be covered (Q8).

### 7.8 Backlog of further platforms

VMware vCenter and ESXi, SAP, Exchange, ADFS, mail gateways, SSH certificate authorities. Each is added as an adapter without changing the core.

### 7.9 Deferred by decision: Apple and cloud services

Not in the roadmap for now, as agreed. The design keeps them possible: iOS and iPadOS can only receive certificates through MDM configuration profiles (SCEP or ACME payloads, key on the device), macOS supports MDM and direct methods, and cloud services (Azure Key Vault with Application Gateway, AWS ACM with ELB or CloudFront, Google Certificate Manager) would use workload identity and certificate import. They can be added as adapters and executors later without changing the strategy, matching or closed-loop model.


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
