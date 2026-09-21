from dlib import *


def entity(ax, x, ytop, w, title, fields, kind="sn"):
    fc, ec = PAL[kind]
    n = len(fields)
    lh = 1.75
    h = 3.2 + n * lh + 0.7
    y = ytop - h
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.5", fc="white", ec=ec, lw=1.5, zorder=3))
    ax.add_patch(FancyBboxPatch((x, y + h - 3.0), w, 3.0, boxstyle="round,pad=0,rounding_size=0.5", fc=fc, ec=ec, lw=1.5, zorder=4))
    ax.text(x + w / 2, y + h - 1.5, title, ha="center", va="center", fontsize=9, fontweight="bold", color=INK, zorder=5)
    for i, f in enumerate(fields):
        ax.text(x + 0.9, y + h - 3.0 - 1.15 - i * lh, f, fontsize=7.2, va="center", ha="left", color=INK, zorder=5)
    return (x, y, w, h)


# --------------------------------------------------------------------------- 08
def d08_erd(out):
    fig, ax = canvas(16, 10.6, "Logical Data Model (ServiceNow tables)",
                     "PK = primary key, FK = reference. No table stores private keys or plain-text secrets; CredentialRef holds vault paths only", ymax=66.25)
    W = 21
    X = [1.5 + i * 25.6 for i in range(4)]
    Y1, Y2, Y3 = 59, 40, 21
    E = {}
    E["approval"] = entity(ax, X[0], Y1, W, "Approval", ["PK approval_id", "FK request_id", "approver", "decision", "comment", "decided_at"], "warn")
    E["request"] = entity(ax, X[1], Y1, W, "CertRequest", ["PK request_id", "type: new|renew|revoke", "FK policy_id, ca_id", "requester, owner_group", "csr_fingerprint (public)", "ca_order_id", "state, created_at"], "sn")
    E["ca"] = entity(ax, X[2], Y1, W, "CAProfile", ["PK ca_id", "type: Sectigo|ACME|ADCS", "endpoint_url", "cert_profile / template", "FK credential_alias", "rate_limits, status"], "ca")
    E["policy"] = entity(ax, X[3], Y1, W, "Policy", ["PK policy_id", "min_key_size, algorithms", "max_validity_days", "allowed_ca_ids", "approval_rule", "renew_before_days"], "sn")
    E["cert"] = entity(ax, X[0], Y2, W, "Certificate", ["PK cert_id", "common_name, SAN[]", "serial, thumbprint (SHA-256)", "issuer, not_before, not_after", "key_algo, key_size", "state (lifecycle)", "FK request_id, owner_group"], "sn")
    E["binding"] = entity(ax, X[1], Y2, W, "Binding", ["PK binding_id", "FK cert_id, target_id", "service, port, sni", "store_path / secret_name", "previous_thumbprint", "last_verified_at"], "sn")
    E["target"] = entity(ax, X[2], Y2, W, "TargetEndpoint (CMDB CI)", ["PK target_id", "hostname / URL / cluster", "technology (windows|linux|k8s..)", "environment, criticality", "FK zone_id, cluster_id", "owner_group"], "tgt")
    E["mid"] = entity(ax, X[3], Y2, W, "Zone / MIDServer", ["PK zone_id", "mid_names[] (HA set)", "network_zone", "status, last_heartbeat", "allowed_adapters[]", "capacity"], "mid")
    E["audit"] = entity(ax, X[0], Y3, W, "AuditEvent", ["PK event_id", "actor, role", "action, object_ref", "timestamp (UTC)", "result, evidence_ref", "prev_hash (tamper-evident)"], "vault")
    E["job"] = entity(ax, X[1], Y3, W, "DeploymentJob", ["PK job_id", "FK request_id, binding_id", "FK adapter_id, zone_id", "state, attempt", "backup_ref (rollback point)", "started_at, ended_at", "verification_evidence"], "mid")
    E["adapter"] = entity(ax, X[2], Y3, W, "Adapter (signed)", ["PK adapter_id", "technology, version", "signature_sha256", "status: approved|revoked", "allowed_operations[]", "approved_by, approved_at"], "mid")
    E["cred"] = entity(ax, X[3], Y3, W, "CredentialRef", ["PK alias", "vault_path (no secret)", "scope: discovery|deploy", "FK zone_id", "lease_ttl", "rotation_policy"], "vault")

    def mid(e, side):
        x, y, w, h = e
        return {"l": (x, y + h / 2), "r": (x + w, y + h / 2), "t": (x + w / 2, y + h), "b": (x + w / 2, y)}[side]

    def rel(a, sa, b, sb, text, dy=1.6, dx=0):
        p1, p2 = mid(E[a], sa), mid(E[b], sb)
        yy = min(E[a][1] + E[a][3], E[b][1] + E[b][3]) - 8.5
        p1, p2 = (p1[0], yy), (p2[0], yy)
        line(ax, [p1, p2], arrow_end=False, color="#455A64", lw=1.4)
        label(ax, (p1[0] + p2[0]) / 2 + dx, yy + 1.4, text, fs=7.4, bold=True)
    rel("approval", "r", "request", "l", "N:1")
    rel("request", "r", "ca", "l", "N:1")
    rel("ca", "r", "policy", "l", "N:M")
    # request -> certificate (diagonal)
    x, y, w, h = E["request"]
    x2, y2, w2, h2 = E["cert"]
    line(ax, [(x + 4, y), (x2 + w2 - 4, y2 + h2)], arrow_end=False, color="#455A64", lw=1.4)
    label(ax, (x + 4 + x2 + w2 - 4) / 2 + 0.5, (y + y2 + h2) / 2, "1:0..1 produces", fs=7.2)
    rel("cert", "r", "binding", "l", "1:N")
    rel("binding", "r", "target", "l", "N:1")
    rel("target", "r", "mid", "l", "N:1")
    p1, p2 = mid(E["binding"], "b"), mid(E["job"], "t")
    line(ax, [p1, p2], arrow_end=False, color="#455A64", lw=1.4)
    label(ax, p1[0], (p1[1] + p2[1]) / 2, "1:N deployed by", fs=7.2)
    rel("audit", "r", "job", "l", "1:N")
    rel("job", "r", "adapter", "l", "N:1")
    p1, p2 = mid(E["mid"], "b"), mid(E["cred"], "t")
    line(ax, [p1, p2], arrow_end=False, color="#455A64", lw=1.4)
    label(ax, p1[0], (p1[1] + p2[1]) / 2, "1:N", fs=7.2)
    save(fig, out)


# --------------------------------------------------------------------------- 09
def d09_poc(out):
    fig, ax = canvas(16, 10.7, "Current POC Topology (single Windows laptop) and Findings",
                     "Derived from Promp.md.txt, POC_SETUP_STATUS.md and mock_sectigo.ps1; red items must change before production", ymax=66.9)
    group(ax, 1, 51, 62, 9, "ServiceNow Personal Developer Instance (cloud)", "sn")
    box(ax, 2.2, 52.2, 18.5, 5, "Flow Designer:\nUniversal Certificate\nDeployment Engine", "sn", fs=7.8)
    box(ax, 22.5, 52.2, 18.5, 5, "REST Message:\nSectigo Generic CA API\n(GET, via MID)", "sn", fs=7.8)
    box(ax, 42.8, 52.2, 19, 5, "If / Else If on flow variable\ntarget_technology_type\n(Windows | RHEL)", "sn", fs=7.8)
    arrow(ax, (20.7, 54.7), (22.5, 54.7)); arrow(ax, (41, 54.7), (42.8, 54.7))
    group(ax, 1, 3, 62, 39, "Windows laptop (Windows 11), the only machine in the POC", "tgt")
    box(ax, 23, 30, 17, 8, "MID Server\nLocal_Laptop_POC_MID\nC:\\ServiceNow_MID, Java 17", "mid", fs=7.6)
    box(ax, 3, 30, 17, 8, "Mock Sectigo API\nmock_sectigo.ps1\nhttp://localhost:8080/sectigo/", "ca", fs=7.6)
    box(ax, 43, 30, 18, 8, "WinRM listener\n127.0.0.1:5985 (HTTP)\nBasic auth, unencrypted", "bad", fs=7.6)
    box(ax, 3, 12, 17, 8, "Staging folder\nC:\\temp\\cert_stage\nproduction_cert.cer", "neutral", fs=7.6)
    box(ax, 23, 12, 17, 8, "Environment A: Windows\nCert:\\LocalMachine\\My\n(certlm.msc)", "ok", fs=7.6)
    box(ax, 43, 12, 18, 8, "Environment B: Linux sim.\nC:\\mock_linux_server\\etc\\\nssl\\certs\\app_server.crt", "warn", fs=7.6)
    arrow(ax, (31.5, 51), (31.5, 38), None, "mid", lw=1.6); badge(ax, 33.5, 45, 1)
    label(ax, 43, 45, "ECC queue (outbound HTTPS)", fs=7.4)
    arrow(ax, (23, 34), (20, 34), None, "ca", both=True, lw=1.6); badge(ax, 21.5, 36.6, 2, r=0.9, fs=7.5)
    arrow(ax, (40, 34), (43, 34), None, "mid", lw=1.6); badge(ax, 41.5, 36.6, 3, r=0.9, fs=7.5)
    arrow(ax, (52, 30), (52, 20), None, "mid", lw=1.6); badge(ax, 54.0, 25, 4, r=0.9, fs=7.5)
    arrow(ax, (46, 30), (36, 20), None, "mid", lw=1.6); badge(ax, 42.0, 26.0, 4, r=0.9, fs=7.5)
    arrow(ax, (23, 16), (20, 16), None, "neutral", lw=1.2)
    label(ax, 32, 8.0, "1 flow job sent to MID over the ECC queue   2 MID GETs the payload from the mock API   3 MID opens WinRM to 127.0.0.1\n"
                       "4 PowerShell: Windows branch stages then Import-Certificate; RHEL branch writes the mock .crt file", fs=7.2, bg=False)
    # findings
    group(ax, 65, 3, 34, 57, "Findings to resolve in the specification", "bad")
    F = [("G1", "Mock returns literal \\n text and fake data, not a real PEM; Import-Certificate will reject it. Use a real self-signed test cert."),
         ("G2", "Flow moves only a public certificate: no CSR, no private key. A store import without the key cannot serve TLS."),
         ("G3", "WinRM HTTP + Basic + AllowUnencrypted is POC-only. Production: WinRM/HTTPS or Kerberos, SSH certs."),
         ("G4", "One admin account (password in SN credential) does everything. Split discovery from deployment accounts; use vault aliases."),
         ("G5", "Response body is pasted into a PowerShell here-string. Use validated parameters and signed, versioned adapters."),
         ("G6", "Endpoint is a placeholder (sectigo.com) vs mock localhost:8080, and no auth or cert types are modelled."),
         ("G7", "Routing depends on a hand-edited flow variable; derive technology from the CMDB CI instead."),
         ("G8", "Linux path is a bare file drop: no permissions, reload, backup, rollback or verification.")]
    yy = 55.4
    for g, t in F:
        box(ax, 66.2, yy - 5.0, 31.6, 5.3, "", "bad", lw=1.0)
        ax.text(67.2, yy - 2.35, g, fontsize=8.4, fontweight="bold", color="#C62828", va="center", zorder=8)
        ax.text(70.6, yy - 2.35, "\n".join(textwrap.fill(t, 58).split("\n")), fontsize=7.3, va="center", ha="left", color=INK, zorder=8, linespacing=1.15)
        yy -= 6.6
    save(fig, out)


# --------------------------------------------------------------------------- 10
def d10_platforms(out):
    fig, ax = canvas(16, 10.8, "Platform-Specific Deployment Paths",
                     "Same orchestrated lifecycle, different signed adapter per platform; every path ends in live verification with a rollback", ymax=67.5)
    lanes = [
        ("Windows", "mid", ["WinRM over HTTPS\nJIT credential from vault", "certreq -new: key created in\nLocalMachine\\My, non-exportable", "certreq -accept after CA issues;\nchain to Intermediate store",
                             "Re-bind IIS / RDP / service;\narchive old thumbprint", "TLS probe: thumbprint, SAN,\nchain. Rollback: re-bind old"]),
        ("Linux", "mid", ["SSH with short-lived\nsigned cert (SSH CA)", "openssl req: key 0600\nroot:ssl-cert, CSR out", "Write fullchain + key to /etc/pki\nor /etc/ssl; backup; restorecon",
                          "nginx -t / apachectl\nconfigtest, systemctl reload", "openssl s_client probe.\nRollback: restore backup dir"]),
        ("macOS / iOS / iPadOS", "warn", ["Select device group in MDM\n(Intune / Jamf)", "Push SCEP / ACME certificate\nprofile; key in Secure Enclave", "CA issues via SCEP/ACME proxy;\ndevice installs identity",
                                            "Profile payloads (Wi-Fi, VPN,\nS/MIME) reference identity", "MDM inventory: profile + expiry.\nRollback: remove profile"]),
        ("Kubernetes", "sn", ["K8s API via namespaced\nServiceAccount (RBAC)", "cert-manager Certificate CR\nor in-cluster CSR", "Update kubernetes.io/tls Secret;\nkeep previous revision",
                              "Rollout restart / ingress\nreload, wait for readiness", "Probe Ingress + Service VIP.\nRollback: previous Secret"]),
        ("F5 / NetScaler appliance", "ca", ["Vendor REST API token\n(iControl / NITRO) from vault", "Generate CSR on device\n(key stays in device / HSM)", "Import issued cert + chain;\nsave running config backup",
                                             "Update client-ssl profile;\nsync HA device group", "Probe each VIP + member.\nRollback: previous profile"]),
    ]
    heads = ["1  Connect", "2  Key and CSR", "3  Install", "4  Activate", "5  Verify / rollback"]
    x0, w, gap = 16, 15.2, 1.8
    for i, hd in enumerate(heads):
        box(ax, x0 + i * (w + gap), 58.3, w, 3.0, hd, "title", fs=8.6, bold=True, color="white", rounding=0.4)
    y = 49.5
    for name, kind, steps in lanes:
        box(ax, 1, y, 13.5, 8.2, name, kind, fs=9, bold=True, wrap=14)
        for i, t in enumerate(steps):
            box(ax, x0 + i * (w + gap), y, w, 8.2, t, "neutral", fs=7.3)
            if i:
                arrow(ax, (x0 + i * (w + gap) - gap, y + 4.1), (x0 + i * (w + gap), y + 4.1), lw=1.3)
        y -= 10.4
    ax.text(1, 3.0, "Java keystores, databases and cloud services reuse the Windows / Linux / API paths and add a keystore or listener update step.",
            fontsize=8.2, color=MUTED, va="center")
    save(fig, out)


# --------------------------------------------------------------------------- 11
def d11_roadmap(out):
    fig, ax = canvas(16, 8.6, "Delivery Roadmap",
                     "Durations are indicative for planning and must be confirmed with the team", ymax=53.75)
    phases = [
        ("Phase 0: POC", "now, 1-2 weeks", "ok", ["Single laptop", "Windows store + mock Linux path", "Mock Sectigo API", "Flow Designer routing", "Close findings G1-G3"]),
        ("Phase 1: MVP", "6-8 weeks", "sn", ["Real Sectigo sandbox (enroll, collect)", "CSR generated on target", "Windows + Linux adapters, secure transport", "Vault integration, JIT credentials",
                                              "Inventory, expiry dashboard", "Pre-check, backup, verify, rollback", "Signed adapter registry, manual fallback"]),
        ("Phase 2: Expansion", "8-10 weeks", "mid", ["Kubernetes, Java keystores", "F5 / NetScaler", "macOS / iOS through MDM", "Multi-zone MID Servers, HA", "Approvals + change integration",
                                                      "Auto-renew, discovery (endpoint + host)"]),
        ("Phase 3: Enterprise", "8-12 weeks", "ca", ["Cloud services, databases, network / IoT", "ACME and Microsoft ADCS CAs", "SIEM, compliance evidence", "DR test, load test, pen test",
                                                      "Operations runbooks and training"]),
        ("Phase 4: Optimise", "ongoing", "vault", ["Shorter certificate lifetimes (CA/B Forum SC-081)", "Crypto-agility, PQC readiness", "Self-service growth", "Cost and capacity tuning"]),
    ]
    w = 18.4
    for i, (t, d, k, items) in enumerate(phases):
        x = 1 + i * 19.6
        fc, ec = PAL[k]
        ax.add_patch(Polygon([(x, 45), (x + w - 1.5, 45), (x + w + 0.3, 41.3), (x + w - 1.5, 37.6), (x, 37.6), (x + 1.8, 41.3)], closed=True, fc=ec, ec="white", lw=1.5, zorder=3))
        ax.text(x + w / 2 - 0.3, 42.3, t, ha="center", va="center", fontsize=8.8, fontweight="bold", color="white", zorder=4)
        ax.text(x + w / 2 - 0.3, 39.9, d, ha="center", va="center", fontsize=7.6, color="white", zorder=4)
        box(ax, x, 6, w, 30.4, "", k, lw=1.2)
        yy = 34.4
        for it in items:
            lines = textwrap.wrap(it, 30)
            txt = "• " + ("\n   ").join(lines)
            ax.text(x + 1.0, yy, txt, fontsize=8.6, va="top", ha="left", color=INK, zorder=5, linespacing=1.2)
            yy -= 0.95 * len(lines) + 2.0
    ax.text(1, 2.6, "Gate between phases: security review, restore/rollback test, and acceptance sign-off against the requirement IDs in the specification.",
            fontsize=8.4, color=MUTED, va="center")
    save(fig, out)
