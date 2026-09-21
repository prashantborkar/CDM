
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
