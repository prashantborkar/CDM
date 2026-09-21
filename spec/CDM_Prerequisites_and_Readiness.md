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
| PRE-MID-10 | Decision: does deployment use the same MID Servers as Discovery or a separate set? Deployment accounts must differ either way (specification chapter 10) | Separation of discovery and deployment | Security architect and ServiceNow administrator | PROD | Decision in T5 | Not started |
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


---

## 9. Step 6: Target servers (Windows IIS, Linux Apache, Java)

Goal: the servers are reachable and safe to automate, and we know exactly what is installed where. Discovery only tells us the server and the certificate name. The details below (sites, paths, keystores) come from the server owners and go into the deployment profiles (specification section 7.8).

### 9.1 Windows IIS

| ID | Prerequisite | Why it is needed | Owner | Stage | Proof | Status |
|---|---|---|---|---|---|---|
| PRE-WIN-01 | The in-scope Windows servers are listed with the operating system (Windows Server 2016 or later) and IIS version (8.5 or later) | Scope of the Windows adapter | Windows team | both | Template T6 and T7 | Not started |
| PRE-WIN-02 | PowerShell 5.1 or later and the IIS administration module are available on each server | The adapter uses them | Windows team | both | Appendix B.4 output | Not started |
| PRE-WIN-03 | A WinRM over HTTPS listener (port 5986) with a valid certificate is set up and open from the MID host. Port 5985, Basic authentication and unencrypted traffic are not allowed, except in the POC lab | Secure transport for the certificate and key | Windows team | both | Test-WSMan with SSL succeeds | Not started |
| PRE-WIN-04 | A deployment account (from CyberArk) with only these rights: manage certificates in the Local Machine store, manage IIS bindings, set permissions on private keys, and remote PowerShell (or a constrained JEA endpoint). Not a domain administrator | Least privilege | Windows team and CyberArk administrator | both | Rights list and a test run | Not started |
| PRE-WIN-05 | For each IIS site to be automated: site name, IP, port, host header, SNI flag and application pool identity | The profile needs them and the private key permission goes to the pool identity | Windows team | both | Template T7 | Not started |
| PRE-WIN-06 | The thumbprint bound to each binding today, equal to the thumbprint in the CMDB | The pre-check stops if the server differs from the CMDB | Windows team | both | Binding listing next to the CMDB record | Not started |
| PRE-WIN-07 | PowerShell policies (execution policy, constrained language mode, AppLocker or WDAC) allow the signed adapter operations | Otherwise the adapter is blocked | Windows team and Security | both | Test run | Not started |
| PRE-WIN-08 | Antivirus or EDR will not block the import of a certificate bundle and its temporary file | Silent failures otherwise | Security | both | Exception agreed | Not started |
| PRE-WIN-09 | An IIS configuration backup exists or is allowed, and a restore procedure is known | Extra safety for rollback | Windows team | PROD | Procedure link | Not started |
| PRE-WIN-10 | Change window and impact statement agreed: a binding update needs no restart | Owners informed | Windows team and Change manager | PROD | Statement | Not started |

Inputs: **T7 (Windows IIS input)** for each server.

### 9.2 Linux Apache (and nginx)

| ID | Prerequisite | Why it is needed | Owner | Stage | Proof | Status |
|---|---|---|---|---|---|---|
| PRE-LNX-01 | The in-scope Linux servers are listed with distribution, version, and Apache or nginx version | Scope of the Linux adapter | Linux team | both | Template T6 and T8 | Not started |
| PRE-LNX-02 | SSH is enabled, a deployment user exists, login is by key or signed certificate only (no password), and the host keys are recorded | Secure, non-interactive access | Linux team | both | Appendix B.5 SSH test | Not started |
| PRE-LNX-03 | The deployment user's sudo rights are limited to the commands the adapter needs (Appendix C) and reviewed by Linux security | Least privilege | Linux team and Security | both | Reviewed rule | Not started |
| PRE-LNX-04 | The Apache configuration uses stable file names for the certificate, chain and key (or the exact paths are recorded), and the virtual hosts are listed | The adapter swaps files and keeps the configuration unchanged | Linux team | both | Template T8 | Not started |
| PRE-LNX-05 | The owner and permission standard for the certificate and key files is agreed (for example key root:root 0600, or root with the service group 0640) | The adapter applies it | Linux team | both | Standard noted in T8 | Not started |
| PRE-LNX-06 | SELinux mode and AppArmor profile are known, with the expected file contexts for the paths | The new files must be readable by the web server | Linux team | both | ls -Z output | Not started |
| PRE-LNX-07 | openssl and apachectl (or nginx) are installed and the configuration test passes today | Baseline for the pre-check | Linux team | both | apachectl configtest output | Not started |
| PRE-LNX-08 | A root-only backup directory (for example /var/backups/cdm, mode 0700) exists with enough disk space | Rollback point | Linux team | both | Directory and free space | Not started |
| PRE-LNX-09 | A graceful reload is permitted and has been tested on a non-production server. The window is agreed | The design reloads and does not restart | Linux team and Change manager | PROD | Test result | Not started |
| PRE-LNX-10 | The fingerprint of the certificate the server uses today equals the CMDB thumbprint | The pre-check stops on a difference | Linux team | both | Fingerprint next to the CMDB record | Not started |

Inputs: **T8 (Linux Apache input)** for each server.

### 9.3 Java applications

| ID | Prerequisite | Why it is needed | Owner | Stage | Proof | Status |
|---|---|---|---|---|---|---|
| PRE-JVA-01 | The in-scope Java applications are listed: name, server, Java version, application server | Scope of the Java adapter | Java application owners | both | Template T9 | Not started |
| PRE-JVA-02 | For each application: keystore path, type (JKS or PKCS#12), alias, and the truststore location if separate | The profile needs them | Java application owners | both | Template T9 | Not started |
| PRE-JVA-03 | The keystore and key passwords are placed in CyberArk (safe CDM-Java) with agreed object names. They are never sent in mail or chat | Passwords come from the vault | Java application owners and CyberArk administrator | both | Object names in T9 | Not started |
| PRE-JVA-04 | keytool is available to the deployment user, and the path is known | The adapter imports with keytool | Java application owners | both | Appendix B.7 output | Not started |
| PRE-JVA-05 | How the application loads the keystore, and whether a hot reload exists (for example Tomcat 9 or later). Otherwise: the restart procedure, service name, health check URL, restart tolerance and change window | Reload is preferred, a restart needs a window | Java application owners | both | Template T9 | Not started |
| PRE-JVA-06 | The owner and permission of the keystore file, and the user that runs the application | Kept unchanged after the update | Java application owners | both | ls output | Not started |
| PRE-JVA-07 | Any other place where the certificate is pinned (client truststores, configuration files) is known | A renewed certificate may break pinned clients | Java application owners | PROD | Statement in T9 | Not started |
| PRE-JVA-08 | The fingerprint of the certificate in the alias equals the CMDB thumbprint | The pre-check stops on a difference | Java application owners | both | keytool output next to the CMDB record | Not started |

Inputs: **T9 (Java input)** for each application.

---

## 10. Step 7: Lab and pilot

Goal: safe places to build and prove the tool first, then a small real pilot.

### 10.1 Lab for the proof of concept

| ID | Prerequisite | Why it is needed | Owner | Stage | Proof | Status |
|---|---|---|---|---|---|---|
| PRE-LAB-01 | A Windows lab server with IIS, one site and an HTTPS binding using an old test certificate | Target for the IIS adapter | Windows team | POC | Binding listing | Not started |
| PRE-LAB-02 | A Linux lab (WSL or a small virtual machine) with Apache and a virtual host using an old test certificate | Target for the Apache adapter | Linux team | POC | apachectl -S output | Not started |
| PRE-LAB-03 | A small Java application with a PKCS#12 keystore holding an old test certificate | Target for the Java adapter | Java application owners | POC | keytool output | Not started |
| PRE-LAB-04 | Lab host names resolve from the MID host, and the test certificates carry those names in their SAN | Matching and verification use names | Network team | POC | Name lookup | Not started |
| PRE-LAB-05 | Old test certificates with a short validity, so they are inside the renewal window | Lets the flow run immediately | PKI and Sectigo administrator | POC | Certificate dates | Not started |
| PRE-LAB-06 | New test certificates for the same names are waiting in the Sectigo sandbox (or test CA) landing area | The replacements to deploy | PKI and Sectigo administrator | POC | List call shows them | Not started |
| PRE-LAB-07 | Either real Discovery covers the lab servers, or a clearly labelled scan simulator updates the certificate records daily and on demand. It is agreed who builds and runs it | The closed loop needs certificate records that refresh | CMDB and Discovery owner | POC | Records refresh after a change | Not started |
| PRE-LAB-08 | The lab MID Server can reach all lab servers | Executor | ServiceNow administrator | POC | Connection tests | Not started |

### 10.2 Pilot on real servers

| ID | Prerequisite | Why it is needed | Owner | Stage | Proof | Status |
|---|---|---|---|---|---|---|
| PRE-PIL-01 | A pilot set is chosen: two or three servers per technology, non-critical first, with a mix of certificate lifetimes (one month and one year) | Small, safe, representative | Project lead and service owners | PROD | Template T6 | Not started |
| PRE-PIL-02 | Each pilot server has a business owner who agrees, and a change window | Consent and timing | Service owners and Change manager | PROD | Agreement recorded | Not started |
| PRE-PIL-03 | The pilot certificates are Sectigo-issued, their expiry dates are known, and it is confirmed that a replacement will be in the landing area before their renewal windows | Something must be there to deploy | PKI and Sectigo administrator | PROD | List with dates | Not started |
| PRE-PIL-04 | A rollback and contact plan exists for each pilot server: who to call, what to do if the rollback fails | Safety net | Service owners | PROD | Plan | Not started |
| PRE-PIL-05 | For each pilot server the CMDB record, the Sectigo record and the server itself show the same certificate (thumbprint, SAN, dates) | Confirms the data is clean before automation | Project lead | PROD | Three-way comparison | Not started |

Inputs: **T6 (Pilot and lab inventory)**.

---

## 11. Step 8: Security and change approvals

Goal: the design and the operating model are approved before the first real change.

| ID | Prerequisite | Why it is needed | Owner | Stage | Proof | Status |
|---|---|---|---|---|---|---|
| PRE-SCR-01 | Security review of the key handling design is done. Sectigo creates the key, the MID Server fetches and installs it, the key is wiped afterwards, and one key may be shared by several servers of the same service. Risks are accepted or changed | This is the most sensitive part of the design | Security architect | both | Signed review | Not started |
| PRE-SCR-02 | Approval for key material to exist in MID memory or in encrypted temporary storage for a few minutes, with evidence of disk encryption on the MID hosts | Meets the key handling principles | Security architect | both | Approval and evidence | Not started |
| PRE-SCR-03 | The change model for automated certificate changes is agreed: a pre-approved standard change, or an approval step, and the windows | Automated changes need a route | Change manager | both | Change model document | Not started |
| PRE-SCR-04 | Logging and SIEM requirements and the classification of certificate data (identity data only is stored in ServiceNow) are agreed | Audit and data handling | Security architect | PROD | Requirements | Not started |
| PRE-SCR-05 | All access requests are raised and tracked with their lead times: CyberArk application identity and safes, firewall rules, service accounts, sudo rules, Sectigo API account | These are the slowest items | Project lead | both | Request numbers in the tracker | Not started |
| PRE-SCR-06 | A security testing plan is agreed: secret scan of ServiceNow, logs and MID hosts, adapter tamper test, penetration test, and the time it needs | Required before production | Security architect | PROD | Plan | Not started |
| PRE-SCR-07 | Compliance requirements that apply (for example PCI DSS, ISO 27001, SOC 2) are identified | Reporting and evidence | Security architect | PROD | List | Not started |
| PRE-SCR-08 | The incident process is agreed: who is called when a deployment fails, a rollback fails, or a deployment is not confirmed | Failures need an owner | Operations lead | PROD | Contact and process | Not started |
| PRE-SCR-09 | A manual runbook exists for renewing certificates if CDM or ServiceNow is unavailable | The business must not depend on one tool | Operations lead | PROD | Runbook | Not started |
| PRE-SCR-10 | Retention for audit and job records is agreed (default 13 months online) | Storage and compliance | Security architect | PROD | Decision in T11 | Not started |

Inputs: **T11 (Policy decisions)**.

---

## 12. Step 9: Readiness gates

### 12.1 What is needed when building (proof of concept)

The build follows the order in the specification, section 14.3. Each build step needs these prerequisites to be ready before it starts.

| Build step | Needs |
|---|---|
| 1. Scoped application, tables and settings | PRE-SN-01, PRE-SN-03, PRE-SN-09, PRE-SN-11 |
| 2. Connect the MID Server | PRE-MID-01 to PRE-MID-06, PRE-NET-01, PRE-NET-08 |
| 3. Sectigo connector | PRE-SG-01 to PRE-SG-06, PRE-SG-10, PRE-NET-02, PRE-NET-03 |
| 4. Sync and matching | PRE-SN-04 to PRE-SN-08, PRE-SG-09 |
| 5. Planning and deployment profiles | PRE-WIN-05, PRE-LNX-04, PRE-JVA-02, PRE-LAB-01 to PRE-LAB-05 |
| 6. Adapters (IIS, Apache, Java) | PRE-NET-05 to PRE-NET-07, PRE-NET-10, PRE-WIN-02 to PRE-WIN-04, PRE-WIN-07, PRE-LNX-02, PRE-LNX-03, PRE-LNX-07, PRE-LNX-08, PRE-JVA-04 to PRE-JVA-06, PRE-MID-07, PRE-MID-08, PRE-CA-10 |
| 7. Confirmation by the next scan | PRE-SN-04, PRE-LAB-07 |
| 8. Failure paths | PRE-LAB-06, PRE-WIN-09, PRE-LNX-09 |
| 9. Replace the stand-ins | PRE-CA-01 to PRE-CA-09, PRE-SG-02 to PRE-SG-08, PRE-SN-02 |

### 12.2 The three gates

| Gate | Meaning | Must be true | Approver |
|---|---|---|---|
| Gate 1: start building | The proof of concept can start | PRE-GOV-01 to PRE-GOV-06, PRE-SN-01, PRE-SN-03, PRE-SN-09, PRE-SN-11, PRE-SG-10, PRE-CA-10, PRE-MID-01 to PRE-MID-04, PRE-LAB-01, PRE-LAB-02, PRE-LAB-04, PRE-LAB-08. The other POC items must be ready by the build step that needs them (12.1) | Sponsor |
| Gate 2: start the pilot | The tool may change real servers | Every prerequisite with Stage PROD or both in Steps 1 to 8 for the pilot servers, and PRE-PIL-01 to PRE-PIL-05, PRE-SCR-01 to PRE-SCR-05. The POC exit criteria in the specification (section 14.4) are met | Sponsor, Security architect, Change manager |
| Gate 3: production | Broad use | PRE-SCR-06 to PRE-SCR-10, the pilot ran with acceptance tests TC-01 to TC-20 passed (specification chapter 15), no item is Blocked | Sponsor, Security architect, Change manager |

---

## 13. Status tracker

Fill one line per step. Update it weekly.

| Step | Team | Item IDs | Target date | Status | Blockers |
|---|---|---|---|---|---|
| 1 Organise | Project lead | PRE-GOV-01 to PRE-GOV-06 | | Not started | |
| 2 ServiceNow | ServiceNow administrator, CMDB and Discovery owner | PRE-SN-01 to PRE-SN-14 | | Not started | |
| 3 Sectigo | PKI and Sectigo administrator | PRE-SG-01 to PRE-SG-12 | | Not started | |
| 4 CyberArk | CyberArk administrator | PRE-CA-01 to PRE-CA-10 | | Not started | |
| 5 MID and network | ServiceNow administrator, Network team | PRE-MID-01 to PRE-MID-11, PRE-NET-01 to PRE-NET-11 | | Not started | |
| 6 Targets | Windows team, Linux team, Java owners | PRE-WIN-01 to PRE-WIN-10, PRE-LNX-01 to PRE-LNX-10, PRE-JVA-01 to PRE-JVA-08 | | Not started | |
| 7 Lab and pilot | Platform teams, service owners | PRE-LAB-01 to PRE-LAB-08, PRE-PIL-01 to PRE-PIL-05 | | Not started | |
| 8 Security and change | Security architect, Change manager | PRE-SCR-01 to PRE-SCR-10 | | Not started | |
| 9 Gates | Sponsor | Gate 1, Gate 2, Gate 3 | | Not started | |

**Size:** 115 prerequisites in total: 11 needed for the proof of concept only, 24 needed for production only, 80 needed for both. By step: GOV 6, SN 14, SG 12, CA 10, MID 11, NET 11, WIN 10, LNX 10, JVA 8, LAB 8, PIL 5, SCR 10.

---

## Appendix A: Input templates to fill

Fill these step by step and send each one back when it is ready. Rows marked "Example" show the format and are to be replaced. No passwords, keys or secrets in any template: use CyberArk object names.

### T1: People and owners (Step 1)

| Role | Name | Email | Backup | Steps |
|---|---|---|---|---|
| Example: Sponsor | | | | 1, 9 |
| Project lead | | | | 1, 9 |
| ServiceNow administrator | | | | 2, 5 |
| CMDB and Discovery owner | | | | 2 |
| PKI and Sectigo administrator | | | | 3 |
| CyberArk administrator | | | | 4 |
| Network and firewall team | | | | 5 |
| Windows and IIS team | | | | 6 |
| Linux and Apache team | | | | 6 |
| Java application owners | | | | 6 |
| Security architect | | | | 8 |
| Change manager | | | | 8 |
| Operations lead | | | | 8 |

### T2: ServiceNow details (Step 2)

| Item | Value |
|---|---|
| Personal instance URL and release | |
| Licensed development, test and production instance URLs and release | |
| Active plugins (Discovery, MID Server, Flow Designer, application development, external credential storage) | |
| Discovery schedule name and time of day, and the last three run dates | |
| Certificate class or table name | |
| Field names for name, thumbprint, serial, SAN, server, valid from, valid to, last scanned | |
| SAN format (separator, case, wildcard) and date format and time zone | |
| Number of certificate records, number not scanned in 36 hours, number without owner group | |
| Scope name reserved for the application | |
| Promotion method (update sets or application repository) | |
| Where Sectigo list calls run (instance or MID Server) and IP restrictions at Sectigo | |
| Account names used by Discovery (no secrets) | |
| On-demand rescan of one server possible (yes or no) | |
| Outbound email and the distribution lists per owner group | |

### T3: Sectigo details (Step 3)

| Item | Value |
|---|---|
| Tenant URL and API base URL | |
| Customer URI | |
| Organisations or departments in scope | |
| API account name and its rights | |
| CyberArk object holding the API secret | |
| Certificate profiles or types in scope | |
| Key algorithms and sizes for server-generated keys | |
| Written answer on key creation and bundle delivery by API (attach): call, format, passphrase, downloads, key copy kept, renewal key | |
| Rate limits and IP restrictions | |
| How and when renewals are triggered today, and days before expiry the new certificate is available | |
| Sandbox or test tenant available (yes or no) | |
| Support contact and escalation | |

Two example pairs (old and renewed certificate), public data only:

| Pair | Name | SAN | Serial | Thumbprint | Valid from | Valid to |
|---|---|---|---|---|---|---|
| Example: old | | | | | | |
| Example: renewed | | | | | | |

### T4: CyberArk details (Step 4)

| Item | Value |
|---|---|
| CyberArk version and access method (CCP direct or ServiceNow external credential storage) | |
| CCP URL | |
| Application ID per zone and authentication method | |
| Allowed MID hosts or addresses | |
| Safes (name, owner, application rights) | |
| Object names: Sectigo API, Windows deployment per zone, Linux deployment per zone, Java keystores | |
| Rotation and reconciliation policy names | |
| Availability and behaviour when unavailable | |
| Lab safe for the POC (yes or no) | |

### T5: Zones and MID Servers (Step 5)

| Zone | MID host | OS | Size | Service account | Temporary work directory (encrypted) | Proxy | Separate from Discovery MID (yes or no) |
|---|---|---|---|---|---|---|---|
| Example: internal | | | | | | | |
| Example: dmz | | | | | | | |

### T6: Pilot and lab inventory (Step 7)

| Server (FQDN) | Technology | Environment | Zone | Certificate name | SAN | Lifetime | Valid to | Thumbprint (CMDB) | Sectigo issued | Owner group | Change window | Restart tolerance |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Example: web01.example.com | IIS | pilot | internal | app.example.com | app.example.com | 1 year | | | yes | web-platform | Sat 22:00 | none needed |

### T7: Windows IIS input, per server (Step 6)

| Server | Site | IP | Port | Host header | SNI | Application pool identity | Current thumbprint | WinRM HTTPS ready | CyberArk deployment object |
|---|---|---|---|---|---|---|---|---|---|
| Example: web01.example.com | Default Web Site | * | 443 | app.example.com | yes | IIS APPPOOL\AppPool1 | | yes | svc-cdm-win-deploy |

### T8: Linux Apache input, per server (Step 6)

| Server | Distribution | Web server and version | Virtual host | Certificate path | Chain path | Key path | Key owner and mode | SELinux or AppArmor | Reload command | Deployment user | Backup directory |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Example: lnx01.example.com | RHEL 9 | Apache 2.4 | portal.example.com | /etc/pki/tls/certs/portal.crt | /etc/pki/tls/certs/portal-chain.crt | /etc/pki/tls/private/portal.key | root:root 0600 | SELinux enforcing | apachectl graceful | cdmdeploy | /var/backups/cdm |

### T9: Java input, per application (Step 6)

| Application | Server | Java version | Application server | Keystore path | Type | Alias | Truststore | CyberArk object | Reload method | Service name | Restart tolerance | Health URL | Keystore owner and mode |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Example: api | app01.example.com | 17 | Spring Boot | /opt/api/conf/keystore.p12 | PKCS12 | api | default | java-keystore-api | service restart | api | 30 seconds in window | https://api.example.com/health | app:app 0640 |

### T10: Firewall requests (Step 5)

| Rule | Source | Destination | Port and protocol | Purpose | Zone | Request reference | Status |
|---|---|---|---|---|---|---|---|
| Example: NET-01 | MID host | Instance | 443 HTTPS | ECC queue | internal | | |

### T11: Policy decisions (Step 8)

| Decision | Default | Your choice |
|---|---|---|
| Renewal window maximum | 30 days | |
| Renewal window fraction of lifetime | 33 percent | |
| Renewal window floor | 3 days | |
| Deploy as soon as the replacement lands | No (wait for the window) | |
| Alert days when no replacement has landed | 30, 14, 7, 3, 1 | |
| Approval for production deployments | None at first | |
| Approval for non-production | None | |
| Production change window | 22:00 to 05:00 | |
| Confirmation timeout after deployment | 36 hours | |
| Notification groups per owner | | |
| Audit retention online | 13 months | |
| Where an unknown or unlocated certificate is reported | | |

---

## Appendix B: Verification commands

Use these to prove a prerequisite is ready. Run them from the MID host (or as stated). Put the result in the tracker. Never paste a secret. Commands that need a secret read it from an environment variable that you set in your own session.

### B.1 Network from the MID host

```text
# Windows MID host
Test-NetConnection <instance-host> -Port 443
Test-NetConnection <sectigo-host> -Port 443
Test-NetConnection <cyberark-ccp-host> -Port 443
Test-NetConnection <windows-server> -Port 5986
Test-NetConnection <linux-server> -Port 22

# Linux MID host
nc -vz <host> <port>
curl -sS -o /dev/null -w "%{http_code}\n" https://<host>/
```

### B.2 Sectigo API (indicative, confirm call and headers in your Sectigo documentation)

```text
curl -sS -H "login: $SECTIGO_USER" -H "password: $SECTIGO_PASS" -H "customerUri: $SECTIGO_URI" "https://<sectigo-api-base>/api/ssl/v1?size=5"
```

Expected: a list of certificates with status and validity. Then test the certificate and key bundle call that Sectigo confirmed (PRE-SG-02) on a test certificate.

### B.3 CyberArk retrieval (indicative)

```text
curl --cert client.pem --key client.key "https://<ccp-host>/AIMWebService/api/Accounts?AppID=CDM&Safe=CDM-Internal&Object=svc-cdm-win-deploy"
```

Expected: the account name and secret are returned (do not save or share the output), and the retrieval appears in the CyberArk audit.

### B.4 Windows server

```text
$PSVersionTable.PSVersion
Get-Module -ListAvailable WebAdministration
Test-WSMan -ComputerName <server> -UseSSL -Port 5986
Get-WebBinding -Protocol https
Get-ChildItem Cert:\LocalMachine\My | Select-Object Subject, Thumbprint, NotAfter
w32tm /query /status
```

### B.5 Linux server

```text
ssh -o BatchMode=yes cdmdeploy@<server> 'sudo -n -l'
apachectl configtest
apachectl -S
openssl x509 -in /etc/pki/tls/certs/portal.crt -noout -fingerprint -sha256 -dates
ls -lZ /etc/pki/tls/certs /etc/pki/tls/private
getenforce
chronyc tracking
```

### B.6 Live endpoint (any technology)

```text
openssl s_client -connect <host>:443 -servername <name> </dev/null 2>/dev/null | openssl x509 -noout -fingerprint -sha256 -dates -ext subjectAltName
```

Compare the fingerprint with the thumbprint in the CMDB record.

### B.7 Java keystore

```text
keytool -list -v -keystore /opt/api/conf/keystore.p12 -alias api
```

Use a protected way to supply the password. Compare the SHA-256 fingerprint with the CMDB record.

### B.8 ServiceNow (in the interface)

- MID Servers list: status Up and Validated, version matches the instance release.
- Discovery schedules: the daily schedule, its time and last runs.
- The certificate record list in the CMDB: open five records and check the fields (thumbprint, serial, SAN, server, valid from, valid to, last scanned), then export 20 records.
- System plugins: the list of active plugins.

---

## Appendix C: Sample access rules (indicative)

These are starting points to be reviewed by the owning security teams. They are not final.

**Linux deployment user.** Prefer one root-owned wrapper script that the adapter calls, and allow only that script through sudo. If individual commands are used instead, limit them exactly and avoid wildcards that allow arbitrary arguments.

```text
# /etc/sudoers.d/cdm  (indicative, review before use)
cdmdeploy ALL=(root) NOPASSWD: /usr/local/sbin/cdm-deploy-wrapper
```

The wrapper performs only: read the current fingerprint, back up, install the files with the given owner and mode, restorecon, configuration test, graceful reload, and rollback.

**Windows deployment account.** Local rights only on the target servers: manage the Local Machine certificate store, manage IIS bindings, set private key permissions, and remote PowerShell (preferably through a constrained JEA endpoint that exposes only the adapter commands). No domain administrator rights.

**CyberArk.** The CDM application identity has retrieve-only rights on its safes. Each zone has its own safes and its own application identity, allowed only from that zone's MID hosts.

**Sectigo.** A dedicated API account with rights to list certificates, collect certificates and fetch the bundle for the organisations in scope. Renewal rights are added only when CDM triggers renewals in a later phase.
