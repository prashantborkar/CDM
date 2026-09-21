# Certificate Deployment Manager (CDM): End-to-End Specification

| Item | Detail |
|---|---|
| Version | 1.0 (draft for review). Replaces all earlier versions. |
| Date | 2026-09-21 |
| Basis | Your problem statement and your answers to the open questions. Nothing else is assumed. |
| Format | One Markdown file, no images. Flows are drawn as text so they render anywhere. |

> Written for: you and the team who will build CDM. It describes exactly how the tool works from the first scan to the confirmed deployment, and how to configure it.

**Conventions.** Requirement IDs: `FR-<area>-<nnn>` functional, `AD-<technology>-<nn>` adapter, `NFR-<area>-<nn>` non-functional. **Pri:** M = Must, S = Should, C = Could. **Phase:** P1 = first release, P2 = next, P3 = later (P0 = proof of concept on the ServiceNow personal instance). **Src:** PS = your problem statement, ANS = your answers.

## Contents

- [0. Summary](#0-summary)
- [1. Problem statement](#1-problem-statement)
- [2. Confirmed inputs and design decisions](#2-confirmed-inputs-and-design-decisions)
- [3. Scope](#3-scope)
- [4. End-to-end flow](#4-end-to-end-flow)
- [5. Certificate matching](#5-certificate-matching)
- [6. Private key and certificate bundle handling](#6-private-key-and-certificate-bundle-handling)
- [7. Configuration](#7-configuration)
- [8. Functional requirements](#8-functional-requirements)
- [9. Technology adapters](#9-technology-adapters)
- [10. Security and CyberArk](#10-security-and-cyberark)
- [11. Data model and states](#11-data-model-and-states)
- [12. Interfaces](#12-interfaces)
- [13. Non-functional requirements](#13-non-functional-requirements)
- [14. Building it: proof of concept on the personal instance](#14-building-it-proof-of-concept-on-the-personal-instance)
- [15. Test and acceptance](#15-test-and-acceptance)
- [16. Roadmap](#16-roadmap)
- [17. Risks](#17-risks)
- [18. Items to verify](#18-items-to-verify)
- [Appendices](#appendix-a-adapter-contract)

---

## 0. Summary

**Problem.** Certificates on many servers and technologies must be renewed before they expire (validity from one month to a year or more). Sectigo, the issuing CA, can issue the renewed certificate early and keep it available in a landing area that is read by an API. It does not know where the old certificate is installed. ServiceNow Discovery scans every day and knows, for each certificate, its name, thumbprint, serial, SAN, server and exact dates, but it cannot issue or deploy a certificate. Today the delivery is manual.

**Solution.** CDM connects the two. Every day it:

1. reads the certificates that Discovery found (ServiceNow),
2. reads the new certificates that are available at Sectigo (API),
3. matches them by certificate identity so it knows which new certificate replaces which old one, and on which server,
4. fetches the new certificate together with its private key, which Sectigo creates and delivers by API,
5. deploys it on the server with the method for that technology (Windows IIS, Linux Apache, Java), with credentials from CyberArk and through the MID Server that already has access,
6. checks the live endpoint right away,
7. and the next day, when Discovery scans again and finds the new certificate with the new dates and thumbprint, CDM confirms that the deployment worked.

```text
 ServiceNow (personal instance now, full licence later)         Sectigo (issuing CA)
 Discovery scans every day  -> certificate CIs                  new / renewed certificates available
 (name, thumbprint, serial, SAN, server, dates)                 (landing area, read by API)
              |                                                            |
              +---------------->     CDM      <-----------------------------+
                        1 sync  2 sync  3 match  4 plan
                                      |   job (no secrets)
                                      v
                          MID Server in the target's zone
                 5 credentials from CyberArk, just in time
                 6 pre-check and backup
                 7 fetch certificate + private key from Sectigo (API)
                 8 install for the technology (IIS / Apache / Java)
                 9 activate (bind or graceful reload)   10 verify the live endpoint
                 11 wipe all temporary material
                                      |
                                      v
   Next day: Discovery scans again -> CMDB shows new thumbprint + dates -> 12 CDM confirms and closes
```

**In scope for the first release:** Windows IIS, Linux Apache (and nginx), Java. **Later:** OpenShift or Kubernetes and other technologies. **Not needed:** IWS, Rundeck, Apple, cloud services. **Selling** is parked until the product works.

**Size of this specification.** 91 functional requirements (P1: 78, P2: 12, P3: 1; Must 78, Should 13, Could 0), 39 adapter requirements, 16 non-functional requirements, 20 acceptance tests, 10 items to verify.

---

## 1. Problem statement

1. There are many applications on different servers and technologies.
2. Every certificate has a validity: some one month, some one year. Before it ends it must be renewed and the new certificate must be installed where the old one was. Both sides, the issuer and the receiver, have authority: the CA decides what is issued, and the server decides what it presents.
3. The issuing CA (Sectigo) can issue the certificate before it expires. The new certificate is available in a landing area and is read with an API call. Sectigo knows what it issued but not where it is used.
4. ServiceNow Discovery scans the infrastructure every day. It knows each certificate's name, thumbprint, serial, SAN, server and exact dates. Discovery does not store the certificate itself or its private key. It is a scanning tool and cannot issue or deploy.
5. So the location is in ServiceNow (CMDB) and the issued certificate is in Sectigo. One month before expiry, someone joins the two by hand and deploys the certificate.
6. The tool has to access both ServiceNow and Sectigo. A certificate has an identity (fingerprint or thumbprint, serial, SAN, exact timestamps, name). That information exists in both systems. The tool picks the information from ServiceNow, treats the certificate as unique by that identity, picks the replacement from Sectigo, goes to the server through the MID Server (which has access downstream) and deploys the certificate one more time.
7. The next day the ServiceNow Discovery scan runs. If it finds the new certificate with the new dates, the deployment is proven, and the tool records that.
8. There are several technologies and each has its own method: Windows IIS (certificate store, private key permission, HTTPS binding), Linux Apache (private key, owner and file permission, configuration reload and not a server restart), Java applications (keystore).
9. There are several ways to get a certificate (API, network agent, others). The best way is the API, so the tool follows the API.

---

## 2. Confirmed inputs and design decisions

| # | Topic | Your answer | Design consequence |
|---|---|---|---|
| 1 | How Sectigo delivers a certificate | New certificates are available in a landing area, read by an API call | CDM polls the Sectigo API for new certificates (FR-SYN-002) |
| 2 | Private key | Sectigo creates the private key together with the certificate, and this can be done by API (to be verified with Sectigo, item V1) | CDM fetches a certificate and key bundle by API at deployment time (chapter 6) |
| 3 | Renewal today | Manual | CDM removes the manual pickup and deployment. Triggering the renewal at Sectigo stays with Sectigo (auto or manual) in the first release |
| 4 | Discovery data | Thumbprint, serial, SAN, server, certificate name and exact dates. Not the certificate or the private key | Matching uses these fields (chapter 5). The certificate and key can only come from Sectigo |
| 5 | Scan frequency | Every day | The loop is daily: deploy on day 0, confirm on day 1 (section 4.3) |
| 6 | ServiceNow | Personal instance for now, full licence later | Build and prove on the personal instance, then move the same scoped application to the licensed instance (chapter 14) |
| 7 | Vault | CyberArk | Every credential comes from CyberArk, just in time (chapter 10) |
| 8 | IWS and Rundeck | Not used, only an example | Not in the design. The MID Server is the only executor |
| 9 | Apple and cloud services | Not needed now | Out of scope |
| 10 | Pickup method | API preferred | API is the only pickup method in the design |
| 11 | Selling | Later | Not part of this specification |
| 12 | Technologies | Windows IIS, Linux Apache, Java, more later | Adapters for these three first (chapter 9) |

---

## 3. Scope

**In scope**

- Daily read of the certificate CIs that Discovery stores in the ServiceNow CMDB.
- Read of new and renewed certificates from the Sectigo landing area by API.
- Matching by certificate identity, with a uniqueness guarantee.
- Fetching the certificate and private key that Sectigo creates, by API.
- Deployment through the MID Server with technology adapters for Windows IIS, Linux Apache (and nginx) and Java.
- Pre-check, backup, rollback, immediate live verification.
- Confirmation by the next daily Discovery scan.
- CyberArk for every credential; no permanent private key on the MID Server; no key stored in ServiceNow.
- Alerts, manual fallback, audit, dashboards.
- Configuration of all of the above (chapter 7).

**Later (not in the first release)**

- Triggering the renewal at Sectigo from CDM.
- OpenShift or Kubernetes (service account and role binding), load balancers, databases, network devices.
- Approvals and change-window integration beyond the basics.

**Not needed**

- IWS and Rundeck. Apple. Cloud services. Selling and packaging.
- Replacing ServiceNow Discovery or acting as a CA.

**Definitions**

| Term | Meaning |
|---|---|
| Landing area | The place at Sectigo where new or renewed certificates are available, read with an API call |
| Certificate CI | The ServiceNow CMDB record that Discovery creates for a certificate found on a server |
| Identity | Thumbprint, serial, SAN set, certificate name, exact validity timestamps |
| Binding | One certificate on one server in one place (for example an IIS site, an Apache virtual host, a Java keystore) |
| Deployment profile | The configuration that says how to deploy on one server (chapter 7) |
| Bundle | The certificate, its chain and its private key delivered together by Sectigo (PKCS#12) |
| MID Server | ServiceNow agent inside the network with access to the servers; connects outbound only |
| Closed loop | Deploy, verify now, then confirm by the next Discovery scan |
| CyberArk | The vault that holds every credential |

---

## 4. End-to-end flow

### 4.1 Overview

```text
 DAY 0
  [1] Sync ServiceNow    read certificate CIs from the CMDB after the daily scan
  [2] Sync Sectigo       read new certificates from the landing area (API)
  [3] Match              old certificate on a server  <->  new certificate at Sectigo (by identity)
  [4] Plan               deployment profile exists? within renewal window? policy, change window ok?
  [5] Dispatch           job (no secrets) to the MID Server in the server's zone
  [6] Prepare            CyberArk gives the credentials just in time; pre-check; backup
  [7] Fetch              MID Server fetches certificate + private key from Sectigo (API)
  [8] Install            per technology: IIS / Apache / Java
  [9] Activate           IIS binding, or Apache graceful reload, or Java reload
 [10] Verify now         the live endpoint presents the new thumbprint, SAN, chain, dates
 [11] Clean up           wipe temporary files and memory, close sessions
      state: "Deployed, awaiting scan"

 DAY 1
 [12] Discovery scans again; CDM syncs; the CMDB shows the new thumbprint and dates on that server
      -> "Confirmed by discovery"; the request is closed; the old certificate is marked replaced
```

### 4.2 Stage by stage

**Stage 1. Sync ServiceNow**

| Item | Detail |
|---|---|
| Trigger | Daily, a configurable time after the Discovery scan window has finished (default: 2 hours after the scan starts), and on demand |
| Input | Certificate CIs in the CMDB: name, thumbprint, serial, SAN, server, valid from, valid to, last scanned |
| Actions | Read new or changed CIs since the last sync. Upsert into the CDM certificate and binding records. Compute days to expiry and the renewal window (section 7.4). Mark certificates that entered the window as "Expiring" |
| Output | Up-to-date certificate and binding records |
| Failure | ServiceNow unreachable or stale data (last scanned older than 36 hours): alert, do not decide on stale data |

**Stage 2. Sync Sectigo (landing area)**

| Item | Detail |
|---|---|
| Trigger | On a schedule (default hourly) and after Stage 1 |
| Input | Sectigo API: certificates that are issued and available |
| Actions | List certificates issued since the last poll. For each new one, keep the metadata (Sectigo ID, name, SAN, serial, thumbprint, validity, status). The public certificate is collected to get an exact thumbprint if the list does not carry one. The private key is not fetched here |
| Output | The landing queue: certificates available at Sectigo that CDM has not yet deployed |
| Failure | API error or rate limit: retry with back-off, alert after a configurable number of failures |

**Stage 3. Match**

For every certificate that Discovery found and that is in the renewal window, find the replacement in the landing queue by identity (chapter 5). Results: matched and unique, ambiguous, no replacement yet, unknown to Sectigo, unlocated.

**Stage 4. Plan**

| Check | Rule | If it fails |
|---|---|---|
| Unique match | Exactly one replacement | Ambiguous: review queue, no deployment |
| Deployment profile | An approved profile exists for this server and certificate | Status "No profile": manual task to the owner |
| Timing | The old certificate is inside its renewal window, or deploy-on-landing is switched on | Wait, re-check the next day |
| Policy | Key size, algorithm, validity, names within policy | Rejected with reason |
| Approval and window | Approval (if the policy requires it) and the change window | Wait for approval or window |
| Multi-server | The same certificate is on several servers | One job per server, canary first, stop on first failure |

Output: one deployment job per binding.

**Stage 5. Dispatch**

The job carries only references and identifiers: the binding, the Sectigo certificate ID, the expected new thumbprint, the deployment profile version, the adapter and its version, the CyberArk object names. It carries no secret, no key and no certificate content. It goes through the ECC queue to a MID Server that belongs to the server's zone.

**Stage 6. Prepare (on the MID Server)**

1. Ask CyberArk for the credentials the job needs (target deployment account, Sectigo API account, keystore password for Java). They are short-lived and are held in memory only.
2. Pre-check: the server is reachable, the account can do what is needed, there is disk space, the service is running, and the server currently presents the old thumbprint that Discovery reported. If it presents something else, stop: the state of the server is not what the CMDB says (drift).
3. Backup: record the old thumbprint, the binding or configuration, and keep the old certificate files or store entry on the server so that a rollback is possible.

**Stage 7. Fetch the certificate and private key**

The MID Server calls the Sectigo API and fetches the bundle (certificate, chain and private key) for the exact Sectigo ID in the job. It checks that the certificate thumbprint equals the expected new thumbprint, that the private key matches the certificate, that the SAN matches the identity, and that the chain is complete. The bundle is held in memory or in encrypted temporary storage on the MID Server, never in ServiceNow (chapter 6).

**Stage 8. Install**

The adapter for the technology installs the certificate and key (chapter 9):

| Technology | What happens |
|---|---|
| Windows IIS | Import into the Windows certificate store (Local Machine, Personal), non-exportable; grant the private key permission only to the identity that needs it |
| Linux Apache | Write certificate, chain and key to a new versioned location; set owner and file permission; switch a symlink; SELinux context |
| Java | Import into the application's keystore (JKS or PKCS#12) with the keystore password from CyberArk |

**Stage 9. Activate**

| Technology | Activation |
|---|---|
| Windows IIS | Update the HTTPS binding to the new thumbprint (with SNI where used); no site restart |
| Linux Apache | Test the configuration, then a graceful reload. Not a server restart |
| Java | Hot reload of the connector where the server supports it, otherwise a controlled restart inside a change window |

**Stage 10. Verify now**

The MID Server opens a TLS connection to the live endpoint (with SNI) and checks: the presented thumbprint equals the new thumbprint, the SAN covers the names, the chain is complete and trusted, the dates are correct. If the check fails, the adapter rolls back to the backup and verifies the rollback, and CDM raises an incident.

**Stage 11. Clean up**

Delete temporary files and clear memory holding the bundle and passwords, close sessions, and confirm the clean-up in the result. The result reported to ServiceNow contains the thumbprints, dates, checks and timings, and no key or password.

**Stage 12. Confirm by the next scan**

| Item | Detail |
|---|---|
| Trigger | The next daily sync after Discovery has scanned again |
| Rule | For the binding: the CI on that server now shows the new thumbprint, the expected valid-to date, and a last-scanned time later than the deployment time |
| Confirmed | Set "Confirmed by discovery", link the old certificate to the new one (replaced by), close the job, write the audit record, update the dashboard |
| Old thumbprint still seen after the scan | The live check said the new one, but Discovery sees the old one: alert (another node, a cache, or a different binding) and do not close |
| Not scanned yet | Wait |
| Not confirmed after the timeout (default 36 hours) | Alert the owner, re-probe the live endpoint, escalate |

### 4.3 The daily clock

Times are examples; all are configuration.

| When | What happens |
|---|---|
| Day 0, 02:00 | ServiceNow Discovery scan runs |
| Day 0, 04:00 | CDM syncs ServiceNow (stage 1) and Sectigo (stage 2), matches and plans (stages 3 and 4) |
| Day 0, from 04:15 | Jobs run at once, or wait for the change window (for example 22:00) (stages 5 to 11) |
| Day 0, after deployment | State "Deployed, awaiting scan". Owner notified of success |
| Day 1, 02:00 | ServiceNow Discovery scans again |
| Day 1, 04:00 | CDM syncs and confirms (stage 12). Done, typically 26 to 30 hours after deployment |
| Day 1, 04:00 to Day 2, 14:00 | Timeout window (36 hours after deployment); alert if still unconfirmed |

### 4.4 State of one binding

```text
 Discovered
     |  expiry window reached
     v
 Expiring ----(no replacement landed by the alert thresholds)----> ALERT (renewal not available)
     |  replacement found at Sectigo, unique match
     v
 Replacement landed --(no profile)--> Manual task ---------------------------+
     |  profile ok, policy ok, approval / window ok                          |
     v                                                                       |
 Planned                                                                     |
     v                                                                       |
 Deploying --(failure)--> Rolled back --> Incident --> retry after fix       |
     |  live check ok                                                        |
     v                                                                       |
 Deployed, awaiting scan  <-------- manual task completed + live check ok ---+
     |  next scan shows new thumbprint + dates
     v
 Confirmed by discovery (done)
```

### 4.5 Exceptions

| Situation | What CDM does |
|---|---|
| Certificate expiring and no replacement at Sectigo | Alert at the configured thresholds (default 30, 14, 7, 3, 1 days). In the first release someone triggers the renewal at Sectigo; a later phase lets CDM request it |
| Two or more possible replacements | Review queue, no deployment |
| No deployment profile | Manual task with instructions; when done, the live check and the next scan still confirm |
| Server does not show the old thumbprint (drift) | Stop before any change; alert |
| Sectigo cannot deliver the bundle (key not created, already downloaded, error) | Stop before any change; alert; see chapter 6 for the fallback |
| Install or activation fails | Roll back, verify the rollback, incident |
| Live check fails | Roll back, verify, incident |
| Rollback fails | Critical incident, the server is flagged, manual recovery |
| CyberArk unavailable | Job waits and retries; alert; never falls back to stored passwords |
| MID Server down | The job moves to another MID Server in the zone, or waits |
| Discovery not scanned for more than 36 hours | Alert; do not decide on stale data |
| Next scan does not confirm | Alert, live re-probe, escalate, never closed silently |

---

## 5. Certificate matching

### 5.1 Identity attributes

| Attribute | ServiceNow (Discovery) | Sectigo | Use |
|---|---|---|---|
| Thumbprint (fingerprint) | Yes | Yes | Exact identity of one certificate |
| Serial number | Yes | Yes | Exact identity, second key |
| Certificate name and common name | Yes | Yes | Lineage between old and new |
| SAN set | Yes | Yes | Lineage and name check |
| Valid from and valid to (exact UTC) | Yes | Yes | Order in time; the new one starts later and ends later |
| Server | **Yes, only here** | No | Where to deploy |
| Certificate and private key | **No, not stored** | **Yes, only here** | What to deploy |
| Sectigo ID and status | No | **Yes, only here** | How to fetch |

### 5.2 Rules

| Rule | Description | Outcome |
|---|---|---|
| M1 | The thumbprint at Sectigo equals the thumbprint in ServiceNow | Same certificate. Link the CMDB CI to the Sectigo record |
| M2 | Renewal: same common name, same SAN set (or a superset the policy allows), later valid-from and later valid-to than the certificate in ServiceNow, and not yet deployed by CDM | The Sectigo certificate is the replacement |
| M3 | More than one candidate satisfies M2 | Ambiguous: review queue. The newest is never chosen automatically |
| M4 | A certificate in ServiceNow with no counterpart at Sectigo | Unknown to Sectigo (other CA or unmanaged): report |
| M5 | A certificate at Sectigo with no server in ServiceNow | Unlocated: report, cannot deploy |
| M6 | Compare all timestamps in UTC with a small skew tolerance | Avoids false differences |
| M7 | The same certificate on several servers | One replacement, one binding per server, deployed one by one |
| M8 | Wildcard or multi-SAN certificate | Matched by the full SAN set, never by one name |

### 5.3 Uniqueness guarantee

A deployment job is created only if the match is unique and the identity check passes. After the bundle is fetched, the thumbprint and SAN are checked again against what the plan expected. Any difference stops the job before any change to the server.

---

## 6. Private key and certificate bundle handling

Sectigo creates the private key together with the certificate and delivers both by API (to be verified with Sectigo, item V1). This is the secure path you chose, and it fits the flow: the server never has to generate a request, and CDM never handles a request. It also means the key travels, so the handling is strict.

### 6.1 Design rules

1. **Two separate fetches.** The public certificate is fetched early (stage 2) for identity and matching. The bundle with the private key is fetched only at deployment time (stage 7).
2. **The MID Server fetches the bundle directly from Sectigo.** The key never enters ServiceNow: not in a table, a log, a job payload, a flow variable or an ECC message.
3. **Memory or encrypted temporary storage only.** The bundle is held in memory, or in encrypted temporary storage with a short life (default 15 minutes), on the MID Server. It is deleted, and the deletion is confirmed, at the end of the job, whether the job succeeded or failed.
4. **Passphrase.** Any passphrase that protects the bundle is generated per job on the MID Server (or supplied by CyberArk) and held in memory only.
5. **Protected transfer to the server.** The bundle reaches the server only through the encrypted channel of the adapter (WinRM over HTTPS, SSH). It is imported or written on the server and the temporary copy is deleted there too.
6. **Non-exportable where possible.** On Windows the key is imported as non-exportable. On Linux the key file is owned by root and readable only by the service if the profile says so. In Java the key goes into the keystore only.
7. **Limited exposure.** A bundle is fetched once per job. If Sectigo allows a limited number of downloads, CDM records each download and alerts when a bundle is fetched more than expected.
8. **Same key on several servers.** When one certificate is deployed to several servers, they share the key that Sectigo created. That is how load-balanced pairs already work, and it is recorded per binding.
9. **No permanent copy.** CDM keeps no key after deployment. The key remains only on the servers that use it (and at Sectigo, item V1).

### 6.2 If Sectigo cannot deliver the key by API

The fallback keeps the same flow with one step added: the adapter creates the key and the certificate request on the server, CDM submits the request to Sectigo, and the issued certificate is installed against the key that stays on the server. The key then never travels. This requires CDM to start the issuance (a later phase) and a per-technology request step in each adapter. The decision is made after verification item V1.

### 6.3 Points to verify with Sectigo (V1)

- Is server-side key generation available for your organisation and certificate profile, and by API?
- Which API call returns the bundle, in which format (PKCS#12 or PEM), and how is the passphrase set?
- Can the bundle be downloaded more than once, and for how long?
- Does Sectigo keep a copy of the key (key escrow), and how is it removed or protected there?
- Is the renewed certificate a new key or the same key as the old one?


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
