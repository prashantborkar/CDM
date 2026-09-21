
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

{{TOTALS}}

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
