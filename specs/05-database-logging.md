# Spec 05: Database & Logging

**Version**: 1.1 (Updated feature_count from 25 to 32 per Spec 01)
**Date**: 31 Agustus 2026
**Related PRD**: FR-5

---

## Tujuan

Menyimpan setiap hasil klasifikasi traffic HTTP beserta metadata lengkap ke database, sehingga dapat diakses oleh Dashboard Admin dan digunakan untuk analisis historis serta retraining model di masa depan.

---

## Teknologi Database

| Environment | Database | Alasan |
|-------------|----------|--------|
| Development / Demo | SQLite | Ringan, no external dependency, cukup untuk prototipe |
| Production (future) | PostgreSQL | Scalable, mendukung concurrent writes |

Untuk fase kompetisi/demo, gunakan **SQLite** saja.

---

## Skema Database

### Table: `traffic_logs`

Menyimpan setiap request yang diproses oleh middleware.

```sql
CREATE TABLE traffic_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_ip       TEXT,
    source_port     INTEGER,
    method          TEXT NOT NULL,
    url             TEXT NOT NULL,
    full_url        TEXT,
    user_agent      TEXT,
    referer         TEXT,
    content_type    TEXT,
    payload_body    TEXT,
    
    -- Classification result
    label           TEXT NOT NULL CHECK(label IN ('normal', 'anomalous')),
    confidence      REAL NOT NULL,
    attack_class    TEXT,
    
    -- Action taken by middleware
    action          TEXT NOT NULL CHECK(action IN ('allow', 'flag', 'block')),
    
    -- Metrics
    inference_latency_ms  REAL,
    feature_count       INTEGER,
    
    -- Metadata
    is_blocked     INTEGER DEFAULT 0 CHECK(is_blocked IN (0, 1)),
    review_status  TEXT DEFAULT 'auto' CHECK(review_status IN ('auto', 'manual_review', 'false_positive', 'confirmed_attack')),
    
    INDEX idx_timestamp (timestamp),
    INDEX idx_label (label),
    INDEX idx_attack_class (attack_class),
    INDEX idx_source_ip (source_ip),
    INDEX idx_review_status (review_status)
);
```

### Table: `notification_logs`

Mencatat setiap notifikasi Telegram yang dikirim.

```sql
CREATE TABLE notification_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    traffic_log_id  INTEGER REFERENCES traffic_logs(id),
    sent_at         DATETIME,
    status          TEXT NOT NULL CHECK(status IN ('sent', 'failed', 'aggregated')),
    message_preview TEXT,
    error_message   TEXT,
    aggregated_from INTEGER DEFAULT 1  -- Jumlah event dalam agregasi
);
```

### Table: `model_metrics_snapshots`

Snapshots periodik metrik model untuk monitoring degradation.

```sql
CREATE TABLE model_metrics_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date   DATE NOT NULL,
    accuracy        REAL,
    precision       REAL,
    recall          REAL,
    f1_score        REAL,
    roc_auc         REAL,
    total_predictions   INTEGER,
    normal_count      INTEGER,
    anomalous_count   INTEGER,
    fpr               REAL,
    note              TEXT
);
```

### Table: `configuration`

Konfigurasi sistem yang dapat diubah tanpa code change.

```sql
CREATE TABLE configuration (
    key       TEXT PRIMARY KEY,
    value     TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Default values
INSERT INTO configuration (key, value) VALUES 
    ('block_threshold', '0.7'),
    ('notification_enabled', '1'),
    ('telegram_bot_token', ''),
    ('telegram_chat_id', ''),
    ('notification_aggregation_window_sec', '60'),
    ('max_notifications_per_hour', '20'),
    ('middleware_enabled', '1');
```

---

## Database Abstraction Layer

### Lokasi File

```
src/
├── database/
│   ├── __init__.py
│   ├── connection.py         # DB connection management
│   ├── models.py             # SQLAlchemy / raw query models
│   ├── logger.py             # Traffic logging functions
│   └── queries.sql           # Raw SQL queries
```

### Connection Management

```python
# src/database/connection.py
import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.getenv("AI_GUARD_DB_PATH", "data/ai_guard.db")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
    return conn

@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initialize database schema."""
    with get_db() as conn:
        conn.executescript(open("src/database/schema.sql").read())
```

### Logger Interface

```python
# src/database/logger.py
from datetime import datetime
from typing import Optional

class TrafficLogger:
    """Log classification results to database."""
    
    def __init__(self, db_conn):
        self.db = db_conn
    
    def log_request(
        self,
        request: dict,
        label: str,
        confidence: float,
        action: str,
        latency_ms: float,
        attack_class: Optional[str] = None
    ):
        """
        Log a single traffic classification result.
        
        Args:
            request: dict dengan keys method, url, headers, body
            label: 'normal' atau 'anomalous'
            confidence: confidence score (0.0 - 1.0)
            action: 'allow', 'flag', atau 'block'
            latency_ms: waktu inference dalam ms
            attack_class: jenis serangan (hanya jika anomalous)
        """
        query = """
            INSERT INTO traffic_logs 
            (source_ip, method, url, user_agent, referer, content_type, 
             payload_body, label, confidence, attack_class, action,
             inference_latency_ms, feature_count, is_blocked)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            request.get('source_ip'),
            request['method'],
            request['url'],
            request.get('headers', {}).get('User-Agent', ''),
            request.get('headers', {}).get('Referer', ''),
            request.get('headers', {}).get('Content-Type', ''),
            request.get('body', '')[:10000],  # Truncate超长payload
            label,
            confidence,
            attack_class,
            action,
            latency_ms,
            32,  # feature_count (updated from 25 to 32 per Spec 01)
            1 if action == 'block' else 0
        )
        
        self.db.execute(query, params)
    
    def get_anomaly_reports(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        attack_class: Optional[str] = None,
        limit: int = 100
    ) -> list:
        """Query anomaly records with optional filters."""
        query = "SELECT * FROM traffic_logs WHERE label = 'anomalous'"
        params = []
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        if attack_class:
            query += " AND attack_class = ?"
            params.append(attack_class)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        return self.db.execute(query, params).fetchall()
    
    def get_traffic_summary(self, hours: int = 24) -> dict:
        """Get summary statistics for recent traffic."""
        query = """
            SELECT 
                label,
                COUNT(*) as count,
                AVG(confidence) as avg_confidence,
                GROUP_CONCAT(DISTINCT attack_class) as attack_classes
            FROM traffic_logs 
            WHERE timestamp >= datetime('now', ?)
            GROUP BY label
        """
        rows = self.db.execute(query, (f'-{hours} hours',)).fetchall()
        
        summary = {}
        for row in rows:
            summary[row['label']] = {
                'count': row['count'],
                'avg_confidence': row['avg_confidence'],
                'attack_classes': row['attack_classes'].split(',') if row['attack_classes'] else []
            }
        
        return summary
    
    def record_notification(
        self,
        traffic_log_id: int,
        status: str,
        message_preview: Optional[str] = None,
        error_message: Optional[str] = None,
        aggregated_from: int = 1
    ):
        """Record a notification send attempt."""
        query = """
            INSERT INTO notification_logs 
            (traffic_log_id, sent_at, status, message_preview, 
             error_message, aggregated_from)
            VALUES (?, current_timestamp, ?, ?, ?, ?)
        """
        self.db.execute(query, (
            traffic_log_id, status, message_preview, error_message, aggregated_from
        ))
```

---

## Data Retention Policy

| Table | Retention | Cleanup Strategy |
|-------|-----------|-----------------|
| `traffic_logs` | 30 hari | Delete records older than 30 days weekly |
| `notification_logs` | 30 hari | CASCADE via foreign key or manual cleanup |
| `model_metrics_snapshots` | Forever | Append-only, keep historical |

### Cleanup Script

```python
def cleanup_old_records(days: int = 30):
    """Remove records older than specified days."""
    with get_db() as conn:
        conn.execute(
            "DELETE FROM traffic_logs WHERE timestamp < datetime('now', ?)",
            (f"-{days} days",)
        )
        conn.execute(
            "DELETE FROM notification_logs WHERE timestamp < datetime('now', ?)",
            (f"-{days} days",)
        )
```

---

## Acceptance Criteria

- [ ] Semua tabel sesuai skema di atas dibuat saat initialization
- [ ] Setiap classification result tercatat di `traffic_logs`
- [ ] Query filter by time range, attack class bekerja dengan benar
- [ ] Traffic summary aggregation memberikan statistik akurat
- [ ] Notification logged ke `notification_logs`
- [ ] Data retention cleanup berjalan (manual script, bukan auto)
- [ ] Database file berlokasi di `data/ai_guard.db` (di-gitignore)
- [ ] Schema migration tersedia jika ada perubahan struktur
