
---

## 7. Configuration

This chapter answers "how do we configure it". Everything below is set in ServiceNow (scoped application tables and system properties) and can be exported and imported as YAML or JSON. Secrets are never part of the configuration: only CyberArk references are.

### 7.1 Where each kind of configuration lives

| What | Where | Notes |
|---|---|---|
| Global settings, schedules, thresholds | ServiceNow: CDM settings | Section 7.3 |
| Source connections (ServiceNow CMDB, Sectigo) | ServiceNow: CDM source connections | Section 7.5 |
| Credentials | CyberArk | Referenced by safe and object name, never stored in ServiceNow (section 7.6) |
| Zones and MID Servers | ServiceNow: CDM zones | Which MID Servers serve which network zone (section 7.7) |
| Deployment profiles | ServiceNow: CDM deployment profiles | One per server and certificate (section 7.8) |
| Adapters | ServiceNow: CDM adapter registry, source control | Approved, signed, versioned (chapter 9) |
| Matching and renewal rules | ServiceNow: CDM settings | Sections 7.4 and 7.9 |
| Notifications and roles | ServiceNow | Section 7.10 |

### 7.2 Configuration file (reference)

This is the complete logical configuration. The same content is entered in the ServiceNow forms, or imported as a file.

```yaml
cdm:
  environment: poc                    # poc (personal instance) or production
  timezone: UTC                       # all timestamps are stored and compared in UTC

sources:
  servicenow:
    mode: in-instance                 # CDM runs inside the instance, reads the CMDB directly
    certificate_table: cmdb_ci_certificate        # verify the class in your instance (item V2)
    field_map:                        # CDM field: ServiceNow field (verify names, item V2)
      name: name
      thumbprint: thumbprint
      serial: serial_number
      san: subject_alternative_names
      server: server                  # relationship to the server CI
      valid_from: valid_from
      valid_to: valid_to
      last_scanned: last_discovered
    sync:
      after_discovery_hours: 2        # sync 2 hours after the daily scan starts
      schedule: "04:00"               # fallback fixed time (UTC)
      stale_after_hours: 36           # do not decide on CIs scanned longer ago than this
  sectigo:
    base_url: https://cert-manager.com/api        # confirm for your tenant (item V1)
    customer_uri: "<your customerUri>"
    organization: "<organisation or department>"
    credential: {vault: cyberark, safe: CDM-Sectigo, object: sectigo-api-cdm}
    poll: {interval_minutes: 60, overlap_minutes: 120}
    bundle: {format: pkcs12, temp_ttl_minutes: 15, expected_downloads: 1}
    rate_limit: {requests_per_minute: 60}
    environment: sandbox              # sandbox or production

vault:
  type: cyberark
  access: ccp                         # ccp (Central Credential Provider) or servicenow-external-credential-storage
  ccp:
    url: https://ccp.example.com/AIMWebService/api/Accounts
    app_id: CDM
    auth: client-certificate          # the MID Server presents a client certificate
  lease_minutes: 15

zones:
  - name: internal
    mid_servers: [mid-int-01, mid-int-02]
    accounts:
      windows_deploy: {safe: CDM-Internal, object: svc-cdm-win-deploy}
      linux_deploy:   {safe: CDM-Internal, object: svc-cdm-linux-deploy}
  - name: dmz
    mid_servers: [mid-dmz-01]
    accounts:
      windows_deploy: {safe: CDM-Dmz, object: svc-cdm-win-deploy}
      linux_deploy:   {safe: CDM-Dmz, object: svc-cdm-linux-deploy}

matching:
  san_rule: equal                     # equal or approved-superset
  require_unique: true
  timestamp_skew_seconds: 120

renewal:
  window_max_days: 30                 # start when remaining life <= min(30 days, 33 percent of lifetime)
  window_fraction_of_lifetime: 0.33
  window_floor_days: 3
  deploy_on_landing: false            # false: wait for the renewal window; true: deploy as soon as it lands
  alert_days: [30, 14, 7, 3, 1]       # alerts when no replacement has landed

deployment:
  require_profile: true
  require_approval: {production: false, non_production: false}   # start simple, tighten later
  change_window: {production: "22:00-05:00", non_production: any}
  max_parallel_per_zone: 5
  canary_first: true
  stop_on_first_failure: true
  retry: {attempts: 3, backoff_seconds: [30, 120, 600]}

verification:
  live_probe: {tls_min: "1.2", check: [thumbprint, san, chain, dates]}
  confirm_by_discovery: true
  confirm_timeout_hours: 36

retention:
  old_certificate_on_server_days: 30
  audit_online_months: 13

notifications:
  email_groups: {default: cert-owners@example.com, critical: pki-admins@example.com}
  events: [landed, planned, deployed, confirmed, failed, rolled_back, unconfirmed, no_replacement, no_profile, ambiguous]
```

### 7.3 Global settings and defaults

| Setting | Default | Meaning |
|---|---|---|
| ServiceNow sync time | 2 hours after the Discovery scan starts | When stage 1 runs |
| Sectigo poll interval | 60 minutes | How often the landing area is read |
| Sectigo poll overlap | 120 minutes | Re-read window so nothing is missed |
| Stale data limit | 36 hours | CIs scanned longer ago are not used for decisions |
| Renewal window | min(30 days, 33 percent of lifetime), floor 3 days | When a certificate counts as expiring |
| Deploy on landing | Off | Off: wait for the renewal window. On: deploy as soon as the new certificate lands |
| Alert days | 30, 14, 7, 3, 1 | Alerts when no replacement has landed |
| Confirmation timeout | 36 hours | Alert if the next scan has not confirmed |
| Bundle temporary life | 15 minutes | Maximum time key material exists on the MID Server |
| Credential lease | 15 minutes | CyberArk credentials are held no longer than this |
| Maximum parallel jobs per zone | 5 | Concurrency limit |
| Retry attempts and back-off | 3 attempts, 30 s, 2 min, 10 min | Transient errors only |
| Old certificate retention on server | 30 days | Before optional removal |
| Audit retention online | 13 months | Then archive |

### 7.4 Renewal window and timing

A certificate is "Expiring" when its remaining life is at most the smaller of the window maximum (default 30 days) and the window fraction of its lifetime (default 33 percent), and never less than the floor (default 3 days).

| Certificate lifetime | Renewal window | Example |
|---|---|---|
| One month (30 days) | About 10 days | Valid 1 to 30 June: window starts 20 June |
| 90 days | 30 days | |
| One year | 30 days | |
| Longer | 30 days | |

If Sectigo has already issued the replacement (landed) and "deploy on landing" is off, CDM keeps it in the landing queue until the old certificate enters its window. With "deploy on landing" on, CDM deploys as soon as the match is unique and a profile exists.

### 7.5 Source connections and field mapping

**ServiceNow (CMDB, filled by Discovery).** The class and field names below are indicative and must be confirmed in your instance (item V2). You have confirmed that the data exists: thumbprint, serial, SAN, server, certificate name and exact dates. The certificate and private key are not stored.

| CDM field | ServiceNow (indicative) | Sectigo (indicative) | Used for |
|---|---|---|---|
| Certificate name | Certificate CI name or common name | Common name or friendly name | Lineage, display |
| Thumbprint | Thumbprint or fingerprint | From the collected certificate | Exact identity |
| Serial | Serial number | Serial number | Exact identity |
| SAN set | Subject alternative names | Subject alternative names | Lineage, name check |
| Server | Related server CI | Not available | Where to deploy |
| Valid from | Valid from | Not before or issued | Order in time |
| Valid to | Valid to | Not after or expires | Expiry, confirmation |
| Last scanned | Last discovered | Not applicable | Freshness, confirmation |
| Sectigo ID and status | Not available | Certificate ID, order number, status | Fetching the bundle |

**Sectigo.** Base URL, customer URI, organisation, certificate types or profiles in scope, sandbox or production, the CyberArk object for the API account, poll interval, rate limit, bundle format.

### 7.6 CyberArk configuration

CyberArk holds every credential. The MID Server asks for a credential when a job needs it; the credential is held in memory for the job and released.

| CyberArk object (example) | Safe | Used for | Access |
|---|---|---|---|
| sectigo-api-cdm | CDM-Sectigo | Sectigo API login or key | MID Servers of all zones (or the ServiceNow app for list calls) |
| svc-cdm-win-deploy (per zone) | CDM-Internal, CDM-Dmz | Windows deployment account (or gMSA) | MID Servers of that zone only |
| svc-cdm-linux-deploy (per zone) | CDM-Internal, CDM-Dmz | SSH key or signed SSH certificate for the Linux deployment user | MID Servers of that zone only |
| java-keystore-<application> | CDM-Java | Keystore and key password of an application | MID Servers of that zone only |
| ccp application identity | CDM | The MID Server's own identity toward CyberArk (client certificate) | One per zone |

Rules: separate safes per zone; the deployment accounts are different from any account used for Discovery; least privilege on each safe; retrieval is audited by CyberArk; no credential is written to ServiceNow, a script, a flow variable or a file. Two access options: the MID Server calls the Central Credential Provider directly, or ServiceNow's external credential storage for CyberArk is used (to be confirmed for your instance and MID version, item V3).

### 7.7 Zones and MID Servers

A zone is a network segment served by its own MID Server or MID pair. A server belongs to one zone (from the CMDB or from its profile). A job only runs on a MID Server of the server's zone. MID Servers only connect outbound to ServiceNow. On the personal instance one MID Server on the laptop plays every zone.

### 7.8 Deployment profiles

A deployment profile is the configuration for deploying on one server. Discovery only gives the server and the certificate name, so the technology-specific details (IIS site, Apache paths, Java keystore) come from the profile. No profile means no automatic deployment (a manual task is raised).

| Field | Meaning |
|---|---|
| profile id, version, status | Versioned and approved |
| certificate identity | Certificate name and SAN set this profile is for |
| server and zone | From the CMDB |
| technology and adapter and version | For example windows-iis 1.0.0 |
| credential references | CyberArk safe and object names |
| technology settings | Site, paths, alias, ownership (examples below) |
| activation | Binding update, graceful reload, JMX reload or restart |
| verification | Port, SNI name, checks |
| window and owner | Change window, notification group |

**Example: Windows IIS**

```yaml
profile: PRF-0001
version: 1
status: approved
server: web01.example.com
zone: internal
certificate: {name: app.example.com, san: [app.example.com, www.example.com]}
adapter: {id: windows-iis, version: 1.0.0}
credentials: {deploy: {safe: CDM-Internal, object: svc-cdm-win-deploy}}
windows:
  store: LocalMachine/My
  key_exportable: false
  key_permission:
    read: ["IIS APPPOOL\\AppPool1"]      # only this identity, plus SYSTEM and Administrators
  bindings:
    - {site: "Default Web Site", ip: "*", port: 443, host_header: app.example.com, sni: true}
    - {site: "Default Web Site", ip: "*", port: 443, host_header: www.example.com, sni: true}
activation: {method: binding-update}      # no restart
verification: {host: app.example.com, port: 443, sni: app.example.com}
window: production-standard
owner_group: web-platform
```

**Example: Linux Apache**

```yaml
profile: PRF-0002
version: 1
status: approved
server: lnx01.example.com
zone: dmz
certificate: {name: portal.example.com, san: [portal.example.com]}
adapter: {id: linux-apache, version: 1.0.0}
credentials: {deploy: {safe: CDM-Dmz, object: svc-cdm-linux-deploy}}
linux:
  cert_dir: /etc/pki/tls/certs
  key_dir: /etc/pki/tls/private
  link_names: {cert: portal.crt, chain: portal-chain.crt, key: portal.key}   # Apache config points to these links
  owner: {cert: "root:root 0644", chain: "root:root 0644", key: "root:root 0600"}
  selinux_restorecon: true
activation: {method: graceful-reload, pre_test: "apachectl configtest", command: "apachectl graceful"}
verification: {host: portal.example.com, port: 443, sni: portal.example.com}
window: production-standard
owner_group: web-platform
```

**Example: Java keystore**

```yaml
profile: PRF-0003
version: 1
status: approved
server: app01.example.com
zone: internal
certificate: {name: api.example.com, san: [api.example.com]}
adapter: {id: java-keystore, version: 1.0.0}
credentials:
  deploy: {safe: CDM-Internal, object: svc-cdm-linux-deploy}
  keystore: {safe: CDM-Java, object: java-keystore-api}
java:
  keystore_path: /opt/api/conf/keystore.p12
  keystore_type: PKCS12
  alias: api
  alias_strategy: replace                   # replace or new-alias
  owner: "app:app 0640"
activation: {method: service-restart, service: api, window_required: true}   # or tomcat-jmx-reload
verification: {host: api.example.com, port: 8443, sni: api.example.com}
window: production-standard
owner_group: java-platform
```

### 7.9 Matching configuration

| Setting | Default | Meaning |
|---|---|---|
| SAN rule | equal | The replacement must have the same SAN set. Option: approved superset |
| Require unique | true | Ambiguous matches never deploy |
| Timestamp skew | 120 seconds | Tolerance when comparing dates |
| Name key | common name and SAN set | Lineage between old and new |

### 7.10 Notifications and roles

| Role | Can do |
|---|---|
| cdm_admin | Configure settings, sources, zones, adapters, profiles |
| cdm_owner | See own certificates, complete manual tasks, receive notifications |
| cdm_operator | Monitor jobs, retry, roll back |
| cdm_approver | Approve profiles and, where enabled, deployments (cannot approve own) |
| cdm_auditor | Read only: inventory, audit trail, reports |
| cdm_integration | Service role used by CDM integrations, minimal rights |

Notifications go to the owner group of the server or profile for: replacement landed, planned, deployed, confirmed, failed, rolled back, unconfirmed after the timeout, no replacement by the alert days, no profile, ambiguous match.

### 7.11 Personal instance now, licensed instance later

| Item | Personal instance (proof of concept) | Licensed instance (production) |
|---|---|---|
| ServiceNow | Personal developer instance | Full licence, separate dev, test and production instances |
| Discovery | Real scan of the lab server if possible, otherwise a clearly labelled scan simulator that updates the certificate CI daily | Real daily Discovery |
| Sectigo | Sandbox if available, otherwise a test CA that behaves like the landing area and delivers a real bundle | Production tenant |
| CyberArk | A lab or developer safe if available; otherwise a temporary stand-in that must not be carried to production | The production CyberArk with the safes in 7.6 |
| MID Server | One MID Server on the laptop | MID Servers per zone with a pair for high availability |
| Targets | Local IIS, a Linux VM or WSL with Apache, a small Java app | The real servers |
| Move | Package as a scoped application and move with the same configuration file | |

---

## 8. Functional requirements

### 8.1 Synchronisation (SYN)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-SYN-001 | Read the certificate CIs from the ServiceNow CMDB every day: name, thumbprint, serial, SAN, server, valid from, valid to, last scanned. Incremental. | M | P1 | PS, ANS |
| FR-SYN-002 | Read new and renewed certificates from the Sectigo landing area by API: list what is available since the last poll and keep the metadata (Sectigo ID, name, SAN, serial, validity, status). | M | P1 | PS, ANS |
| FR-SYN-003 | Obtain the exact thumbprint of each Sectigo certificate by collecting the public certificate only. The private key is not fetched at this stage. | M | P1 | PS |
| FR-SYN-004 | Run the ServiceNow sync at a configurable time after the daily scan, the Sectigo poll at a configurable interval (default hourly), and both on demand. | M | P1 | ANS |
| FR-SYN-005 | Stale-data guard: do not decide on a CI whose last scan is older than the configured limit (default 36 hours). Alert instead. | M | P1 | ANS |
| FR-SYN-006 | Store and compare all timestamps in UTC. | M | P1 | PS |
| FR-SYN-007 | Syncs are idempotent and safe to rerun, with an overlap window so no certificate is missed. | M | P1 | NEW |
| FR-SYN-008 | Respect Sectigo rate limits; retry with back-off; alert after repeated failures. | M | P1 | NEW |
| FR-SYN-009 | Store only identity metadata. Never store a certificate private key or bundle. | M | P1 | ANS |
| FR-SYN-010 | Show the last successful sync per source and alert when it is late. | S | P2 | NEW |
| FR-SYN-011 | Weekly full reconciliation of both sources. | S | P2 | NEW |

### 8.2 Matching (MAT)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-MAT-001 | Match by certificate identity using rules M1 to M8 (chapter 5). | M | P1 | PS |
| FR-MAT-002 | Deploy automatically only when the match is unique. Ambiguous matches go to a review queue. | M | P1 | PS |
| FR-MAT-003 | Record for every match the rule, the evidence and the result. | M | P1 | NEW |
| FR-MAT-004 | Support one certificate on several servers: one binding per server, tracked separately. | M | P1 | PS |
| FR-MAT-005 | Report certificates unknown to Sectigo and certificates at Sectigo that have no server. | M | P1 | PS |
| FR-MAT-006 | Re-check thumbprint and SAN after the bundle is fetched. Any difference from the plan stops the job before any change. | M | P1 | PS |
| FR-MAT-007 | Review queue for ambiguous, unlocated and unknown certificates, with audited decisions. | M | P1 | NEW |
| FR-MAT-008 | Optionally use the Sectigo renewal lineage when the API provides it. | S | P2 | NEW |

### 8.3 Planning (PLN)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-PLN-001 | Apply the adaptive renewal window (section 7.4). | M | P1 | PS |
| FR-PLN-002 | Provide the "deploy on landing" option. | M | P1 | PS |
| FR-PLN-003 | Deploy automatically only when an approved deployment profile exists for the server and certificate. Otherwise create a manual task. | M | P1 | PS |
| FR-PLN-004 | Check the replacement against policy: key size and algorithm, validity, names. | M | P1 | NEW |
| FR-PLN-005 | Alert at the configured days when an expiring certificate has no replacement at Sectigo. | M | P1 | PS |
| FR-PLN-006 | Create one job per binding; for several servers deploy a canary first and stop on the first failure. | M | P1 | PS |
| FR-PLN-007 | Dry run: run the pre-checks and report what would change, without changing anything. | M | P1 | NEW |
| FR-PLN-008 | Concurrency limit per zone and a lock per server so jobs never overlap. | M | P1 | NEW |
| FR-PLN-009 | Optional approval by policy and optional change-window scheduling. | S | P2 | NEW |
| FR-PLN-010 | Let CDM request the renewal at Sectigo through the API when none has landed. | S | P3 | PS |

### 8.4 Certificate and key bundle (KEY)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-KEY-001 | Fetch the certificate and private key bundle from Sectigo by API, only at deployment time. | M | P1 | ANS |
| FR-KEY-002 | The MID Server fetches the bundle directly from Sectigo. It never passes through ServiceNow. | M | P1 | ANS |
| FR-KEY-003 | The private key is never stored in ServiceNow tables, logs, job payloads, flow variables or ECC messages. | M | P1 | ANS |
| FR-KEY-004 | The bundle is held in memory or in encrypted temporary storage for at most the configured time (default 15 minutes) and deleted at the end of the job, success or failure. Deletion is confirmed and audited. | M | P1 | ANS |
| FR-KEY-005 | Validate the bundle: thumbprint equals the plan, the key matches the certificate, SAN and chain are correct, dates are as expected. Reject otherwise. | M | P1 | PS |
| FR-KEY-006 | Record each bundle download and alert on an unexpected repeat. | M | P1 | NEW |
| FR-KEY-007 | Import the key as non-exportable wherever the platform allows. | M | P1 | NEW |
| FR-KEY-008 | Send the bundle to the server only through the adapter's encrypted channel, and delete the temporary copy on the server. | M | P1 | NEW |
| FR-KEY-009 | Generate any bundle passphrase per job in memory (or take it from CyberArk). Never persist it. | M | P1 | NEW |
| FR-KEY-010 | Fallback design: key created on the server (chapter 6.2), if Sectigo cannot deliver the key by API. | S | P2 | ANS |

### 8.5 Deployment execution (DEP)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-DEP-001 | A job carries references only: binding, Sectigo ID, expected thumbprint, profile version, adapter version, CyberArk object names. No secrets, keys or certificate content. | M | P1 | PS |
| FR-DEP-002 | Dispatch the job to a MID Server of the server's zone, with failover inside the zone. | M | P1 | PS |
| FR-DEP-003 | Obtain every credential from CyberArk at job time, short-lived, in memory only. | M | P1 | ANS |
| FR-DEP-004 | Pre-check: reachable, permissions, disk space, service running, and the server currently presents the old thumbprint. Stop on drift. | M | P1 | PS |
| FR-DEP-005 | Back up the old certificate and the binding or configuration as the rollback point before any change. | M | P1 | NEW |
| FR-DEP-006 | Install through the signed adapter for the technology (chapter 9). | M | P1 | PS |
| FR-DEP-007 | Activate without restarting where the technology allows: IIS binding update, Apache graceful reload, Java hot reload. Restart only if the profile says so and inside a window. | M | P1 | PS |
| FR-DEP-008 | Roll back automatically on failure and verify the rollback. | M | P1 | NEW |
| FR-DEP-009 | Clean up and confirm: temporary files, memory, sessions. | M | P1 | ANS |
| FR-DEP-010 | Jobs are idempotent and resumable, with timeouts and retries with back-off for transient errors. | M | P1 | NEW |
| FR-DEP-011 | Cluster and high-availability support: node by node, remove from rotation, validate each node and the VIP. | S | P2 | NEW |
| FR-DEP-012 | Only registered, signed, approved adapters may run. Free-text scripts are refused. | M | P1 | NEW |

### 8.6 Verification and closed loop (VER)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-VER-001 | Verify the live endpoint right after activation: presented thumbprint equals the new one, SAN, chain, dates, from a MID Server in the zone. | M | P1 | PS |
| FR-VER-002 | After a good live check set the state "Deployed, awaiting scan". | M | P1 | PS |
| FR-VER-003 | After the next scan and sync, confirm when the CI on that server shows the new thumbprint, the expected valid-to and a last-scanned time later than the deployment. Then set "Confirmed by discovery". | M | P1 | PS |
| FR-VER-004 | If the scan still shows the old thumbprint after the deployment, alert and do not close. | M | P1 | PS |
| FR-VER-005 | If not confirmed within the timeout (default 36 hours), alert, re-probe the live endpoint and escalate. | M | P1 | ANS |
| FR-VER-006 | Link the old certificate CI to the new one ("replaced by") and record the replacement in the audit trail. | M | P1 | PS |
| FR-VER-007 | Use the live probe result to tell a failed deployment from a scan that has not run yet. | M | P1 | NEW |
| FR-VER-008 | Request an on-demand rescan of one server after deployment where ServiceNow allows it. | S | P2 | NEW |
| FR-VER-009 | Optionally remove the old certificate from the server after the retention period. | S | P2 | NEW |

### 8.7 Exceptions, manual work and notifications (EXC)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-EXC-001 | When there is no profile, or automation is not allowed, create a manual task for the owner with instructions and the certificate identity. CDM never sends a key. The operator gets the bundle from Sectigo with their own access. | M | P1 | PS |
| FR-EXC-002 | Manual tasks have due times and escalation. Completion triggers the live check and the same confirmation by scan. | M | P1 | PS |
| FR-EXC-003 | Create an incident for a failed deployment, a rollback, a failed rollback and an unconfirmed deployment. | M | P1 | NEW |
| FR-EXC-004 | Notify the owner group on the events in 7.10 by email. Teams or Slack is a Should. | M | P1 | NEW |
| FR-EXC-005 | Notification text never contains secrets, keys or certificate content. | M | P1 | NEW |
| FR-EXC-006 | If CyberArk is unavailable, wait and retry with an alert. Never fall back to a stored password. | M | P1 | ANS |

### 8.8 Configuration (CFG)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-CFG-001 | Every setting in chapter 7 is configurable in ServiceNow without code changes. | M | P1 | NEW |
| FR-CFG-002 | Export and import the full configuration as YAML or JSON. | M | P1 | NEW |
| FR-CFG-003 | Validate on save: connection tests to ServiceNow, Sectigo and CyberArk, and a dry run of each profile. | M | P1 | NEW |
| FR-CFG-004 | Version and audit every configuration change. | M | P1 | NEW |
| FR-CFG-005 | Configuration holds only CyberArk references, never secrets. | M | P1 | ANS |
| FR-CFG-006 | Provide profile templates for IIS, Apache, nginx and Java. | M | P1 | PS |
| FR-CFG-007 | Promote configuration from the personal instance to the licensed instances. | S | P2 | ANS |

### 8.9 Adapter framework (ADP)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-ADP-001 | One adapter contract with the operations precheck, backup, install, activate, verify, rollback, cleanup and discover (Appendix A). | M | P1 | PS |
| FR-ADP-002 | Adapter inputs are typed parameters. Certificate content and key are never concatenated into script text. | M | P1 | NEW |
| FR-ADP-003 | An adapter registry holds name, version, signature and approval status. The MID Server runs only approved, signed versions. | M | P1 | NEW |
| FR-ADP-004 | Adapters are version controlled, reviewed, tested, signed and promoted from test to production. | M | P1 | NEW |
| FR-ADP-005 | Deliver Windows IIS, Linux Apache and nginx, and Java in P1; OpenShift or Kubernetes and others later. | M | P1 | PS |
| FR-ADP-006 | Provide an adapter template so a new technology can be added without changing the core. | S | P2 | PS |
| FR-ADP-007 | Map adapter errors to a catalogue of codes with remediation hints. | M | P1 | NEW |

### 8.10 Security (SEC)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-SEC-001 | CyberArk holds every credential: Sectigo API, deployment accounts, SSH keys, keystore passwords. | M | P1 | ANS |
| FR-SEC-002 | Separate accounts per zone and separate from any discovery account. | M | P1 | NEW |
| FR-SEC-003 | The MID Server connects outbound only and accepts no inbound connections. | M | P1 | NEW |
| FR-SEC-004 | TLS 1.2 or higher on every link; mutual TLS to CyberArk; WinRM over HTTPS or Kerberos; SSH with keys or certificates. | M | P1 | NEW |
| FR-SEC-005 | Role-based access with segregation of duties (7.10); a requester or owner cannot approve their own change. | M | P1 | NEW |
| FR-SEC-006 | No secret, key or certificate content in any log. | M | P1 | NEW |
| FR-SEC-007 | Four-eyes approval of adapters and profiles. | S | P2 | NEW |

### 8.11 Audit and reporting (AUD)

| ID | Requirement | Pri | Phase | Src |
|---|---|---|---|---|
| FR-AUD-001 | Audit every action: who, what, when, server, adapter and version, job, result, thumbprints before and after. Tamper-evident. | M | P1 | NEW |
| FR-AUD-002 | Dashboard: expiring, replacement landed, planned, deployed awaiting scan, confirmed, failed, no profile, ambiguous, unknown to Sectigo, unlocated. | M | P1 | NEW |
| FR-AUD-003 | Audit retention configurable (default 13 months online, then archive). | M | P1 | NEW |
| FR-AUD-004 | Reports and SIEM export; deploy-to-confirm time and coverage KPIs. | S | P2 | NEW |

---

## 9. Technology adapters

Each adapter follows the same contract (Appendix A). Commands are indicative and are fixed during adapter design. Each installs the certificate and key from the Sectigo bundle, then activates and verifies.

### 9.1 Windows IIS (adapter WIN, P1)

| ID | Aspect | Specification |
|---|---|---|
| AD-WIN-01 | Scope | Windows Server 2016 and later, IIS 8.5 and later. Certificate store (Local Machine, Personal), private key permission, IIS HTTPS bindings. |
| AD-WIN-02 | Transport | WinRM over HTTPS (5986) with a certificate, or Kerberos in a domain. HTTP, Basic and unencrypted traffic are not allowed. A constrained endpoint (JEA) that exposes only the needed commands is preferred. |
| AD-WIN-03 | Account | The zone deployment account from CyberArk. Never a domain administrator. |
| AD-WIN-04 | Pre-check | Read the current HTTPS bindings (`Get-WebBinding -Protocol https`) and the certificate hash of each. It must equal the old thumbprint from the CMDB. IIS running, disk space, account rights. |
| AD-WIN-05 | Backup | Record every binding of the old certificate (site, IP, port, host header, SNI flag, hash, store). The old certificate stays in the store. |
| AD-WIN-06 | Import | Import the PKCS#12 into `Cert:\LocalMachine\My` (`Import-PfxCertificate`, passphrase as a secure string, key non-exportable). Import intermediates into the intermediate store. The temporary file is deleted. |
| AD-WIN-07 | Private key permission | Give Read on the private key only to the identity that needs it (the IIS application pool identity or the service account). Remove other principals except SYSTEM and Administrators. Record the resulting permission in the result. |
| AD-WIN-08 | HTTPS binding | For each binding in the profile set the new certificate (`AddSslCertificate` with the new thumbprint and store name), keeping SNI and host headers. |
| AD-WIN-09 | Activate | The binding update applies to new connections. No IIS restart. |
| AD-WIN-10 | Verify | TLS handshake with SNI to the site from the zone MID Server. Check thumbprint, SAN, chain, dates. |
| AD-WIN-11 | Rollback | Re-bind every binding to the old thumbprint, verify, then remove the new certificate and key from the store. |
| AD-WIN-12 | Discover | List the certificates in the store with thumbprint, SAN, dates, has-private-key, bindings (used for the pre-check and drift). |
| AD-WIN-13 | More bindings later | RDP listener, WinRM listener, SQL Server and other services through the profile in P2. |
| AD-WIN-14 | Retention | After the retention period (default 30 days) optionally remove the old certificate from the store. |

### 9.2 Linux Apache and nginx (adapter LNX, P1)

| ID | Aspect | Specification |
|---|---|---|
| AD-LNX-01 | Scope | RHEL family, Ubuntu and Debian, SUSE; Apache 2.4 (httpd or apache2) and nginx. |
| AD-LNX-02 | Transport | SSH from the zone MID Server with a key or signed certificate from CyberArk. No password login. Host key pinned. |
| AD-LNX-03 | Privilege | A dedicated deployment user. sudo limited to the named commands (install, restorecon, configtest, reload). |
| AD-LNX-04 | Pre-check | Compute the fingerprint of the certificate file the server uses (`openssl x509 -fingerprint -sha256`). It must equal the old thumbprint. `apachectl configtest` passes today. Disk space. SELinux mode noted. |
| AD-LNX-05 | Backup | Copy the current certificate, chain, key and virtual-host configuration to a root-only backup directory named by job ID. |
| AD-LNX-06 | Write files | Write the new certificate, chain and key to new versioned files in the profile directories, first as temporary files and then by atomic rename. |
| AD-LNX-07 | Owner and permission | Certificate and chain: `root:root 0644`. Private key: `root:root 0600` (Apache reads keys as root when it starts or reloads), or `root:<service group> 0640` if the profile says so. |
| AD-LNX-08 | Switch | Point the stable link names used by the Apache configuration (for example `portal.crt`) to the new files. The Apache configuration does not change. |
| AD-LNX-09 | SELinux and AppArmor | Run `restorecon` on the new files and check the context; confirm the AppArmor profile allows the paths. |
| AD-LNX-10 | Configuration reload, not restart | Test with `apachectl configtest` (nginx: `nginx -t`), then reload gracefully: `apachectl graceful` or `systemctl reload httpd` or `apache2` (nginx: `systemctl reload nginx`). A restart only if the profile says so, inside a window. |
| AD-LNX-11 | Verify | `openssl s_client -connect host:port -servername name` from the zone MID Server. Check fingerprint, SAN, chain, dates. |
| AD-LNX-12 | Rollback | Switch the links back to the old files, reload, verify. |
| AD-LNX-13 | Shared certificate | One certificate used by several virtual hosts: all are covered by one switch and one reload. |
| AD-LNX-14 | Discover | Read the configured certificate paths and fingerprints (pre-check and drift). |

### 9.3 Java applications (adapter JVA, P1)

| ID | Aspect | Specification |
|---|---|---|
| AD-JVA-01 | Scope | JKS and PKCS#12 keystores for Tomcat, JBoss or WildFly, Spring Boot and similar. Java 8 and later. |
| AD-JVA-02 | Access | Through SSH or WinRM to the host. Keystore path, type and alias come from the profile. |
| AD-JVA-03 | Passwords | The keystore and key passwords come from CyberArk. They are passed by a protected file or environment variable, never on a visible command line, and wiped afterwards. |
| AD-JVA-04 | Pre-check | `keytool -list -v` for the alias must show the old fingerprint. The keystore is writable. The service state is known. |
| AD-JVA-05 | Backup | Copy the keystore with a checksum, keeping owner and permission. |
| AD-JVA-06 | Import | `keytool -importkeystore` from the Sectigo PKCS#12 into the application keystore (destination type JKS or PKCS#12). The profile chooses `replace` (remove the old alias after backup and import under the same alias) or `new-alias` (import under a new alias and switch the application configuration). |
| AD-JVA-07 | Owner and permission | Keep the keystore owner and mode as before (default `app:app 0640`). |
| AD-JVA-08 | Activate | Hot reload where the server supports it (for example Tomcat 9 and later reloading its SSL configuration over JMX). Otherwise a controlled service restart in a change window. |
| AD-JVA-09 | Verify | TLS probe of the application port; `keytool -list` shows the new fingerprint. |
| AD-JVA-10 | Rollback | Restore the keystore backup, reload or restart, verify. |
| AD-JVA-11 | Truststore | Not changed by CDM unless a private CA change is approved. |

### 9.4 Later technologies (not in the first release)

| Technology | Approach when added |
|---|---|
| OpenShift and Kubernetes | Update the TLS Secret (or route certificate) through the API with a service account and role binding limited to the needed namespaces and verbs; rollout restart where needed; verify at the route or ingress |
| F5 and NetScaler | Vendor REST API from the zone MID Server; import as a new versioned object, update the SSL profile, synchronise the pair |
| Databases and middleware | Through the Windows or Linux adapter plus the engine's reload or restart, inside a change window |
| Network devices | Vendor CLI over SSH or enrolment protocol |
