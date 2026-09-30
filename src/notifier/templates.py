"""Message templates untuk Telegram alert — sesuai specs/07-notifications.md."""
from collections import Counter
from datetime import datetime, timezone


def _fmt_time(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def format_single_alert(alert: dict) -> str:
    """Format satu alert anomalous menjadi pesan Telegram."""
    confidence_pct = round(float(alert.get("confidence", 0.0)) * 100)
    action_label = {"block": "Blocked", "flag": "Flagged"}.get(
        alert.get("action", ""), alert.get("action", "-")
    )
    return (
        "🚨 AI Guard Alert - Anomalous Traffic Detected\n\n"
        f"⏰ Time: {alert.get('timestamp_str') or _fmt_time(alert['timestamp'])}\n"
        f"🌐 Source IP: {alert.get('source_ip') or 'unknown'}\n"
        f"📡 Endpoint: {alert.get('method', '')} {alert.get('url', '')}\n"
        f"🔍 Attack Type: {alert.get('attack_class') or 'unknown'}\n"
        f"📊 Confidence: {confidence_pct}%\n"
        f"⚡ Action Taken: {action_label}\n\n"
        "-- AI Guard System"
    )


def format_aggregated_alert(alerts: list) -> str:
    """Format beberapa alert (burst) dalam satu window menjadi satu pesan."""
    n = len(alerts)
    timestamps = [a["timestamp"] for a in alerts]
    first_seen = _fmt_time(min(timestamps))
    last_seen = _fmt_time(max(timestamps))
    unique_ips = {a.get("source_ip") for a in alerts if a.get("source_ip")}

    attack_counter = Counter(a.get("attack_class") or "unknown" for a in alerts)
    breakdown_lines = "\n".join(
        f"   - {attack}: {count} event{'s' if count != 1 else ''}"
        for attack, count in attack_counter.most_common()
    )

    endpoint_counter = Counter(a.get("url", "") for a in alerts)
    top_endpoint, top_count = endpoint_counter.most_common(1)[0]

    return (
        f"🚨 AI Guard Alert - Multiple Anomalous Traffic ({n} events in a burst)\n\n"
        f"⏰ First seen: {first_seen}\n"
        f"🔚 Last seen:  {last_seen}\n"
        f"👥 Unique IPs: {len(unique_ips)}\n"
        f"📊 Breakdown:\n{breakdown_lines}\n"
        f"🎯 Most Targeted: {top_endpoint} ({top_count} events)\n\n"
        "⚠️ Some notifications suppressed due to rate limiting.\n\n"
        "-- AI Guard System"
    )
