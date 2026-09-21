# Certificate Deployment Manager (CDM): Prerequisites and Readiness Checklist

| Item | Detail |
|---|---|
| Version | 1.0 (draft) |
| Date | 2026-09-21 |
| Companion to | CDM_End_to_End_Specification.md (called "the specification" below) |
| Purpose | Everything that must be ready before implementation starts, in the order it should be done, with an owner, a reason and a way to prove it is ready |

> Written for: the teams who have to provide something (ServiceNow, PKI and Sectigo, CyberArk, network and firewall, Windows, Linux, Java application owners, security, change management). Each team can take its own step from this document. **Do not write any password, key or secret into this document.** Secrets go into CyberArk only.

## Contents

- [1. How to use this document](#1-how-to-use-this-document)
- [2. The short list: what to start first](#2-the-short-list-what-to-start-first)
- [3. Who does what](#3-who-does-what)
- [4. Step 1: Organise the work](#4-step-1-organise-the-work)
- [5. Step 2: ServiceNow](#5-step-2-servicenow)
- [6. Step 3: Sectigo](#6-step-3-sectigo)
- [7. Step 4: CyberArk](#7-step-4-cyberark)
- [8. Step 5: MID Servers and network](#8-step-5-mid-servers-and-network)
- [9. Step 6: Target servers (Windows IIS, Linux Apache, Java)](#9-step-6-target-servers-windows-iis-linux-apache-java)
- [10. Step 7: Lab and pilot](#10-step-7-lab-and-pilot)
- [11. Step 8: Security and change approvals](#11-step-8-security-and-change-approvals)
- [12. Step 9: Readiness gates](#12-step-9-readiness-gates)
- [13. Status tracker](#13-status-tracker)
- [Appendix A: Input templates to fill](#appendix-a-input-templates-to-fill)
- [Appendix B: Verification commands](#appendix-b-verification-commands)
- [Appendix C: Sample access rules (indicative)](#appendix-c-sample-access-rules-indicative)

---

## 1. How to use this document

1. The work is split into nine steps. Steps 2 to 6 can run in parallel once Step 1 is done.
2. Every prerequisite has an ID (PRE-xxx-nn), a **Stage** and a **Status**.
   - **Stage POC** means it is needed to build and prove the tool on the ServiceNow personal instance with lab servers.
   - **Stage PROD** means it is needed for the licensed instance, the real Sectigo, the real CyberArk and real servers.
   - **Stage both** means it is needed in both.
3. **Owner** is the role that provides it. Replace the role with a name in the tracker (section 13).
4. **Proof** is how you show it is ready. Section Appendix B has the commands. Attach the result (not the secret) to the tracker.
5. **Status** values: Not started, In progress, Ready, Blocked (with the reason).
6. The **input templates** you have to fill in are in Appendix A (T1 to T11). Fill them step by step and send them back. Nothing is needed all at once.
7. The three **gates** in Step 9 say when implementation can start (POC), when a pilot on real servers can start, and when production is allowed.

Stage summary of the whole project: build and prove on the personal instance (POC), then repeat on the licensed instance with real systems (PROD). See chapter 14 and 16 of the specification.

---

## 2. The short list: what to start first

These take the longest because they need approvals or other teams. Start them on day one.

| # | Item | Why it is slow | Step |
|---|---|---|---|
| 1 | Written answer from Sectigo that they can create the private key with the certificate and deliver it by API (and how) | Depends on Sectigo support and your account settings. It decides the key design | 3 |
| 2 | Sectigo API account and access from the MID Server and, if required, from ServiceNow | Account creation, role setup and IP allow-listing | 3 |
| 3 | CyberArk application identity, safes and test retrieval from the MID host | CyberArk team approvals and certificate-based application authentication | 4 |
| 4 | Firewall rules from the MID Server to Sectigo, CyberArk, ServiceNow and the servers | Change lead time | 5 |
| 5 | Deployment service accounts on Windows and Linux with only the needed rights | Access approvals | 6 |
| 6 | Sample export of certificate records from ServiceNow Discovery (to confirm the fields) | Needs someone with CMDB access, and confirms the matching design | 2 |
| 7 | Pilot servers chosen, with owners and change windows | Needs business owners | 7 |
| 8 | Security review of the key handling design | Security team capacity | 8 |
| 9 | Change approval model for automated certificate changes | Change board timing | 8 |
| 10 | Names for the people in Step 1 | Nothing starts without owners | 1 |

---

## 3. Who does what

| Team or role | Steps and items |
|---|---|
| Project lead and sponsor | Step 1, Step 9 |
| ServiceNow administrator | Step 2, MID installation in Step 5 |
| CMDB and Discovery owner | Step 2 (PRE-SN-04 to PRE-SN-08) |
| PKI and Sectigo administrator | Step 3 |
| CyberArk administrator | Step 4 |
| Network and firewall team | Step 5 (PRE-NET) |
| Windows and IIS team | Step 6 (PRE-WIN) |
| Linux and Apache team | Step 6 (PRE-LNX) |
| Java application owners | Step 6 (PRE-JVA) |
| Application and service owners (pilot) | Step 7 |
| Security architect | Step 8 |
| Change manager | Step 8 |

---

## 4. Step 1: Organise the work

Goal: named owners, agreed scope, and a way to decide.

| ID | Prerequisite | Why it is needed | Owner | Stage | Proof | Status |
|---|---|---|---|---|---|---|
| PRE-GOV-01 | A named project sponsor and a decision owner | Open questions must be decided quickly | Sponsor | both | Names in template T1 | Not started |
| PRE-GOV-02 | A named owner (and a backup) for every step in this document | Each step has a person who answers for it | Project lead | both | Template T1 complete | Not started |
| PRE-GOV-03 | Scope confirmed: technologies (Windows IIS, Linux Apache, Java), the zones, and the pilot servers. Apple, cloud, IWS and Rundeck are out | Prevents work on things that are not needed | Sponsor | both | Signed scope line in the tracker | Not started |
| PRE-GOV-04 | A weekly readiness review meeting and one shared place for status | Keeps the steps moving | Project lead | both | Meeting set, tracker shared | Not started |
| PRE-GOV-05 | A rule for sharing information: no secrets in documents, tickets or chat. Only CyberArk holds secrets | Avoids leaking credentials while collecting inputs | Security architect | both | Rule communicated | Not started |
| PRE-GOV-06 | The person who can approve each readiness gate (Step 9) | Gates must have an approver | Sponsor | both | Names in T1 | Not started |

---

## 5. Step 2: ServiceNow

Goal: an instance where CDM can be built, and proof that Discovery holds the data the matching needs.

| ID | Prerequisite | Why it is needed | Owner | Stage | Proof | Status |
|---|---|---|---|---|---|---|
| PRE-SN-01 | The personal developer instance is active, you have administrator access, and the release is known | Where the POC is built. Personal instances can be reclaimed after inactivity, so keep it in use and keep the work exportable | ServiceNow administrator | POC | Login works; release name recorded in T2 | Not started |
| PRE-SN-02 | The licensed instances (development, test, production) are named, with URLs, release and administrator access | Where the product will run. The scoped application moves there | ServiceNow administrator | PROD | URLs and release in T2 | Not started |
| PRE-SN-03 | Products and plugins are available and active: Discovery (certificate discovery), MID Server, Flow Designer, scoped application development. If you choose ServiceNow's external credential storage for CyberArk, that as well | CDM is a scoped application that reads Discovery data and runs jobs on the MID Server | ServiceNow administrator | both | List of active plugins attached | Not started |
| PRE-SN-04 | Discovery scans certificates on the in-scope servers every day, and the schedule time is known | The closed loop depends on the next-day scan | CMDB and Discovery owner | both | Schedule name and time in T2; last three run dates | Not started |
| PRE-SN-05 | Sample export of at least 20 certificate records from the CMDB with: name, thumbprint, serial, SAN, server, valid from, valid to, last scanned (and the class and field names used) | Confirms the fields exist and their format, so the matching rules are right (specification item V2) | CMDB and Discovery owner | both | CSV export (no keys, no secrets; certificate data only) | Not started |
| PRE-SN-06 | Each certificate record is related to its server record, and the server names match the names the MID Server will use | CDM must know which server a certificate is on | CMDB and Discovery owner | both | Three examples showing certificate and server | Not started |
| PRE-SN-07 | Data quality is known: duplicates, records not scanned in the last 36 hours, records without an owner group | CDM does not decide on stale data. You need to know how many that is | CMDB and Discovery owner | both | Counts recorded in T2 | Not started |
| PRE-SN-08 | The SAN format is known (separator, case, wildcard handling) and the date format and time zone | The matching compares SAN sets and exact UTC times | CMDB and Discovery owner | both | Note attached to the sample export | Not started |
| PRE-SN-09 | Developer accounts to build the scoped application, and test users for the roles cdm_admin, cdm_owner, cdm_operator, cdm_approver, cdm_auditor | Building and testing role separation | ServiceNow administrator | both | Accounts created | Not started |
| PRE-SN-10 | Outbound email works, and distribution lists exist for each owner group | CDM notifications go to owner groups | ServiceNow administrator | both | Test email received | Not started |
| PRE-SN-11 | A scope name for the application is reserved and the path from the personal instance to the licensed instances is agreed (update sets or the application repository) | The same application is moved between instances | ServiceNow administrator | both | Scope name and method recorded in T2 | Not started |
| PRE-SN-12 | It is known whether the instance can call Sectigo directly and whether Sectigo restricts access by IP (then the instance egress addresses must be allowed), or whether all Sectigo calls will go through the MID Server | Decides where the Sectigo list calls run | ServiceNow administrator and Sectigo administrator | both | Decision recorded in T2 | Not started |
| PRE-SN-13 | The ServiceNow Discovery credential and account used for scanning is known, and confirmed to be different from any account CDM will use for deployment | Discovery and deployment must stay separate | CMDB and Discovery owner | PROD | Account names (not secrets) in T2 | Not started |
| PRE-SN-14 | Whether one server can be rescanned on demand is known (optional, not needed for the first release) | Would shorten confirmation from a day to minutes later | CMDB and Discovery owner | PROD | Yes or no in T2 | Not started |

Inputs to provide for this step: **T2 (ServiceNow details)** and the sample export from PRE-SN-05.

---

## 6. Step 3: Sectigo

Goal: proof that Sectigo can list new certificates by API and deliver the certificate together with its private key by API, and an account that may do so.

| ID | Prerequisite | Why it is needed | Owner | Stage | Proof | Status |
|---|---|---|---|---|---|---|
| PRE-SG-01 | The Sectigo Certificate Manager tenant details: tenant URL, customer URI, and the organisation or departments in scope | The connector needs them | PKI and Sectigo administrator | both | Template T3 | Not started |
| PRE-SG-02 | **Written confirmation from Sectigo that the private key can be created together with the certificate and delivered by API**, including: which API call, the bundle format (PKCS#12 or PEM), how the passphrase is set, how many times and for how long it can be downloaded, whether Sectigo keeps a copy of the key, and whether a renewal gets a new key (specification item V1) | This decides the key design. If it is not possible the fallback is a key created on the server | PKI and Sectigo administrator | both | Sectigo reply or ticket attached | Not started |
| PRE-SG-03 | An API account dedicated to CDM (not a personal account) with only the rights needed: list certificates, collect certificates, fetch the bundle (and later renew) for the organisations in scope | Least privilege and traceability | PKI and Sectigo administrator | both | Account name in T3; rights list | Not started |
| PRE-SG-04 | The API secret for that account stored in CyberArk (Step 4), never shared by mail or chat | Secrets only in the vault | PKI and CyberArk administrators | both | CyberArk object name in T3 | Not started |
| PRE-SG-05 | API documentation for your version, the base URL, rate limits, and any IP restriction | Correct calls and safe polling | PKI and Sectigo administrator | both | Links and limits in T3 | Not started |
| PRE-SG-06 | The certificate profiles or types in scope, and the allowed key algorithms and sizes for server-generated keys | Policy checks and the bundle content | PKI and Sectigo administrator | both | Profile names in T3 | Not started |
| PRE-SG-07 | Domain control validation is in place for the domains of the pilot certificates | Without it the CA cannot issue | PKI and Sectigo administrator | PROD | Validation status per domain | Not started |
| PRE-SG-08 | How a renewal reaches the landing area today: who triggers it, how many days before expiry, and any auto-renew setting | CDM starts when a new certificate is available. It must be there before the renewal window starts | PKI and Sectigo administrator | both | Description in T3 | Not started |
| PRE-SG-09 | Two example pairs (old certificate and its renewal) with names, SANs, serials, thumbprints and dates | Lets the matching rules be tested on real data | PKI and Sectigo administrator | both | Table of two pairs (public data only) | Not started |
| PRE-SG-10 | A sandbox or test tenant, or a set of test certificates, for the POC. If neither is available, the POC uses a test CA that behaves like the landing area | The POC needs a certificate source that is safe to test against | PKI and Sectigo administrator | POC | Decision in T3 | Not started |
| PRE-SG-11 | A list of the certificates in scope that are **not** issued by Sectigo | They are reported as unknown and are out of automation | PKI and Sectigo administrator | PROD | List | Not started |
| PRE-SG-12 | A Sectigo support contact and an escalation path | API questions will come up | PKI and Sectigo administrator | both | Contact in T3 | Not started |

Inputs to provide for this step: **T3 (Sectigo details)** and the two example pairs from PRE-SG-09.

---

## 7. Step 4: CyberArk

Goal: the MID Server can obtain every credential just in time, and nothing is stored anywhere else.

| ID | Prerequisite | Why it is needed | Owner | Stage | Proof | Status |
|---|---|---|---|---|---|---|
| PRE-CA-01 | CyberArk version and the way applications retrieve credentials: Central Credential Provider (CCP) URL, or Credential Provider on the MID host | The MID Server retrieves credentials at job time | CyberArk administrator | both | Details in T4 | Not started |
| PRE-CA-02 | The access method for CDM is decided: the MID Server calls CCP directly, or ServiceNow external credential storage for CyberArk is used (requires the right MID version and plugin) (specification item V3) | Two supported options with different setup | CyberArk and ServiceNow administrators | both | Decision in T4 | Not started |
| PRE-CA-03 | An application identity (for example CDM) per zone, with the authentication method (client certificate) and the allowed MID hosts or addresses | CyberArk only releases secrets to a known application from known hosts | CyberArk administrator | both | AppID names in T4 | Not started |
| PRE-CA-04 | Safes: one per zone for deployment accounts (for example CDM-Internal, CDM-Dmz), one for Sectigo (CDM-Sectigo), one for Java keystore passwords (CDM-Java). The CDM application has retrieve-only rights | Separation by zone and least privilege | CyberArk administrator | both | Safe list in T4 | Not started |
| PRE-CA-05 | Accounts (objects) created with agreed names: Sectigo API secret, Windows deployment account (per zone), Linux SSH key or certificate (per zone), each Java keystore and key password | These are the credentials the jobs use | CyberArk administrator with the platform teams | both | Object names in T4 (no secrets) | Not started |
| PRE-CA-06 | Rotation and reconciliation are set where applicable for the target accounts, and it is confirmed that a retrieval always returns the current value | Rotated passwords must never break a job | CyberArk administrator | PROD | Policy names in T4 | Not started |
| PRE-CA-07 | A **test retrieval from the MID host succeeds** for each object, and the retrieval appears in the CyberArk audit | Proof that the path works end to end | CyberArk administrator | both | Test result and audit line (no secret) | Not started |
| PRE-CA-08 | The MID host trusts the CyberArk server certificate chain and the firewall allows MID to CyberArk on 443 | Otherwise retrieval fails | Network team and CyberArk administrator | both | Test from the MID host | Not started |
| PRE-CA-09 | CyberArk availability is known (redundancy of the CCP) and an agreed behaviour when it is down: jobs wait and retry, never a stored password | Deployments depend on the vault | CyberArk administrator | PROD | Statement in T4 | Not started |
| PRE-CA-10 | A lab safe or a developer instance for the POC. If none exists, a temporary stand-in that is clearly marked and removed before production | The POC cannot wait for production CyberArk | CyberArk administrator | POC | Decision in T4 | Not started |

Inputs to provide for this step: **T4 (CyberArk details)**.

---

## 8. Step 5: MID Servers and network

Goal: MID Servers that can reach ServiceNow, Sectigo, CyberArk and the servers, and are safe.

### 8.1 MID Servers

| ID | Prerequisite | Why it is needed | Owner | Stage | Proof | Status |
|---|---|---|---|---|---|---|
| PRE-MID-01 | The MID hosts per zone: operating system, size and host names. POC: the laptop. PROD: at least two MID Servers per zone for high availability. Follow ServiceNow's current MID requirements for size | The executor for every job | ServiceNow administrator | both | Hosts listed in T5 | Not started |
| PRE-MID-02 | MID software installed at the version that matches the instance release, service running, status Up and Validated | It cannot run jobs otherwise | ServiceNow administrator | both | MID status screenshot | Not started |
| PRE-MID-03 | A dedicated, least-privilege service account for the MID service. Not a domain administrator | Limits the damage if the MID host is compromised | ServiceNow administrator and Windows or Linux team | both | Account name in T5 | Not started |
| PRE-MID-04 | The MID host reaches the instance by outbound HTTPS 443 (through the proxy if one is used) | ECC queue connection | Network team | both | MID status Up | Not started |
| PRE-MID-05 | Time is synchronised (NTP) on the MID hosts and on all target servers | Timestamps are compared exactly | Windows and Linux teams | both | Time offset under one minute | Not started |
| PRE-MID-06 | The MID Java trust store contains the certificate authorities needed for CyberArk, Sectigo and the internal servers (mind TLS inspection proxies) | Otherwise HTTPS calls from the MID fail | ServiceNow administrator | both | Test calls succeed | Not started |
| PRE-MID-07 | A protected temporary work directory on each MID host on an encrypted volume, readable only by the MID service account | The certificate and key bundle lives here for a few minutes | Windows or Linux team | both | Path and encryption noted in T5 | Not started |
| PRE-MID-08 | It is agreed how the signed adapter scripts are delivered to the MID host and how unsigned scripts are refused | Only approved adapters may run | ServiceNow administrator and Security architect | both | Method noted in T5 | Not started |
| PRE-MID-09 | Antivirus or EDR on the MID host and the servers will not quarantine the adapter operations or the temporary directory, and its exceptions are agreed with security | Otherwise imports and file writes fail silently | Security architect | both | Exception list | Not started |
| PRE-MID-10 | Decision: does deployment use the same MID Servers as Discovery or a separate set? Deployment accounts must differ either way (specification item V8) | Separation of discovery and deployment | Security architect and ServiceNow administrator | PROD | Decision in T5 | Not started |
| PRE-MID-11 | MID Server monitoring and alerting is in place (heartbeat, status) | A down MID Server must be noticed | ServiceNow administrator | PROD | Alert test | Not started |

Inputs to provide for this step: **T5 (Zones and MID Servers)**.

### 8.2 Network access

Every connection is opened from the MID Server or from the instance outward. Nothing connects in to the MID Server.

| ID | From | To | Port and protocol | Purpose | Stage |
|---|---|---|---|---|---|
| PRE-NET-01 | MID Server | ServiceNow instance | 443, HTTPS | ECC queue | both |
| PRE-NET-02 | MID Server | Sectigo API (tenant URL) | 443, HTTPS | List certificates, fetch bundle | both |
| PRE-NET-03 | ServiceNow instance (or the MID Server, per PRE-SN-12) | Sectigo API | 443, HTTPS | List certificates, public certificate | both |
| PRE-NET-04 | MID Server | CyberArk CCP | 443, HTTPS with client certificate | Credentials just in time | both |
| PRE-NET-05 | MID Server | Windows servers | 5986, WinRM over HTTPS | Windows IIS adapter. Port 5985 is allowed only in the POC lab | both |
| PRE-NET-06 | MID Server | Linux servers | 22, SSH | Apache, nginx and Java adapters | both |
| PRE-NET-07 | MID Server | Live endpoints of the services | 443 or the application port (for example 8443), TLS | Live verification | both |
| PRE-NET-08 | MID Server | DNS and NTP | 53 and 123 | Name resolution and time | both |

| ID | Prerequisite | Why it is needed | Owner | Stage | Proof | Status |
|---|---|---|---|---|---|---|
| PRE-NET-09 | The firewall rules above are requested, approved and open for the zones in scope, with the source addresses of the MID hosts | Without them nothing can run | Network team | both | Test results from the MID host (Appendix B.1) | Not started |
| PRE-NET-10 | Server host names resolve from the MID host and match the names in the CMDB | Certificates are found by server name | Network team | both | Name lookup output | Not started |
| PRE-NET-11 | Any proxy in the path is known, and its rules for Sectigo, CyberArk and ServiceNow are set | Proxies often break TLS or block APIs | Network team | both | Proxy settings in T5 | Not started |

Inputs to provide for this step: the firewall request in **T10 (Firewall requests)**.
