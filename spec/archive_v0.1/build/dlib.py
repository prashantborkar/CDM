"""Small drawing helpers for the CDM specification diagrams (matplotlib only)."""
import textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, FancyArrowPatch, Rectangle

FONT = "Segoe UI"
plt.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans"]

# name: (fill, edge)
PAL = {
    "sn":     ("#E4F5E6", "#2E7D32"),   # ServiceNow / orchestration
    "ca":     ("#F1E6FA", "#7B1FA2"),   # certificate authorities
    "vault":  ("#FFF1D6", "#E65100"),   # secrets / keys
    "mid":    ("#E1EEFC", "#1565C0"),   # MID / execution
    "tgt":    ("#EEF1F3", "#455A64"),   # targets
    "bad":    ("#FDE7E5", "#C62828"),   # risk / failure / gap
    "ok":     ("#E4F5E6", "#2E7D32"),
    "warn":   ("#FFF4CC", "#B58900"),
    "neutral": ("#FFFFFF", "#607D8B"),
    "title":  ("#1F2D3D", "#1F2D3D"),
}
INK = "#1F2D3D"
MUTED = "#5F6B7A"


def canvas(w, h, title, subtitle=None, xmax=100, ymax=None):
    ymax = ymax or 100 * h / w
    fig, ax = plt.subplots(figsize=(w, h), dpi=150)
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, xmax)
    ax.set_ylim(0, ymax)
    ax.axis("off")
    ax.text(1.2, ymax - 1.6, title, fontsize=19, fontweight="bold", color=INK, va="top", ha="left")
    if subtitle:
        ax.text(1.2, ymax - 4.6, subtitle, fontsize=10.5, color=MUTED, va="top", ha="left")
    fig.subplots_adjust(left=0.005, right=0.995, top=0.995, bottom=0.005)
    return fig, ax


def box(ax, x, y, w, h, text="", kind="neutral", fs=9.5, bold=False, wrap=None,
        align="center", rounding=0.6, lw=1.4, ls="-", color=None, z=3):
    fc, ec = PAL[kind]
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={rounding}",
                       fc=fc, ec=ec, lw=lw, ls=ls, zorder=z)
    ax.add_patch(p)
    if text:
        if wrap:
            text = "\n".join(textwrap.fill(t, wrap) for t in text.split("\n"))
        tx = x + w / 2 if align == "center" else x + 1.0
        ax.text(tx, y + h / 2, text, ha=align, va="center", fontsize=fs,
                fontweight="bold" if bold else "normal", color=color or INK, zorder=z + 1,
                linespacing=1.25)
    return p


def group(ax, x, y, w, h, title, kind="neutral", fs=10.5, ls="--"):
    fc, ec = PAL[kind]
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.9",
                       fc=fc, ec=ec, lw=1.6, ls=ls, alpha=0.35, zorder=1)
    ax.add_patch(p)
    p2 = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.9",
                        fc="none", ec=ec, lw=1.6, ls=ls, zorder=2)
    ax.add_patch(p2)
    ax.text(x + 1.0, y + h - 0.8, title, fontsize=fs, fontweight="bold", color=ec,
            va="top", ha="left", zorder=4)


def diamond(ax, cx, cy, w, h, text, kind="warn", fs=9):
    fc, ec = PAL[kind]
    pts = [(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)]
    ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=ec, lw=1.4, zorder=3))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, color=INK, zorder=4, linespacing=1.2)


def arrow(ax, p1, p2, label=None, kind="neutral", lw=1.5, ls="-", rad=0.0, fs=8.2,
          lpos=0.5, loff=(0, 0), both=False, lbg=True, color=None):
    ec = color or PAL[kind][1]
    if kind == "neutral" and not color:
        ec = "#37474F"
    style = "<|-|>" if both else "-|>"
    a = FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=13, lw=lw, ls=ls,
                        color=ec, connectionstyle=f"arc3,rad={rad}", zorder=5,
                        shrinkA=0, shrinkB=0)
    ax.add_patch(a)
    if label:
        mx = p1[0] + (p2[0] - p1[0]) * lpos + loff[0]
        my = p1[1] + (p2[1] - p1[1]) * lpos + loff[1]
        ax.text(mx, my, label, fontsize=fs, ha="center", va="center", color=INK, zorder=6,
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.92) if lbg else None,
                linespacing=1.15)


def line(ax, pts, kind="neutral", lw=1.5, ls="-", color=None, arrow_end=True, z=5):
    """Poly-line with optional arrow head on last segment."""
    ec = color or ("#37474F" if kind == "neutral" else PAL[kind][1])
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    if len(pts) > 2:
        ax.plot(xs[:-1], ys[:-1], color=ec, lw=lw, ls=ls, zorder=z, solid_capstyle="round")
    a = FancyArrowPatch(pts[-2], pts[-1], arrowstyle="-|>" if arrow_end else "-",
                        mutation_scale=13, lw=lw, ls=ls, color=ec, zorder=z, shrinkA=0, shrinkB=0)
    ax.add_patch(a)


def label(ax, x, y, text, fs=8.5, color=INK, ha="center", bold=False, bg=True, rot=0):
    ax.text(x, y, text, fontsize=fs, ha=ha, va="center", color=color, zorder=7,
            fontweight="bold" if bold else "normal", rotation=rot, linespacing=1.2,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.9) if bg else None)


def badge(ax, x, y, n, kind="title", r=1.15, fs=8.5):
    fc, ec = PAL[kind]
    ax.add_patch(plt.Circle((x, y), r, fc=ec, ec="white", lw=1.2, zorder=8))
    ax.text(x, y, str(n), color="white", fontsize=fs, fontweight="bold", ha="center",
            va="center", zorder=9)


def save(fig, path):
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)
