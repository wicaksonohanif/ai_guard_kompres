"""NotificationAggregator — rate-limiting & burst aggregation, sesuai Spec 07."""
import time

from .templates import format_single_alert, format_aggregated_alert

DEFAULT_CONFIG = {
    "aggregation_window_seconds": 60,
    "max_notifications_per_hour": 20,
    "min_interval_seconds": 30,
}


class NotificationAggregator:
    """Aggregate and rate-limit notification sends."""

    def __init__(self, config: dict = None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.alert_buffer = []  # Store alerts during aggregation window
        self.last_send_time = 0.0
        self.hourly_count = 0
        self.hourly_reset_time = time.time()

    def should_notify(self, alert_data: dict) -> bool:
        """Determine if a notification should be sent now."""
        now = time.time()

        # Reset hourly cap window
        if now >= self.hourly_reset_time + 3600:
            self.hourly_count = 0
            self.hourly_reset_time = now

        if self.hourly_count >= self.config["max_notifications_per_hour"]:
            return False

        # Add to buffer
        self.alert_buffer.append(alert_data)

        # Clear old entries outside aggregation window
        window_start = now - self.config["aggregation_window_seconds"]
        self.alert_buffer = [a for a in self.alert_buffer if a["timestamp"] >= window_start]

        buffer_size = len(self.alert_buffer)
        min_interval_elapsed = (now - self.last_send_time) >= self.config["min_interval_seconds"]

        if buffer_size >= 1 and min_interval_elapsed:
            self.last_send_time = now
            return True

        return False

    def get_aggregated_message(self) -> tuple:
        """Generate aggregated notification message and count. Clears buffer."""
        alerts = self.alert_buffer.copy()
        self.alert_buffer.clear()

        if not alerts:
            return "", 0

        if len(alerts) == 1:
            return format_single_alert(alerts[0]), 1

        return format_aggregated_alert(alerts), len(alerts)

    def record_sent(self):
        """Record that a notification was sent (for hourly cap tracking)."""
        self.hourly_count += 1
