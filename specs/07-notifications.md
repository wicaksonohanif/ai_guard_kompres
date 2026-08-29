# Spec 07: Telegram Notifications

**Version**: 1.0
**Date**: 29 Agustus 2026
**Related PRD**: FR-7

---

## Tujuan

Mengirim notifikasi otomatis ke Telegram Bot saat traffic anomalous terdeteksi, dengan mekanisme agregasi/rate-limiting untuk mencegah spam saat burst serangan.

---

## Flow Notifikasi

```
Middleware detects anomalous traffic
            │
            ▼
    ┌───────────────┐
    │ Is >= block   │
    │ threshold?    │
    └───────────────┘
       Yes     │     No
        │      │      │
        ▼      ▼      ▼
   Check     Log     Continue
   rate       only    processing
   limit
        │
   ┌──────────┐
   │ Within   │
   │ limit?   │
   └──────────┘
     Yes  │   No
      │    │    │
      ▼    ▼    ▼
 Send   Queue  Suppress
 notify  for   immediately
 next
 window
```

---

## Telegram Bot Setup

### Langkah Setup

1. Buka @BotFather di Telegram
2. Kirim `/newbot` dan ikuti instruksi
3. Simpan `BOT_TOKEN` dari respons
4. Dapatkan chat ID:
   - Kirim pesan ke bot
   - Akses `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates`
   - Extract `message.chat.id` dari respons

### Environment Variables

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=-1001234567890
```

---

## Notification Message Format

### Single Alert

```
🚨 AI Guard Alert - Anomalous Traffic Detected

⏰ Time: 2026-08-29 14:23:45
🌐 Source IP: 192.168.1.100
📡 Endpoint: POST /api/login
🔍 Attack Type: SQL Injection
📊 Confidence: 97%
⚡ Action Taken: Blocked

-- AI Guard System
```

### Aggregated Alert (Burst)

```
🚨 AI Guard Alert - Multiple Anomalous Traffic (5 events in 60s)

⏰ First seen: 2026-08-29 14:20:00
🔚 Last seen:  2026-08-29 14:21:00
👥 Unique IPs: 3
📊 Breakdown:
   - SQL Injection: 2 events
   - XSS: 1 event
   - CRLF Injection: 2 events
🎯 Most Targeted: /api/login (3 events)

⚠️ Some notifications suppressed due to rate limiting.

-- AI Guard System
```

---

## Rate Limiting Strategy

### Configuration

```python
NOTIFICATION_CONFIG = {
    # Enable/disable notifications
    "enabled": True,
    
    # Rate limiting
    "aggregation_window_seconds": 60,     # Group alerts within this window
    "max_notifications_per_hour": 20,      # Hard cap per hour
    "min_interval_seconds": 30,            # Min time between individual alerts
    
    # Only notify on blocked traffic (not flagged)
    "notify_on_block_only": True,
    
    # Retry settings
    "retry_attempts": 3,
    "retry_delay_seconds": 5
}
```

### Aggregation Logic

```python
import time
from collections import defaultdict

class NotificationAggregator:
    """Aggregate and rate-limit notification sends."""
    
    def __init__(self, config: dict):
        self.config = config
        self.alert_buffer = []  # Store alerts during aggregation window
        self.last_send_time = 0
        self.hourly_count = 0
        self.hourly_reset_time = time.time()
    
    def should_notify(self, alert_data: dict) -> bool:
        """Determine if a notification should be sent now."""
        now = time.time()
        
        # Check hourly cap
        if now >= self.hourly_reset_time + 3600:
            self.hourly_count = 0
            self.hourly_reset_time = now
        
        if self.hourly_count >= self.config['max_notifications_per_hour']:
            return False
        
        # Add to buffer
        self.alert_buffer.append(alert_data)
        
        # Clear old entries outside aggregation window
        window_start = now - self.config['aggregation_window_seconds']
        self.alert_buffer = [
            a for a in self.alert_buffer 
            if a['timestamp'] >= window_start
        ]
        
        # Determine if we should send
        buffer_size = len(self.alert_buffer)
        min_interval_elapsed = (now - self.last_send_time) >= self.config['min_interval_seconds']
        
        if buffer_size >= 1 and min_interval_elapsed:
            self.last_send_time = now
            return True
        
        return False
    
    def get_aggregated_message(self) -> tuple[str, int]:
        """Generate aggregated notification message and count."""
        alerts = self.alert_buffer.copy()
        self.alert_buffer.clear()
        
        if len(alerts) == 1:
            msg = self._format_single_alert(alerts[0])
            return msg, 1
        
        msg = self._format_aggregated_alert(alerts)
        return msg, len(alerts)
    
    def record_sent(self):
        """Record that a notification was sent."""
        self.hourly_count += 1
```

---

## Telegram Bot Service

### Lokasi File

```
src/
├── notifier/
│   ├── __init__.py
│   ├── telegram_bot.py        # Telegram Bot service
│   ├── aggregator.py          # Rate limiting & aggregation
│   └── templates.py           # Message templates
```

### Telegram Bot Implementation

```python
import logging
import requests
from typing import Optional
from .aggregator import NotificationAggregator
from .templates import format_single_alert, format_aggregated_alert

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Send notifications to Telegram."""
    
    BASE_URL = "https://api.telegram.org/bot{token}"
    
    def __init__(self, bot_token: str, chat_id: str, aggregator: NotificationAggregator):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = self.BASE_URL.format(token=bot_token)
        self.aggregator = aggregator
        self.session = requests.Session()
    
    def notify(
        self,
        label: str,
        confidence: float,
        attack_class: Optional[str],
        source_ip: str,
        url: str,
        method: str,
        timestamp: str,
        action: str
    ) -> bool:
        """Send notification for an anomalous traffic event."""
        
        # Prepare alert data
        alert_data = {
            'label': label,
            'confidence': confidence,
            'attack_class': attack_class,
            'source_ip': source_ip,
            'url': url,
            'method': method,
            'timestamp': timestamp,
            'action': action
        }
        
        # Check if we should send
        if not self.aggregator.should_notify(alert_data):
            logger.debug("Notification suppressed by rate limiter")
            return False
        
        # Get formatted message
        message, count = self.aggregator.get_aggregated_message()
        
        # Send to Telegram
        success = self._send_message(message)
        
        if success:
            self.aggregator.record_sent()
            logger.info(f"Notification sent ({count} events)")
        else:
            logger.error("Failed to send notification")
        
        return success
    
    def _send_message(self, text: str) -> bool:
        """Send message to Telegram with retry logic."""
        url = f"{self.base_url}/sendMessage"
        
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        
        for attempt in range(3):
            try:
                response = self.session.post(url, json=payload, timeout=10)
                
                if response.status_code == 200:
                    return True
                
                # Handle rate limiting from Telegram (429 Too Many Requests)
                if response.status_code == 429:
                    retry_after = int(response.json().get('parameters', {}).get('retry_after', 5))
                    logger.warning(f"Telegram rate limited. Retry after {retry_after}s")
                    time.sleep(retry_after)
                    continue
                
                logger.error(f"Telegram API error: {response.status_code}")
                return False
                
            except requests.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1})")
                time.sleep(5)
                continue
            except requests.ConnectionError:
                logger.error("Connection error to Telegram API")
                return False
        
        return False
```

### Integration with Database Logger

```python
# In src/database/logger.py, extend the record_notification method:

def log_notification_result(self, traffic_log_id: int, status: str, error: str = None):
    """Log notification result to database."""
    query = """
        UPDATE notification_logs 
        SET status = ?, error_message = ?
        WHERE traffic_log_id = ? AND status = 'sent'
    """
    # Note: This assumes notification is logged before sending
    # Update after actual send attempt
    self.db.execute(query, (status, error, traffic_log_id))
```

---

## Testing

### Manual Test

```bash
# Test with curl
curl -X POST http://localhost:8000/test-notification \
  -H "Content-Type: application/json" \
  -d '{
    "label": "anomalous",
    "confidence": 0.95,
    "attack_class": "sql_injection",
    "source_ip": "192.168.1.100",
    "url": "/api/login",
    "method": "POST"
  }'
```

### Unit Test

```python
import unittest
from src.notifier.telegram_bot import TelegramNotifier
from src.notifier.aggregator import NotificationAggregator

class TestNotificationAggregator(unittest.TestCase):
    def test_single_alert(self):
        config = {
            'aggregation_window_seconds': 60,
            'max_notifications_per_hour': 20,
            'min_interval_seconds': 30
        }
        agg = NotificationAggregator(config)
        
        alert = {'timestamp': time.time(), 'label': 'anomalous'}
        self.assertTrue(agg.should_notify(alert))
    
    def test_rate_limiting(self):
        config = {
            'aggregation_window_seconds': 60,
            'max_notifications_per_hour': 3,
            'min_interval_seconds': 1
        }
        agg = NotificationAggregator(config)
        
        # Send 3 alerts (should all pass)
        for i in range(3):
            alert = {'timestamp': time.time(), 'label': 'anomalous'}
            time.sleep(1.1)
            self.assertTrue(agg.should_notify(alert))
        
        # 4th alert should be suppressed
        alert = {'timestamp': time.time(), 'label': 'anomalous'}
        self.assertFalse(agg.should_notify(alert))
```

---

## Acceptance Criteria

- [ ] Bot dikirim ke Telegram saat anomalous terdeteksi
- [ ] Message format sesuai template (single + aggregated)
- [ ] Rate limiting berfungsi: tidak > max_notifications_per_hour
- [ ] Aggregation group alerts dalam window waktu yang ditentukan
- [ ] Retry logic bekerja jika pengiriman gagal
- [ ] Telegram rate limiting (429) ditangani dengan benar
- [ ] Notification logged ke database
- [ ] Dapat disable/enable via konfigurasi tanpa code change
- [ ] Tidak mengirim notifikasi untuk traffic normal
