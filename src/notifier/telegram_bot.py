"""TelegramNotifier — kirim alert anomaly ke Telegram, sesuai Spec 07.

Jika TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID tidak diset, notifier berjalan
dalam mode "disabled": alert tetap dicatat (opsional) tapi tidak benar-benar
mengirim HTTP request ke Telegram — supaya prototipe tetap jalan tanpa bot
Telegram sungguhan saat development/testing.
"""
import logging
import time
from typing import Optional

import requests

from .aggregator import NotificationAggregator

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Send notifications to Telegram."""

    BASE_URL = "https://api.telegram.org/bot{token}"

    def __init__(
        self,
        bot_token: str = "",
        chat_id: str = "",
        aggregator: Optional[NotificationAggregator] = None,
        notify_on_block_only: bool = True,
    ):
        self.bot_token = bot_token or ""
        self.chat_id = chat_id or ""
        self.base_url = self.BASE_URL.format(token=self.bot_token) if self.bot_token else ""
        self.aggregator = aggregator or NotificationAggregator()
        self.notify_on_block_only = notify_on_block_only
        self.session = requests.Session()

    @property
    def enabled(self) -> bool:
        """Notifier hanya benar-benar mengirim jika token & chat_id sudah diset."""
        return bool(self.bot_token and self.chat_id)

    def notify(
        self,
        label: str,
        confidence: float,
        attack_class: Optional[str],
        source_ip: str,
        url: str,
        method: str,
        action: str,
    ) -> tuple:
        """Send notification for an anomalous traffic event.

        Mengikuti flow Spec 07: hanya request `anomalous` yang dipertimbangkan;
        default `notify_on_block_only=True` berarti hanya action == 'block'
        yang benar-benar memicu notifikasi (flag hanya dicatat, tidak notify).

        Returns:
            (sent: bool, message: str) — message kosong jika tidak ada yang
            dikirim (mis. ditekan rate limiter, atau bukan kandidat notifikasi).
        """
        if label != "anomalous":
            return False, ""

        if self.notify_on_block_only and action != "block":
            logger.debug("Notification skipped: action=%s (notify_on_block_only)", action)
            return False, ""

        alert_data = {
            "timestamp": time.time(),
            "label": label,
            "confidence": confidence,
            "attack_class": attack_class,
            "source_ip": source_ip,
            "url": url,
            "method": method,
            "action": action,
        }

        if not self.aggregator.should_notify(alert_data):
            logger.debug("Notification suppressed by rate limiter")
            return False, ""

        message, count = self.aggregator.get_aggregated_message()
        if not message:
            return False, ""

        if not self.enabled:
            # Mode disabled (belum ada bot token/chat id) — log saja, jangan panggil API.
            logger.info(
                "[TELEGRAM DISABLED] Would send (%d event(s)):\n%s", count, message
            )
            self.aggregator.record_sent()
            return False, message

        success = self._send_message(message)
        if success:
            self.aggregator.record_sent()
            logger.info("Notification sent (%d events)", count)
        else:
            logger.error("Failed to send notification")
        return success, message

    def _send_message(self, text: str) -> bool:
        """Send message to Telegram with retry logic."""
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }

        for attempt in range(3):
            try:
                response = self.session.post(url, json=payload, timeout=10)

                if response.status_code == 200:
                    return True

                if response.status_code == 429:
                    retry_after = int(
                        response.json().get("parameters", {}).get("retry_after", 5)
                    )
                    logger.warning("Telegram rate limited. Retry after %ss", retry_after)
                    time.sleep(retry_after)
                    continue

                logger.error("Telegram API error: %s", response.status_code)
                return False

            except requests.Timeout:
                logger.warning("Request timeout (attempt %d)", attempt + 1)
                time.sleep(5)
                continue
            except requests.ConnectionError:
                logger.error("Connection error to Telegram API")
                return False

        return False
