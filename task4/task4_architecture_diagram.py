"""
Task 4: System Architecture Diagram
Generates a comprehensive architecture diagram as a PNG/SVG using matplotlib.
Covers:
  - RabbitMQ message queue for task distribution
  - Horizontally-scalable worker nodes
  - SQL database with replica
  - Monitoring microservices (health, load, error logging)
  - Failover & recovery mechanisms
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe

# ── Colour palette ─────────────────────────────────────────────────────────
C = {
    "bg":        "#0F172A",   # dark navy background
    "panel":     "#1E293B",   # card background
    "border":    "#334155",   # card border
    "accent1":   "#38BDF8",   # light blue  – ingestion / API
    "accent2":   "#FB923C",   # orange      – RabbitMQ / queue
    "accent3":   "#4ADE80",   # green       – workers
    "accent4":   "#A78BFA",   # violet      – database
    "accent5":   "#F472B6",   # pink        – monitoring
    "accent6":   "#FACC15",   # yellow      – failover
    "text_main": "#F1F5F9",
    "text_sub":  "#94A3B8",
    "arrow":     "#64748B",
    "arrow_hl":  "#38BDF8",
}


def box(ax, x, y, w, h, color, label, sublabel="", radius=0.015, alpha=0.92):
    """Draw a rounded rectangle with a label."""
    rect = FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle=f"round,pad=0,rounding_size={radius}",
        linewidth=1.5, edgecolor=color, facecolor=C["panel"], alpha=alpha,
        zorder=3,
    )
    ax.add_patch(rect)
    ax.text(x, y + (0.01 if sublabel else 0), label,
            ha="center", va="center", fontsize=7.5, fontweight="bold",
            color=color, zorder=4)
    if sublabel:
        ax.text(x, y - 0.025, sublabel,
                ha="center", va="center", fontsize=5.5, color=C["text_sub"], zorder=4)


def arrow(ax, x1, y1, x2, y2, color=C["arrow"], style="->", lw=1.2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw),
                zorder=2)


def dashed_arrow(ax, x1, y1, x2, y2, color=C["arrow"]):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->", color=color, lw=1,
                                linestyle="dashed"),
                zorder=2)


def section_label(ax, x, y, text, color):
    ax.text(x, y, text, ha="center", va="center", fontsize=6,
            color=color, fontstyle="italic", alpha=0.7, zorder=4)


fig, ax = plt.subplots(figsize=(18, 11))
fig.patch.set_facecolor(C["bg"])
ax.set_facecolor(C["bg"])
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")

# ── Title ──────────────────────────────────────────────────────────────────
ax.text(0.5, 0.965, "Distributed Automation & Crawling — System Architecture",
        ha="center", va="center", fontsize=13, fontweight="bold",
        color=C["text_main"])
ax.text(0.5, 0.945, "Task Distribution • Horizontal Scaling • SQL • Monitoring • Failover",
        ha="center", va="center", fontsize=7.5, color=C["text_sub"])

# ════════════════════════════════════════════════════════════════════════════
# ROW 1 — Ingestion layer (Clients / API Gateway)
# ════════════════════════════════════════════════════════════════════════════
section_label(ax, 0.5, 0.905, "── INGESTION LAYER ──", C["accent1"])

clients = [("Web Client", 0.15), ("API Client", 0.35), ("Scheduler", 0.55), ("Webhook", 0.75)]
for label, cx in clients:
    box(ax, cx, 0.875, 0.12, 0.042, C["accent1"], label)

# API Gateway
box(ax, 0.5, 0.800, 0.55, 0.048, C["accent1"], "API Gateway / Load Balancer",
    "nginx / AWS ALB — TLS termination, rate-limiting, auth")

# arrows: clients → gateway
for _, cx in clients:
    arrow(ax, cx, 0.854, 0.5 + (cx - 0.5) * 0.4, 0.826, C["accent1"])

# ════════════════════════════════════════════════════════════════════════════
# ROW 2 — Message Queue (RabbitMQ)
# ════════════════════════════════════════════════════════════════════════════
section_label(ax, 0.5, 0.760, "── MESSAGE QUEUE LAYER ──", C["accent2"])

box(ax, 0.5, 0.730, 0.58, 0.048, C["accent2"], "RabbitMQ Cluster (Primary + Mirror)",
    "Exchanges: tasks.direct | tasks.topic | tasks.deadletter   |   Queues: crawl_queue · scrape_queue · retry_queue · dlq")
arrow(ax, 0.5, 0.776, 0.5, 0.756, C["accent1"])

# Queues shown individually
queues = [
    ("crawl_queue", 0.18), ("scrape_queue", 0.36),
    ("retry_queue", 0.54), ("dead_letter_q", 0.72),
]
for qlabel, qx in queues:
    box(ax, qx, 0.672, 0.14, 0.038, C["accent2"], qlabel)
    arrow(ax, qx, 0.706, qx, 0.693, C["accent2"])

# ════════════════════════════════════════════════════════════════════════════
# ROW 3 — Worker Pool (horizontal scaling)
# ════════════════════════════════════════════════════════════════════════════
section_label(ax, 0.5, 0.638, "── WORKER POOL (auto-scales 2 – 20 nodes) ──", C["accent3"])

workers = [
    ("Worker 1\nCrawler", 0.12),
    ("Worker 2\nCrawler", 0.27),
    ("Worker 3\nScraper", 0.42),
    ("Worker N\nScraper", 0.57),
    ("Worker N+1\nAutomation", 0.72),
    ("Worker N+2\nAutomation", 0.87),
]
for wlabel, wx in workers:
    box(ax, wx, 0.600, 0.13, 0.050, C["accent3"], wlabel)
    # connect from nearest queue
    nearest_q = min(queues, key=lambda q: abs(q[1] - wx))
    arrow(ax, nearest_q[1], 0.653, wx, 0.625, C["accent2"])

# "…" dots between workers 4 and 5
ax.text(0.645, 0.600, "· · ·", ha="center", va="center",
        fontsize=9, color=C["accent3"], zorder=4)

# ════════════════════════════════════════════════════════════════════════════
# ROW 4 — SQL Database (Primary + Replica + Cache)
# ════════════════════════════════════════════════════════════════════════════
section_label(ax, 0.28, 0.543, "── DATA LAYER ──", C["accent4"])

box(ax, 0.13, 0.510, 0.17, 0.048, C["accent4"], "PostgreSQL Primary",
    "Write master — ACID transactions")
box(ax, 0.32, 0.510, 0.17, 0.048, C["accent4"], "PostgreSQL Replica",
    "Read replica — async replication")
box(ax, 0.51, 0.510, 0.14, 0.048, C["accent4"], "Redis Cache",
    "Hot data / sessions")
box(ax, 0.68, 0.510, 0.14, 0.048, C["accent4"], "Object Store",
    "S3/MinIO — raw assets")

# Workers → DB
for wlabel, wx in workers:
    arrow(ax, wx, 0.575, 0.28, 0.536, C["accent3"], lw=0.8)

# Primary ↔ Replica
arrow(ax, 0.22, 0.510, 0.235, 0.510, C["accent4"])

# ════════════════════════════════════════════════════════════════════════════
# ROW 5 — Monitoring stack
# ════════════════════════════════════════════════════════════════════════════
section_label(ax, 0.5, 0.458, "── MONITORING & OBSERVABILITY STACK ──", C["accent5"])

mon = [
    ("Prometheus\n+ Grafana", "System Health\n& Dashboards", 0.13),
    ("Alertmanager\nPagerDuty", "Threshold Alerts\nOn-call routing", 0.30),
    ("ELK Stack\n(Elastic)", "Error Logging\n& Log Aggregation", 0.50),
    ("Jaeger /\nZipkin", "Distributed\nTracing", 0.68),
    ("Datadog\nAPM (opt.)", "Current Load\nProfiling", 0.86),
]
for label, sub, mx in mon:
    box(ax, mx, 0.420, 0.155, 0.062, C["accent5"], label, sub)

# Workers → Monitoring (metrics side-channel)
for wlabel, wx in workers[::2]:
    dashed_arrow(ax, wx, 0.575, 0.50, 0.452, C["accent5"])

# DB → Monitoring
dashed_arrow(ax, 0.22, 0.486, 0.50, 0.452, C["accent5"])

# ════════════════════════════════════════════════════════════════════════════
# ROW 6 — Failover & Recovery
# ════════════════════════════════════════════════════════════════════════════
section_label(ax, 0.5, 0.350, "── FAILOVER & RECOVERY MECHANISMS ──", C["accent6"])

fo = [
    ("RabbitMQ\nMirrored Queues", "Auto-failover on\nbroker crash", 0.13),
    ("DB Automatic\nFailover", "Patroni/pg_auto\nfailover", 0.31),
    ("Worker\nHealth Checks", "Kubernetes liveness\n& readiness probes", 0.50),
    ("Circuit\nBreaker", "Resilience4j /\nTenacity (Python)", 0.68),
    ("Dead Letter\nQueue + Retry", "Exponential back-off\nmax_retries=5", 0.87),
]
for label, sub, fx in fo:
    box(ax, fx, 0.305, 0.16, 0.062, C["accent6"], label, sub)

# Monitoring → Failover trigger arrows
for _, _, mx in mon[::2]:
    dashed_arrow(ax, mx, 0.389, 0.50, 0.337, C["accent6"])

# ════════════════════════════════════════════════════════════════════════════
# ROW 7 — Results / Delivery layer
# ════════════════════════════════════════════════════════════════════════════
section_label(ax, 0.5, 0.250, "── RESULTS & DELIVERY ──", C["accent1"])

box(ax, 0.5, 0.215, 0.58, 0.048, C["accent1"],
    "Results API / Webhook Dispatcher / Export Service",
    "REST · WebSocket · CSV/JSON export · Email notifications")

arrow(ax, 0.5, 0.282, 0.5, 0.239, C["accent1"])

# Downstream consumers
consumers = [("Dashboard\nUI", 0.20), ("Third-party\nWebhook", 0.38),
             ("Data\nWarehouse", 0.56), ("Client\nCallback", 0.74)]
for label, cx in consumers:
    box(ax, cx, 0.160, 0.14, 0.042, C["accent1"], label)
    arrow(ax, cx, 0.191, cx, 0.182, C["accent1"])

# ── Legend ─────────────────────────────────────────────────────────────────
legend_items = [
    (C["accent1"], "Ingestion / API / Delivery"),
    (C["accent2"], "Message Queue (RabbitMQ)"),
    (C["accent3"], "Worker Nodes"),
    (C["accent4"], "Data Layer (SQL + Cache)"),
    (C["accent5"], "Monitoring & Observability"),
    (C["accent6"], "Failover & Recovery"),
]
handles = [mpatches.Patch(facecolor=c, label=l) for c, l in legend_items]
legend = ax.legend(
    handles=handles, loc="lower center",
    ncol=6, bbox_to_anchor=(0.5, 0.01),
    fontsize=6.2, framealpha=0.15,
    labelcolor=C["text_main"],
    facecolor=C["panel"], edgecolor=C["border"],
)

plt.tight_layout(pad=0.3)
plt.savefig("architecture_diagram.png", dpi=180, bbox_inches="tight",
            facecolor=C["bg"])
plt.savefig("architecture_diagram.svg", format="svg", bbox_inches="tight",
            facecolor=C["bg"])
print("✅ Diagrams saved: architecture_diagram.png  &  architecture_diagram.svg")
