from dlib import *


# --------------------------------------------------------------------------- 01
def d01_context(out):
    fig, ax = canvas(16, 9.6, "Certificate Deployment Manager (CDM): System Context",
                     "ServiceNow Discovery/CMDB know where; Sectigo issues; CDM joins them and deploys through vault-controlled MID Servers", ymax=60)
    # people
    group(ax, 1, 24, 17, 29, "People", "tgt")
    for i, t in enumerate(["Certificate owner\n(app / platform team)", "PKI / security admin",
                           "Approver\n(change manager)", "Auditor /\ncompliance"]):
        box(ax, 2.2, 45 - i * 6.6, 14.6, 5.2, t, "neutral", fs=8.6)
    # ServiceNow
    group(ax, 22, 24, 42, 29, "ServiceNow platform: CDM application", "sn")
    cells = [("Certificate inventory\n(CMDB CIs, expiry, owner)", 0, 0), ("Request & approval\n(catalog, change, RBAC)", 1, 0),
             ("Orchestration engine\n(Flow Designer + state machine)", 0, 1), ("Policy & signed adapter\nregistry (allow-list)", 1, 1),
             ("Credential broker\n(aliases only, no secrets)", 0, 2), ("Audit, reporting,\nnotifications, dashboards", 1, 2)]
    for t, c, r in cells:
        box(ax, 23.2 + c * 20, 43 - r * 6.6, 18.6, 5.4, t, "sn", fs=8.4)
    # CA
    group(ax, 69, 38, 30, 15, "Certificate authorities (pluggable)", "ca")
    box(ax, 70.5, 45.2, 27, 3.6, "Sectigo Certificate Manager (primary)", "ca", fs=8.6, bold=True)
    box(ax, 70.5, 41.2, 27, 3.4, "ACME CAs (Let's Encrypt, ZeroSSL, ...)", "ca", fs=8.4)
    box(ax, 70.5, 39.0, 27, 1.7, "", "ca")
    ax.text(84, 39.85, "Microsoft ADCS / private CA (later)", ha="center", va="center", fontsize=8.4, color=INK, zorder=8)
    # vault
    group(ax, 69, 25.5, 30, 10.5, "Secrets and key custody", "vault")
    box(ax, 70.5, 27.0, 27, 5.2, "Vault (HashiCorp / CyberArk / Azure Key Vault)\nHSM-backed private CA keys", "vault", fs=8.4)
    # MID
    group(ax, 22, 11.5, 42, 10, "MID Server pools (one set per network zone)", "mid")
    for i, t in enumerate(["MID: DMZ zone", "MID: Internal zone\n(HA pair, clustered)", "MID: Cloud / K8s zone"]):
        box(ax, 23.2 + i * 13.6, 13, 12.6, 5.0, t, "mid", fs=8.2)
    # integrated
    group(ax, 69, 11.5, 30, 10.5, "Integrated systems", "tgt")
    box(ax, 70.3, 13.0, 13.2, 5.0, "MDM\n(Intune / Jamf)", "neutral", fs=8.4)
    box(ax, 84.7, 13.0, 13.2, 5.0, "ITSM, SIEM,\nmonitoring", "neutral", fs=8.4)
    # targets
    group(ax, 1, 0.8, 98, 8.4, "Deployment targets", "tgt")
    tg = ["Windows\n(store, IIS, SChannel)", "Linux\n(RHEL, Ubuntu, SUSE)", "macOS / iOS\n(via MDM profile)",
          "Kubernetes\n(TLS Secrets, ingress)", "Java / app servers\n(JKS, PKCS12, Tomcat)", "F5 / NetScaler /\nfirewalls", "Cloud services\n(Azure, AWS, GCP)"]
    w = 12.6
    for i, t in enumerate(tg):
        box(ax, 2.2 + i * 13.85, 1.6, w, 4.6, t, "neutral", fs=7.9, ls="--" if t.startswith("Deferred") else "-")
    # arrows
    arrow(ax, (18, 38), (22, 38), both=True)
    arrow(ax, (64, 46), (69, 46), "REST (HTTPS)", "ca", both=True, loff=(0, 1.9), fs=7.6)
    arrow(ax, (64, 30), (69, 30), "alias lookup", "vault", both=True, loff=(0, 1.8), fs=7.6)
    arrow(ax, (43, 24), (43, 21.5), None, "mid", both=True)
    label(ax, 43, 22.8, "outbound-only HTTPS 443 (ECC queue)", fs=7.6)
    arrow(ax, (64, 16), (69, 16), "REST / API", "mid", both=True, loff=(0, 1.6), fs=7.4)
    arrow(ax, (43, 11.5), (43, 9.2), None, "mid", both=True)
    label(ax, 43, 10.35, "WinRM/HTTPS · SSH · K8s API · REST", fs=7.6)
    arrow(ax, (64, 21), (72, 25.5), "JIT secret\nretrieval", "vault", loff=(-0.5, 0.2), fs=7.4, rad=-0.1)
    save(fig, out)


# --------------------------------------------------------------------------- 02
def d02_layers(out):
    fig, ax = canvas(16, 9.6, "Logical Architecture: Layers and Components",
                     "Each layer talks only to the layer below; platform-specific logic lives only in signed adapters", ymax=60)
    layers = [
        ("PRESENTATION", "sn", 44, ["Self-service catalog", "Cert owner portal", "Expiry dashboard", "Approver workspace", "Auditor reports"]),
        ("ORCHESTRATION", "sn", 35, ["Request handler", "Approval & change gate", "Lifecycle state machine", "Scheduler (expiry / renew)", "Retry, timeout, rollback"]),
        ("DOMAIN SERVICES", "sn", 26, ["Inventory & CMDB sync", "Policy engine", "Adapter router", "Credential broker", "Notification service"]),
        ("INTEGRATION", "mid", 17, ["Sectigo + CA connectors", "ServiceNow Discovery / CMDB API", "Vault connector", "MID dispatcher (zone aware)", "K8s API + executor connectors", "ITSM / SIEM connectors"]),
        ("TARGET ADAPTERS (signed, versioned)", "tgt", 8, ["Windows / IIS", "Linux / Apache, nginx", "Java keystores", "OpenShift / Kubernetes", "F5 / DB / others"]),
    ]
    for name, kind, y, items in layers:
        fc, ec = PAL[kind]
        ax.add_patch(FancyBboxPatch((1, y - 0.6), 78, 8.2, boxstyle="round,pad=0,rounding_size=0.8", fc=fc, ec=ec, lw=1.4, alpha=0.45, zorder=1))
        ax.text(2, y + 6.8, name, fontsize=9, fontweight="bold", color=ec, va="top", zorder=4)
        n = len(items)
        w = (76 - (n - 1) * 1.2) / n
        for i, t in enumerate(items):
            box(ax, 2 + i * (w + 1.2), y, w, 4.6, t, "neutral", fs=8.2, wrap=20)
    # cross cutting
    group(ax, 82, 7.4, 17, 45.4, "Cross-cutting", "vault")
    for i, t in enumerate(["Security\n(RBAC, MFA, least privilege)", "Secrets handling\n(vault, no perm. keys)", "Audit trail\n(immutable events)",
                           "Observability\n(metrics, logs, alerts)", "Compliance\n(CA/B Forum, NIST, ISO)"]):
        box(ax, 83.2, 43.2 - i * 7.7, 14.6, 6.2, t, "vault", fs=8)
    for y in (43.4, 34.4, 25.4, 16.4):
        arrow(ax, (40, y), (40, y - 1.0), None, "neutral", lw=1.2, both=True)
    ax.text(40, 3.2, "Persistent data (ServiceNow tables): Certificate, Request, Target, Job, Adapter, Policy, Audit.  "
                     "No private keys and no plain-text passwords are ever persisted here.",
            fontsize=8.6, ha="center", color=MUTED)
    save(fig, out)


# --------------------------------------------------------------------------- 03
def d03_workflow(out):
    fig, ax = canvas(16, 10.4, "End-to-End Deployment Workflow",
                     "Trigger to verified deployment, with pre-check, backup, rollback and manual fallback", ymax=65)
    y1 = 55
    row1 = [("Trigger\nnew / renew / expiry /\nmanual request", "neutral"), ("Validate request\nand policy check", "sn"),
            ("Approval / change\n(if policy requires)", "sn"), ("Generate CSR\n(on target or vault;\nkey never on MID)", "vault"),
            ("Submit to CA\n(Sectigo / ACME / ADCS)", "ca"), ("Validation & issuance\n(DCV, CA processing)", "ca")]
    xs = [1.5, 17.5, 33.5, 49.5, 65.5, 81.5]
    for (t, k), x in zip(row1, xs):
        box(ax, x, y1 - 3.5, 15, 7, t, k, fs=8.2)
    for x in xs[:-1]:
        arrow(ax, (x + 15, y1), (x + 16.5, y1))
    y2 = 42
    box(ax, 81.5, y2 - 3.5, 15, 7, "Retrieve cert +\nchain, verify against\nCSR and policy", "ca", fs=8.2)
    arrow(ax, (89, y1 - 3.5), (89, y2 + 3.5))
    box(ax, 65.5, y2 - 3.5, 15, 7, "Adapter router:\nselect adapter by\ntechnology + zone", "sn", fs=8.2)
    arrow(ax, (81.5, y2), (80.5, y2))
    diamond(ax, 50, y2, 17, 9, "Adapter supports\nautomation?", fs=8.2)
    arrow(ax, (65.5, y2), (58.5, y2))
    box(ax, 22, y2 - 3.5, 16, 7, "Create manual task +\ninstructions + evidence\ncheck; notify owner", "warn", fs=8.0)
    arrow(ax, (41.5, y2), (38, y2))
    label(ax, 39.8, y2 + 1.7, "No", fs=8, bold=True)
    box(ax, 2, y2 - 3.5, 15, 7, "Owner completes;\nverification still\nautomated", "warn", fs=8.0)
    arrow(ax, (22, y2), (17, y2))
    y3 = 29
    label(ax, 51.8, y2 - 6.0, "Yes", fs=8, bold=True)
    arrow(ax, (50, y2 - 4.5), (50, y3 + 3.5))
    box(ax, 41.5, y3 - 3.5, 17, 7, "Pre-check: reachability,\npermissions, disk, dependency,\nchange window", "mid", fs=8.0)
    box(ax, 63, y3 - 3.5, 17, 7, "Backup current cert +\nconfig reference\n(rollback point)", "mid", fs=8.0)
    arrow(ax, (58.5, y3), (63, y3))
    box(ax, 84, y3 - 3.5, 14, 7, "Fetch JIT credential\nfrom vault; open\nsecure session", "vault", fs=8.0)
    arrow(ax, (80, y3), (84, y3))
    y4 = 15
    arrow(ax, (91, y3 - 3.5), (91, y4 + 3.5))
    box(ax, 82, y4 - 3.5, 17, 7, "Deploy (cluster-aware:\nnode by node, drain,\nreload / restart)", "mid", fs=8.0)
    box(ax, 61, y4 - 3.5, 17, 7, "Post-verify at live\nendpoint: SAN, chain,\nexpiry, thumbprint", "sn", fs=8.0)
    arrow(ax, (82, y4), (78, y4))
    diamond(ax, 47, y4, 16, 9, "Verified on\nall nodes + VIP?", fs=8.2)
    arrow(ax, (61, y4), (55, y4))
    box(ax, 12, y4 + 0.5, 18, 6.5, "Update inventory / CMDB,\nclose request, notify,\nscrub temp material", "ok", fs=8.0)
    arrow(ax, (40, y4 + 1.6), (30, y4 + 3.75))
    label(ax, 35.5, y4 + 4.6, "Yes", fs=8, bold=True)
    box(ax, 12, y4 - 7.5, 18, 6.5, "Roll back to backup,\nre-verify, raise incident,\nnotify owner + PKI admin", "bad", fs=8.0)
    arrow(ax, (40, y4 - 1.6), (30, y4 - 4.25))
    label(ax, 35.5, y4 - 4.6, "No", fs=8, bold=True)
    line(ax, [(9.5, y2 - 3.5), (9.5, 23.5), (69.5, 23.5), (69.5, y4 + 3.5)], color="#B58900", ls="--")
    label(ax, 30, 23.5, "manual path rejoins at post-verification", fs=7.8, color="#8a6d00")
    box(ax, 12, 2.0, 30, 4.6, "Next day: Discovery rescan sees the new thumbprint and
expiry in the CMDB, so CDM marks Confirmed (else alert)", "ok", fs=7.8, ls="--")
    ax.text(70, 4.0, "Every step writes an audit event. Transient errors are retried with back-off before rollback is triggered.",
            fontsize=8.6, ha="center", color=MUTED)
    save(fig, out)
