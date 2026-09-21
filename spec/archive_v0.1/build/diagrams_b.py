from dlib import *


# --------------------------------------------------------------------------- 04
def d04_sequence(out):
    fig, ax = canvas(16, 11.2, "Sequence: Issue a Certificate and Deploy It",
                     "Private key is created on the target and never leaves it; only the CSR and the public certificate travel", ymax=70)
    parts = [("Requester /\nscheduler", "neutral", 8), ("ServiceNow\n(CDM)", "sn", 24), ("Vault", "vault", 40),
             ("MID Server", "mid", 56), ("Target host", "tgt", 72), ("Sectigo CA", "ca", 90)]
    top = 57
    for name, kind, x in parts:
        box(ax, x - 6, top, 12, 5.2, name, kind, fs=8.8, bold=True)
        ax.plot([x, x], [top, 3], color="#90A4AE", lw=1.1, ls=(0, (4, 3)), zorder=2)
    R, S, V, M, T, C = 8, 24, 40, 56, 72, 90
    msgs = [
        (R, S, "Renewal trigger (expiry scan) or new request", "neutral"),
        ("self", S, "Validate policy, approvals, change window", "sn"),
        (S, M, "Dispatch signed adapter job (adapter id + version, target ref, credential ALIAS)", "mid"),
        (M, V, "Request just-in-time credential for alias (mTLS)", "vault"),
        (V, M, "Short-lived secret (lease, auto-revoked)", "vault"),
        (M, T, "Generate key pair + CSR ON the target (WinRM/HTTPS or SSH)", "mid"),
        (T, M, "CSR only (private key stays on target / HSM / TPM)", "mid"),
        (M, S, "Return CSR via ECC queue (outbound 443)", "mid"),
        (S, C, "Enroll (CSR, profile, SAN list) via REST", "ca"),
        (C, S, "Issued: certificate + chain (collect / webhook)", "ca"),
        (S, M, "Deploy job: public cert + chain only, rollback point requested", "mid"),
        (M, T, "Pre-check, back up current cert + config, install, bind, reload", "mid"),
        (M, T, "Verify presented cert at live endpoint (SAN, chain, expiry, thumbprint)", "mid"),
        (M, S, "Result + evidence; scrub temp files, drop session, revoke lease", "mid"),
        (S, R, "Notify owner, update inventory/CMDB, write audit trail", "sn"),
    ]
    y = 52.5
    dy = 3.4
    for i, (a, b, text, kind) in enumerate(msgs, 1):
        ec = PAL[kind][1] if kind != "neutral" else "#37474F"
        if a == "self":
            line(ax, [(b, y), (b + 6, y), (b + 6, y - 1.5), (b + 0.3, y - 1.5)], color=ec)
            ax.text(b + 7, y - 0.7, text, fontsize=8, va="center", ha="left", color=INK, zorder=7)
        else:
            arrow(ax, (a, y), (b, y), None, color=ec, lw=1.6)
            mx = (a + b) / 2
            ax.text(mx, y + 0.95, text, fontsize=7.8, ha="center", va="center", color=INK, zorder=7,
                    bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.95))
        badge(ax, 1.6, y, i, r=1.0, fs=7.5)
        y -= dy + (1.0 if a == 'self' else 0)
    save(fig, out)


# --------------------------------------------------------------------------- 05
def d05_adapters(out):
    fig, ax = canvas(16, 11.6, "Technology Adapter Routing Matrix",
                     "The router picks one signed adapter per target technology; adapters own all platform-specific logic", ymax=72.5)
    cols = [(14, 15, "Adapter"), (30, 17, "Targets covered"), (48, 19, "Transport and auth"),
            (68, 25, "Install / update method"), (94, 5, "Tier")]
    ytop = 63
    for x, w, t in cols:
        box(ax, x, ytop, w, 3.4, t, "title", fs=8.8, bold=True, color="white", rounding=0.4)
    rows = [
        ("Windows", "Windows Server 2016+, IIS, SChannel, RDP, Exchange, SQL Server", "WinRM over HTTPS (5986), Kerberos or cert auth, scoped service account",
         "PFX/PEM import to Cert:\\LocalMachine\\My, rebind IIS / service, old cert archived", "MVP", "ok"),
        ("Linux / Unix", "RHEL, Ubuntu, SUSE; nginx, Apache, HAProxy, Postfix", "SSH with short-lived signed user cert (SSH CA) or vault key",
         "PEM to /etc/pki/tls or /etc/ssl, chmod 0600, restorecon, config test, systemctl reload", "MVP", "ok"),
        ("Manual fallback", "Any system that cannot be safely automated", "ServiceNow task to owner group, no remote access",
         "Generated instructions + evidence upload; automated verification still runs", "MVP", "ok"),
        ("Kubernetes", "K8s, OpenShift, AKS / EKS / GKE ingress and workloads", "Kubernetes API, namespaced ServiceAccount + RBAC, OIDC",
         "kubernetes.io/tls Secret update or cert-manager issuer, rollout restart, ingress probe", "Phase 2", "warn"),
        ("Apple: macOS, iOS, iPadOS", "MDM-enrolled Macs, iPhones, iPads", "MDM API (Intune, Jamf, Apple MDM) with API client in vault",
         "SCEP / ACME / PKCS#12 configuration profile push; macOS: security import to System keychain", "Phase 2", "warn"),
        ("Java / app servers", "Tomcat, JBoss, WebLogic, Spring Boot, Kafka", "Through the OS adapter (SSH or WinRM)",
         "keytool import into PKCS#12 / JKS, alias handling, keystore backup, restart", "Phase 2", "warn"),
        ("Load balancers / firewalls", "F5 BIG-IP, Citrix NetScaler, Palo Alto, Fortinet", "Vendor REST API (iControl REST, NITRO), token from vault",
         "Upload cert+key, update client-ssl profile, config sync across HA pair", "Phase 2", "warn"),
        ("Cloud services", "Azure Key Vault / App Gateway, AWS ACM / ELB, GCP", "Cloud SDK / REST with workload identity, no static keys",
         "Import or rotate certificate object, update listener binding", "Phase 3", "bad"),
        ("Databases / middleware", "SQL Server, PostgreSQL, Oracle, MQ", "Through the OS adapter plus engine-specific command",
         "Place files or store entry, engine reload / restart, connection test", "Phase 3", "bad"),
        ("Network devices / IoT", "Routers, switches, printers, appliances", "SCEP or EST enrollment, vendor CLI over SSH",
         "Device-side enrollment or CLI import, config save", "Phase 3", "bad"),
    ]
    rh = 5.55
    y = ytop - 1.0 - rh
    for name, tg, tr, me, tier, k in rows:
        box(ax, 14, y, 15, rh - 0.6, name, "sn", fs=8.4, bold=True, wrap=16)
        box(ax, 30, y, 17, rh - 0.6, tg, "neutral", fs=7.3, wrap=27)
        box(ax, 48, y, 19, rh - 0.6, tr, "neutral", fs=7.3, wrap=31)
        box(ax, 68, y, 25, rh - 0.6, me, "neutral", fs=7.3, wrap=42)
        box(ax, 94, y, 5, rh - 0.6, tier.replace("Phase ", "P"), k, fs=8, bold=True)
        arrow(ax, (10.5, 38), (14, y + (rh - 0.6) / 2), None, "neutral", lw=0.9, rad=0.0)
        y -= rh
    group(ax, 1, 20.5, 9.5, 35, "", "sn")
    box(ax, 1.6, 30, 8.3, 16, "Adapter\nrouter\n\nkey:\ntechnology +\nzone +\ncluster", "sn", fs=8.2, bold=True)
    ax.text(14, 3.2, "Tier: MVP = first release;  P2 / P3 = later phases (see roadmap).", fontsize=8, color=MUTED, va="center")
    save(fig, out)


# --------------------------------------------------------------------------- 06
def d06_security(out):
    fig, ax = canvas(16, 11.4, "Security Architecture and Network Zones",
                     "Zone-specific MID Servers, vault-held credentials, no permanent private keys, only signed adapters", ymax=71.25)
    group(ax, 2, 48, 68, 15.5, "ServiceNow cloud instance (customer-controlled)", "sn")
    for i, t in enumerate(["Orchestration +\nlifecycle state machine", "Signed adapter registry\n(approved versions only)", "Credential ALIASES\n(no secrets stored)", "Immutable audit trail\nforwarded to SIEM"]):
        box(ax, 3.2 + i * 16.6, 50, 15.4, 8.2, t, "sn", fs=8.2)
    group(ax, 73, 48, 25, 15.5, "Secrets and key custody", "vault")
    box(ax, 74.2, 55.6, 22.6, 5.0, "Vault (HashiCorp / CyberArk /\nAzure Key Vault): dynamic secrets", "vault", fs=8)
    box(ax, 74.2, 50, 22.6, 4.6, "HSM / KMS; private CA keys", "vault", fs=8)
    yb = 44
    line(ax, [(8, yb), (92, yb)], arrow_end=False, color="#1565C0", lw=2)
    arrow(ax, (36, yb), (36, 48), None, "mid", both=True, lw=1.8)
    arrow(ax, (86, yb), (86, 48), None, "vault", both=True, lw=1.8)
    label(ax, 36, 45.8, "1  outbound-initiated TLS 443 only", fs=7.8, bold=True)
    label(ax, 86, 45.8, "2  JIT secrets over mTLS", fs=7.8, bold=True)
    zones = [(2, "Zone A: DMZ", ["MID-DMZ-01"], "Web servers, reverse proxies,\nload balancers (nginx, IIS, F5)", "WinRM/HTTPS · SSH · REST"),
             (35.5, "Zone B: Internal / data centre", ["MID-INT-01", "MID-INT-02 (HA)"], "Windows, Linux, Java, databases,\nappliances", "WinRM/HTTPS · SSH · REST"),
             (69, "Zone C: Cloud / Kubernetes / endpoints", ["MID-CLD-01"], "K8s API, cloud services,\nMDM (macOS / iOS)", "K8s API · cloud API · MDM API")]
    for x, title, mids, tgt, tr in zones:
        group(ax, x, 15, 29.5, 26.5, title, "mid")
        n = len(mids)
        w = (27 - (n - 1) * 1) / n
        for i, m in enumerate(mids):
            box(ax, x + 1.2 + i * (w + 1), 33, w, 5.2, m, "mid", fs=8.2, bold=True)
            line(ax, [(x + 1.2 + i * (w + 1) + w / 2, 38.2), (x + 1.2 + i * (w + 1) + w / 2, yb)], arrow_end=False, color="#1565C0", lw=1.4)
        box(ax, x + 1.2, 25, 12.6, 5.6, "Discovery account\n(read-only)", "warn", fs=7.6)
        box(ax, x + 15.6, 25, 12.6, 5.6, "Deployment account\n(write, scoped)", "bad", fs=7.6)
        box(ax, x + 1.2, 16.4, 27, 5.6, tgt, "tgt", fs=7.8)
        arrow(ax, (x + 14.75, 25), (x + 14.75, 22.2), None, "mid", both=True)
        label(ax, x + 14.75, 23.6, tr, fs=7)
        line(ax, [(x + 14.75, 33), (x + 14.75, 30.9)], arrow_end=False, color="#1565C0", lw=1.2)
    box(ax, 2, 1.2, 96, 11.6, "", "neutral", ls="--", lw=1.0)
    L = [("3", "No permanent private keys on any MID Server; CSR is generated on the target, temp material is encrypted and securely wiped."),
         ("4", "Only approved, signed, version-controlled adapters run; unsigned scripts are rejected by the MID allow-list."),
         ("5", "Discovery and deployment use different accounts, roles and workflow permissions (least privilege, per zone)."),
         ("6", "No passwords in scripts, flow variables or config files; credentials are vault aliases resolved just in time."),
         ("7", "Every job is audited (who, what, when, thumbprint) and streamed to the SIEM; break-glass access is time-boxed.")]
    for i, (n, t) in enumerate(L):
        yy = 10.6 - i * 2.1
        badge(ax, 3.6, yy, n, r=0.85, fs=7.2)
        ax.text(5.4, yy, t, fontsize=8.1, va="center", ha="left", color=INK, zorder=7)
    save(fig, out)


# --------------------------------------------------------------------------- 07
def d07_lifecycle(out):
    fig, ax = canvas(16, 9.6, "Certificate Lifecycle State Machine",
                     "States tracked on every certificate record; transitions are audited and policy-gated", ymax=60)
    w, h = 13, 7.2
    A = [("Discovered", "neutral"), ("Requested", "sn"), ("Pending\napproval", "warn"), ("Approved", "sn"), ("Issuing", "ca"), ("Issued", "ca")]
    yA = 44
    xsA = [2 + i * 16 for i in range(6)]
    for (t, k), x in zip(A, xsA):
        box(ax, x, yA, w, h, t, k, fs=9.5, bold=True)
    labsA = ["policy ok", "submitted", "approve", "CA accepts", "CA issues"]
    for i in range(5):
        arrow(ax, (xsA[i] + w, yA + h / 2), (xsA[i + 1], yA + h / 2))
        label(ax, xsA[i] + w + 1.5, yA + h / 2 + 2.4, labsA[i], fs=7.4)
    yB = 27
    B = [("Deploying", "mid", 82), ("Verifying", "mid", 66), ("Active\n(deployed)", "ok", 50), ("Expiring\n(renewal window)", "warn", 34), ("Renewing", "sn", 18)]
    for t, k, x in B:
        box(ax, x, yB, w, h, t, k, fs=9.2, bold=True)
    arrow(ax, (88.5, yA), (88.5, yB + h), "deploy job")
    arrow(ax, (82, yB + h / 2), (79, yB + h / 2)); label(ax, 80.5, yB + h / 2 + 2.3, "installed", fs=7.4)
    arrow(ax, (66, yB + h / 2), (63, yB + h / 2)); label(ax, 64.5, yB + h / 2 + 2.3, "verified", fs=7.4)
    arrow(ax, (50, yB + h / 2), (47, yB + h / 2)); label(ax, 48.5, yB + h / 2 + 2.3, "T-30 d", fs=7.4)
    arrow(ax, (34, yB + h / 2), (31, yB + h / 2)); label(ax, 32.5, yB + h / 2 + 2.3, "auto-renew", fs=7.4)
    line(ax, [(24.5, yB + h), (24.5, 39.5), (72.5, 39.5), (72.5, yA)], color="#7B1FA2")
    label(ax, 48, 39.5, "renewal: new CSR, same policy path", fs=7.6)
    yC = 10
    C = [("Retired", "neutral", 18), ("Expired", "bad", 34), ("Revoked", "bad", 50), ("Rolled back\n(failed verify)", "bad", 66)]
    for t, k, x in C:
        box(ax, x, yC, w, h, t, k, fs=9.2, bold=True)
    arrow(ax, (40.5, yB), (40.5, yC + h), "not renewed", loff=(0.2, 0))
    arrow(ax, (56.5, yB), (56.5, yC + h), "compromise / user", loff=(0.4, 0))
    arrow(ax, (72.5, yB), (72.5, yC + h), "verify failed", loff=(0.2, 0))
    arrow(ax, (34, yC + h / 2), (31, yC + h / 2))
    line(ax, [(56.5, yC), (56.5, 7), (24.5, 7), (24.5, yC)], color="#455A64")
    label(ax, 40, 7, "decommission (owner or policy)", fs=7.6)
    arrow(ax, (79, yC + h / 2), (92, yC + h / 2), None, "bad", ls="--")
    ax.text(85.5, yC + h / 2 + 1.7, "incident +\nretry", fontsize=7.8, ha="center", va="center", color="#C62828")
    save(fig, out)
