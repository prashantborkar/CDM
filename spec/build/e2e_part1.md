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
