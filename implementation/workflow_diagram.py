"""Renders the CDM agent-loop workflow as a single shareable PNG image -- same content and layout
as the artifact page, redrawn with matplotlib so it exists as a real file, not just a hosted link.

Run:  python workflow_diagram.py
Output: workflow_diagram.png (next to this script)
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, FancyArrowPatch
from matplotlib.path import Path
import matplotlib.patches as mpatches

INK = "#17212B"
MUTED = "#5B6672"
ACCENT = "#2454A6"
ACCENT_SOFT = "#E4ECF9"
GOOD = "#1F8A4C"
GOOD_SOFT = "#E4F3EA"
WARN = "#B7791F"
WARN_SOFT = "#FBF0DD"
SURFACE = "#FFFFFF"
LINE = "#C7CED8"

plt.rcParams["font.family"] = ["DejaVu Sans"]

fig, ax = plt.subplots(figsize=(15, 10), dpi=200)
fig.patch.set_facecolor("#F6F7FA")
ax.set_xlim(0, 1100)
ax.set_ylim(0, 720)
ax.axis("off")
ax.invert_yaxis()  # so y grows downward, matching the SVG layout coordinates directly


def box(x, y, w, h, title, lines, fc, ec, title_size=15, line_size=11):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=14",
                                 fc=fc, ec=ec, lw=1.8, zorder=3))
    cx = x + w / 2
    ax.text(cx, y + 30, title, ha="center", va="center", fontsize=title_size, fontweight="bold",
            color=INK, zorder=4)
    for i, (txt, color) in enumerate(lines):
        ax.text(cx, y + 55 + i * 19, txt, ha="center", va="center", fontsize=line_size,
                color=color, zorder=4)


def arrow(p1, p2, color, lw=2.2, style="-", dash=None):
    a = FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=16, lw=lw,
                        color=color, linestyle=style, zorder=2, shrinkA=0, shrinkB=0,
                        connectionstyle="arc3,rad=0")
    if dash:
        a.set_linestyle((0, dash))
    ax.add_patch(a)


def label(x, y, text, color, size=12, weight="normal", rotation=0, ha="center"):
    ax.text(x, y, text, ha=ha, va="center", fontsize=size, color=color,
            fontweight=weight, rotation=rotation, zorder=5)


# ---------------------------------------------------------------- title
fig.text(0.5, 0.975, "CERTIFICATE DEPLOYMENT MANAGER", ha="center", va="top", fontsize=11,
         color=ACCENT, fontweight="bold", family="monospace")
fig.text(0.5, 0.945, "The AI agent that keeps certificates from expiring", ha="center", va="top",
         fontsize=19, color=INK, fontweight="bold")
fig.text(0.5, 0.898, "One picture of the whole loop: two systems that each know half the story,\n"
                     "an AI agent that decides what to do about it, and independent proof it actually worked.",
         ha="center", va="top", fontsize=10.5, color=MUTED, linespacing=1.7)

# ---------------------------------------------------------------- closing loop (drawn first, behind nodes)
loop_x = [930, 930, 175, 175]
loop_y = [585, 625, 625, 205]
for i in range(len(loop_x) - 1):
    style = "-|>" if i == len(loop_x) - 2 else "-"
    a = FancyArrowPatch((loop_x[i], loop_y[i]), (loop_x[i + 1], loop_y[i + 1]),
                        arrowstyle=style, mutation_scale=16, lw=2.3, color=GOOD, zorder=1,
                        shrinkA=0, shrinkB=0)
    ax.add_patch(a)
label(552, 618, 'next day: ServiceNow re-scans the server on its own', GOOD, size=11.5, weight="bold")
label(552, 636, 'sees the new certificate -> marks it "Confirmed" -- independent proof, not a self-report',
      GOOD, size=11.5, weight="bold")

# ---------------------------------------------------------------- ServiceNow node
box(60, 70, 230, 88, "ServiceNow",
    [("knows WHERE + WHEN", MUTED), ("location, thumbprint, expiry date", MUTED)],
    ACCENT_SOFT, ACCENT)

# ---------------------------------------------------------------- Certificate source node
box(810, 70, 230, 88, "Certificate source",
    [("knows WHAT is ready", MUTED), ("the new certificate, issued", MUTED)],
    ACCENT_SOFT, ACCENT)

# ---------------------------------------------------------------- arrows into Agent
arrow((200, 158), (470, 275), INK, lw=1.8)
label(300, 205, "reads location + expiry", MUTED, size=11, rotation=-28)
arrow((900, 158), (632, 275), INK, lw=1.8)
label(760, 205, "checks what's available", MUTED, size=11, rotation=28, ha="right")

# ---------------------------------------------------------------- AI Agent hub
ax.add_patch(Circle((550, 330), 92, fc=ACCENT, ec="none", zorder=3))
label(550, 300, "AI AGENT", "#EAF1FC", size=14, weight="bold")
label(550, 330, "matches by real identity", "#CFE0F7", size=10.5)
label(550, 352, "-- never by name alone --", "#CFE0F7", size=10.5)
label(550, 374, "and decides what to do", "#B9D1F2", size=10)

# ---------------------------------------------------------------- Agent -> Servers (deploy path)
arrow((636, 355), (812, 465), ACCENT, lw=2.6)
label(745, 452, "unique match\n-> deploy", ACCENT, size=11, weight="bold", rotation=-31)

# ---------------------------------------------------------------- Agent -> Person (escalate path)
arrow((464, 355), (288, 465), WARN, lw=2.6, dash=(6, 5))
label(355, 452, "ambiguous /\nno approved plan", WARN, size=11, weight="bold", rotation=31)

# ---------------------------------------------------------------- Person notified node
box(60, 470, 230, 110, "A person is notified",
    [("the agent never guesses --", MUTED), ("it hands over anything", MUTED), ("it isn't certain about", MUTED)],
    WARN_SOFT, WARN)

# ---------------------------------------------------------------- Real server node
box(810, 450, 230, 135, "The real server",
    [("Windows | Linux | Java", MUTED)],
    SURFACE, ACCENT, line_size=10.5)
ax.plot([835, 1015], [512, 512], color=LINE, lw=1, zorder=4)
label(925, 531, "install -> activate -> verify live", INK, size=11)
label(925, 551, "OK matches -> kept", GOOD, size=10.5, weight="bold")
label(925, 569, "X mismatch -> auto-undone", WARN, size=10.5, weight="bold")

# small self-loop marking automatic rollback
loop = FancyArrowPatch((1040, 545), (1042, 575), connectionstyle="arc3,rad=1.3",
                       arrowstyle="-|>", mutation_scale=14, lw=1.8, color=WARN, linestyle=(0, (4, 4)), zorder=4)
ax.add_patch(loop)

# ---------------------------------------------------------------- caption + proof strip
fig.text(0.5, 0.055,
         "The one guarantee that never depends on the AI's judgment: whatever the agent decides to deploy, the\n"
         "system checks the live server afterward -- and if it doesn't match, it undoes the change automatically,\n"
         "every time. The agent chooses WHAT to act on; it never gets to skip the safety check.",
         ha="center", fontsize=10.5, color=MUTED)

pills = ["Proven on Windows", "Proven on Linux", "Proven on Java", "Confirmed independently by ServiceNow"]
n = len(pills)
total_w = 0.86
start_x = (1 - total_w) / 2
step = total_w / n
for i, p in enumerate(pills):
    cx = start_x + step * i + step / 2
    fig.text(cx, 0.018, p, ha="center", fontsize=9.5, color=GOOD, fontweight="bold",
             bbox=dict(boxstyle="round,pad=0.4", fc=GOOD_SOFT, ec=GOOD, lw=1))

fig.subplots_adjust(left=0.01, right=0.99, top=0.80, bottom=0.09)
fig.savefig("workflow_diagram.png", facecolor=fig.get_facecolor())
print("saved workflow_diagram.png")
