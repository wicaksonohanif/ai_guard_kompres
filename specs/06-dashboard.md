# Spec 06: Admin Dashboard

**Version**: 1.1 (Updated for 32 features from Spec 01)
**Date**: 31 Agustus 2026
**Related PRD**: FR-6

---

## Tujuan

Menyediakan dashboard admin untuk memonitor traffic real-time, melihat riwayat deteksi anomali, dan menganalisis pola serangan. Dashboard dapat diakses via browser di `/dashboard`.

---

## Fitur Dashboard

### 1. Real-Time Traffic Overview

| Widget | Deskripsi | Update |
|--------|-----------|--------|
| Total Requests (24h) | Jumlah total request dalam 24 jam terakhir | Setiap 30 detik |
| Normal vs Anomalous Ratio | Pie chart perbandingan normal/anomalous | Setiap 30 detik |
| Anomalies per Hour | Line chart jumlah anomalous per jam | Setiap 30 detik |
| Active Alerts | Counter anomalous dalam 5 menit terakhir | Real-time (WebSocket) atau polling 10s |

### 2. Anomaly History Table

Tabel detail semua deteksi anomali dengan kolom:

| Kolom | Deskripsi |
|-------|-----------|
| Timestamp | Waktu kejadian |
| Source IP | IP pengirim |
| Method + URL | Endpoint yang di-request |
| Attack Class | Jenis serangan terdeteksi |
| Confidence | Score confidence |
| Action | allow / flag / block |
| Review Status | auto / manual_review / false_positive / confirmed_attack |

### 3. Filters

| Filter | Tipe | Options |
|--------|------|---------|
| Time Range | Date picker | Hari ini, 7 hari, 30 hari, custom range |
| Attack Class | Multi-select | SQL Injection, XSS, CRLF, dll. |
| Action | Select | allow, flag, block |
| Source IP | Text input | Filter by IP |
| Review Status | Select | auto, manual_review, false_positive, confirmed_attack |

### 4. Feature Importance Visualization

Menampilkan top 15 feature importance dari model XGBoost untuk edukasi dan penjelasan ke juri.

### 5. Model Metrics

Menampilkan current performance metrics model:
- Accuracy, Precision, Recall, F1-Score
- Confusion matrix visualization
- Historical metric trends

---

## API Endpoints untuk Dashboard

### GET /dashboard/api/traffic-summary?hours=24

Ringkasan traffic terkini.

```json
{
    "total_requests": 15420,
    "normal_count": 12300,
    "anomalous_count": 3120,
    "anomaly_rate": 0.202,
    "per_hour": [
        {"hour": "2026-08-29T00:00", "normal": 450, "anomalous": 89},
        {"hour": "2026-08-29T01:00", "normal": 380, "anomalous": 102},
        ...
    ],
    "top_attack_classes": [
        {"class": "sql_injection", "count": 1200},
        {"class": "xss", "count": 850},
        {"class": "crlf_injection", "count": 420}
    ]
}
```

### GET /dashboard/api/anomalies?page=1&limit=50&attack_class=sql_injection

Riwayat anomali dengan pagination.

```json
{
    "data": [
        {
            "id": 1001,
            "timestamp": "2026-08-29T14:23:45",
            "source_ip": "192.168.1.100",
            "method": "POST",
            "url": "/api/login",
            "attack_class": "sql_injection",
            "confidence": 0.97,
            "action": "block",
            "review_status": "confirmed_attack"
        },
        ...
    ],
    "pagination": {
        "page": 1,
        "limit": 50,
        "total": 3120,
        "total_pages": 63
    }
}
```

### GET /dashboard/api/feature-importance

Top features dari model.

```json
{
    "features": [
        {"name": "payload_has_sql_keywords", "importance": 0.245},
        {"name": "url_special_char_count", "importance": 0.182},
        {"name": "payload_entropy", "importance": 0.134},
        ...
    ]
}
```

### GET /dashboard/api/model-metrics

Current model performance.

```json
{
    "accuracy": 0.965,
    "precision": 0.952,
    "recall": 0.941,
    "f1_score": 0.946,
    "roc_auc": 0.982,
    "snapshot_date": "2026-08-29"
}
```

---

## Frontend Architecture

### Lokasi File

```
frontend/
├── dashboard/
│   ├── index.html             # Main dashboard page
│   ├── css/
│   │   └── dashboard.css      # Styles
│   ├── js/
│   │   ├── app.js             # Main application logic
│   │   ├── charts.js          # Chart rendering
│   │   ├── tables.js          # Table rendering & pagination
│   │   ├── websocket.js       # Real-time updates (optional)
│   │   └── api.js             # API client functions
│   └── templates/
│       ├── overview.html      # Traffic overview section
│       ├── anomalies.html     # Anomaly history table
│       ├── model-info.html    # Model metrics & feature importance
│       └── settings.html      # Configuration panel
```

### Tech Stack

| Layer | Technology | Alasan |
|-------|------------|--------|
| HTML/CSS | Vanilla + CSS Variables | Ringan, no build step untuk demo |
| JavaScript | Vanilla ES6+ | No framework needed untuk prototipe |
| Charts | Chart.js | Simple, responsive, good for dashboards |
| Tables | Custom + DataTables (optional) | Pagination, sorting, filtering |
| Real-time | Server-Sent Events (SSE) atau polling | Lebih simple daripada WebSocket untuk demo |

### Alternative: FastAPI Template Engine

```python
# src/dashboard/routes.py
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
templates = Jinja2Templates(directory="frontend/dashboard")

@router.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/api/traffic-summary")
async def get_traffic_summary(hours: int = 24):
    return traffic_logger.get_traffic_summary(hours)

@router.get("/api/anomalies")
async def get_anomalies(
    page: int = 1,
    limit: int = 50,
    attack_class: str = None,
    start_time: str = None,
    end_time: str = None
):
    return anomaly_logger.get_paginated_anomalies(
        page=page, limit=limit, 
        attack_class=attack_class,
        start_time=start_time,
        end_time=end_time
    )
```

---

## UI Wireframe (Text-Based)

```
┌─────────────────────────────────────────────────────────────────────┐
│  AI Guard - Admin Dashboard                               [🔄 Refresh] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │
│  │ Total Req    │ │ Normal       │ │ Anomalous    │ │ Alert Rate │ │
│  │  15,420      │ │  12,300      │ │  3,120       │ │  20.2%     │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘ │
│                                                                      │
│  ┌──────────────────────────────────┐ ┌────────────────────────────┐ │
│  │  Traffic Over 24 Hours           │ │  Normal vs Anomalous       │ │
│  │  ██████                          │ │        _______             │ │
│  │  ╱╲   ╲                         │ │      ╱        ╲            │ │
│  │ ╱  ╲   ╲______                  │ │    ╱  Normal   ╲           │ │
│  │╱      ╲_______╲                 │ │   ╱    79.7%     ╲         │ │
│  └──────────────────────────────────┘ └────────────────────────────┘ │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │  Anomaly History                        [Filters ▼] [Export CSV] ││
│  ├──────────────────────────────────────────────────────────────────┤│
│  │ Time            │ Source IP     │ Attack Class  │ Conf │ Action ││
│  │ 29 Aug 14:23:45 │ 192.168.1.1 │ SQL Injection │ 0.97 │ Block  ││
│  │ 29 Aug 14:22:12 │ 10.0.0.5    │ XSS           │ 0.91 │ Block  ││
│  │ 29 Aug 14:21:08 │ 172.16.0.3  │ CRLF Inject   │ 0.84 │ Flag   ││
│  │ ...                                                          ││
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌──────────────────────────────────┐ ┌────────────────────────────┐ │
│  │  Top Attack Classes              │ │  Model Performance         │ │
│  │  SQL Injection   ████████ 38%    │ │  Accuracy:  96.5%          │ │
│  │  XSS             ██████   27%    │ │  Precision: 95.2%          │ │
│  │  CRLF Inject     ████     13%    │ │  Recall:    94.1%          │ │
│  │  Buffer Overflow ██       9%     │ │  F1-Score:  94.6%          │ │
│  │  Others          █        13%    │ │  ROC-AUC:   98.2%          │ │
│  └──────────────────────────────────┘ └────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Responsive Design Requirements

- Desktop-first design (1920x1080 target)
- Tablet support (min-width: 768px)
- Mobile support (min-width: 375px) - simplified layout

---

## Acceptance Criteria

- [ ] Dashboard accessible di `/dashboard`
- [ ] Traffic summary menampilkan data real-time (update minimal setiap 30 detik)
- [ ] Anomaly history table menampilkan data dari database
- [ ] Filters berfungsi: time range, attack class, action, source IP
- [ ] Pagination bekerja dengan benar pada anomaly table
- [ ] Chart.js renders pie chart dan line chart dengan benar
- [ ] Feature importance ditampilkan sebagai horizontal bar chart
- [ ] Model metrics section menampilkan current performance metrics
- [ ] Export to CSV button tersedia untuk anomaly data
- [ ] Dashboard tampil baik di desktop dan tablet
- [ ] Loading state terlihat saat data sedang dimuat
