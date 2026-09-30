"""
admin.py — Dashboard admin: pantau traffic AI Guard secara real-time.

Route:
  (login admin lewat halaman /login yang sama dengan mahasiswa — lihat check_admin)
  /admin/                       halaman dashboard
  /admin/api/stats?window=300   JSON ringkasan (di-poll tiap 2 detik oleh dashboard)

Konfigurasi (.env):
  ADMIN_USERNAME=admin
  ADMIN_PASSWORD_HASH=<hasil: python -c "from werkzeug.security import generate_password_hash as g; print(g('passwordmu'))">
"""
import os
import hmac
import functools
import time
from collections import Counter

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from src.database.connection import get_db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

ACTIONS = ("allow", "flag", "block")
BUCKETS = 60

ATTACK_LABELS = {
    "sql_injection": "SQL Injection",
    "xss": "XSS",
    "path_traversal": "Path Traversal",
    "crlf_injection": "CRLF Injection",
    "command_injection": "Command Injection",
    "file_inclusion": "File Inclusion",
    "unknown_anomaly": "Anomali Tidak Teridentifikasi",
}


def detection_info(label, action, attack_class):
    """Return dashboard-friendly security classification.

    Authentication results such as invalid_username are deliberately kept
    separate from attack classification. The attack type comes from the
    traffic log produced by the AI Guard inference pipeline.
    """
    if label == "anomalous":
        detection = "Anomali Terdeteksi"
        severity = "Tinggi" if action == "block" else "Sedang"
        attack = ATTACK_LABELS.get(attack_class or "", "Anomali Tidak Teridentifikasi")
        reasons = {
            "sql_injection": "Pola SQL berisiko terdeteksi pada request.",
            "xss": "Pola script/HTML injection terdeteksi pada request.",
            "path_traversal": "Pola path traversal terdeteksi pada request.",
            "crlf_injection": "Pola CRLF/header injection terdeteksi pada request.",
            "command_injection": "Pola command injection terdeteksi pada request.",
            "file_inclusion": "Pola file inclusion terdeteksi pada request.",
            "unknown_anomaly": "Model mendeteksi request tidak normal tanpa signature serangan spesifik.",
        }
        reason = reasons.get(attack_class or "", reasons["unknown_anomaly"])
        return detection, attack, severity, reason

    return "Normal", "—", "Rendah", "Tidak ada indikator serangan yang terdeteksi."


def check_admin(username, password):
    """Dipakai oleh /login (app.py): True kalau kredensial cocok dengan akun admin di .env."""
    pw_hash = os.getenv("ADMIN_PASSWORD_HASH", "")
    return bool(pw_hash) \
        and hmac.compare_digest(username or "", os.getenv("ADMIN_USERNAME", "admin")) \
        and check_password_hash(pw_hash, password or "")


def admin_required(view):
    @functools.wraps(view)
    def wrapped(*a, **kw):
        if not session.get("is_admin"):
            if request.path.startswith("/admin/api/"):
                return jsonify(error="unauthorized"), 401
            return redirect(url_for("login"))
        return view(*a, **kw)

    return wrapped


@admin_bp.route("/")
@admin_required
def index():
    return render_template("admin_dashboard.html")


@admin_bp.route("/api/stats")
@admin_required
def stats():
    window = min(max(request.args.get("window", 300, type=int), 60), 3600)
    now = int(time.time())  # timestamp di DB = CURRENT_TIMESTAMP (UTC), sama dengan epoch ini
    start = now - window
    size = window / BUCKETS
    span = (f"-{window} seconds",)
    ts = "CAST(strftime('%s', timestamp) AS INTEGER)"

    with get_db() as conn:
        # Request ke /admin tidak ikut dihitung (supaya polling dashboard tidak mengotori data)
        rows = [dict(r) for r in conn.execute(
            f"SELECT {ts} AS t, source_ip AS ip, method, url AS path, label, action, attack_class AS attack, "
            "confidence AS conf, inference_latency_ms AS lat FROM traffic_logs "
            "WHERE timestamp >= datetime('now', ?) AND url NOT LIKE '/admin%' ORDER BY id DESC LIMIT 20000", span)]
        logins = [dict(r) for r in conn.execute(
            f"SELECT {ts.replace('timestamp', 'l.timestamp')} AS t, l.username, l.source_ip AS ip, l.result, "
            "t.label, t.action, t.attack_class AS attack, t.confidence AS conf "
            "FROM login_attempts l LEFT JOIN traffic_logs t ON t.id = l.traffic_log_id "
            "ORDER BY l.id DESC LIMIT 8")]
        lc = dict(conn.execute(
            "SELECT result, COUNT(*) FROM login_attempts WHERE timestamp >= datetime('now', ?) GROUP BY result",
            span).fetchall())

    buckets = [{a: 0 for a in ACTIONS} for _ in range(BUCKETS)]
    counts, attacks, ips, paths, lats = Counter(), Counter(), Counter(), Counter(), []
    for r in rows:
        act = r["action"] if r["action"] in ACTIONS else "allow"
        counts[act] += 1
        buckets[min(BUCKETS - 1, max(0, int((r["t"] - start) / size)))][act] += 1
        ips[r["ip"] or "?"] += 1
        paths[(r["path"] or "?").split("?")[0]] += 1
        if act != "allow" and r["attack"]:
            attacks[r["attack"]] += 1
        if r["lat"] is not None:
            lats.append(r["lat"])

    total = len(rows)
    enriched_recent = []
    for r in rows[:25]:
        detection, attack, severity, reason = detection_info(r.get("label"), r.get("action"), r.get("attack"))
        enriched_recent.append({
            **r,
            "conf": round(r["conf"], 2),
            "detection": detection,
            "attack_label": attack,
            "severity": severity,
            "reason": reason,
        })

    enriched_logins = []
    for l in logins:
        detection, attack, severity, reason = detection_info(l.get("label"), l.get("action"), l.get("attack"))
        enriched_logins.append({
            **l,
            "conf": round(l["conf"], 2) if l.get("conf") is not None else None,
            "detection": detection,
            "attack_label": attack,
            "severity": severity,
            "reason": reason,
        })

    return jsonify(
        window=window, total=total, rps=round(total / window, 2), unique_ips=len(ips),
        allow=counts["allow"], flag=counts["flag"], block=counts["block"],
        attacks_detected=sum(1 for r in rows if r.get("label") == "anomalous"),
        block_rate=round(100 * counts["block"] / total, 1) if total else 0,
        avg_lat=round(sum(lats) / len(lats), 1) if lats else 0,
        buckets=buckets, recent=enriched_recent,
        top_ips=ips.most_common(5), top_paths=paths.most_common(5), attacks=attacks.most_common(5),
        logins=enriched_logins, login_ok=lc.get("success", 0),
        login_fail=lc.get("invalid_username", 0) + lc.get("invalid_password", 0),
    )
