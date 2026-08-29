# AI Guard - Specifications Overview

**Version**: 1.0
**Status**: Draft
**Date**: 29 Agustus 2026
**Source**: PRD_AI_Guard.md v1.0

---

## Daftar Isi

| No | Dokumen | Deskripsi |
|----|---------|-----------|
| 01 | [Feature Extraction Engine](./01-feature-extraction.md) | Ekstraksi fitur dari HTTP request |
| 02 | [Model Training & Evaluation](./02-model-training.md) | Pelatihan & evaluasi model XGBoost + eksperimen LSTM/CNN |
| 03 | [Inference API](./03-inference-api.md) | REST API inference dengan FastAPI |
| 04 | [Middleware Integration](./04-middleware.md) | Interceptor middleware pada prototipe website |
| 05 | [Database & Logging](./05-database-logging.md) | Skema database & mekanisme logging |
| 06 | [Admin Dashboard](./06-dashboard.md) | Dashboard monitoring traffic & riwayat deteksi |
| 07 | [Telegram Notifications](./07-notifications.md) | Notifikasi otomatis ke Telegram Bot |
| 08 | [Attack Simulation Tool](./08-simulation-tool.md) | Alat simulasi serangan untuk demo |
| 09 | [Docker Deployment](./09-docker-deployment.md) | Containerization & orchestration |
| 10 | [Testing & Demo Procedures](./10-testing-demo.md) | Panduan testing end-to-end & prosedur demo |

---

## Arsitektur Sistem (Ringkasan)

```
[User/Attacker Traffic]
        │
        ▼
[Prototipe Website Kampus] ── Middleware Interceptor
        │
        ▼
[Feature Extractor] (Python, shared dgn training pipeline)
        │
        ▼
[Inference API - FastAPI + XGBoost Model]
        │
   ┌────┴────┐
   ▼         ▼
[Logging DB]  [Response ke Website: allow/flag]
   │
   ▼
[Dashboard Admin] ←──── (Real-time via polling/WebSocket)
   │
   ▼
[Notifier Service] ──► [Telegram Bot API] ──► Admin
```

---

## Stack Teknologi

| Komponen | Teknologi |
|----------|-----------|
| Backend API | Python 3.10+, FastAPI |
| Machine Learning | XGBoost, Scikit-learn, PyTorch (LSTM/CNN eksperimen) |
| Dataset | CSIC 2010 HTTP Dataset |
| Database | SQLite (prototipe), PostgreSQL (opsional produksi) |
| Frontend Dashboard | HTML/CSS/JS + Chart.js / Recharts |
| Container | Docker + Docker Compose |
| Notifikasi | Telegram Bot API |
| Server Web | Gunicorn + Uvicorn (API), Flask/FastAPI (Website) |

---

## Success Metrics (Dari PRD)

1. **Akurasi klasifikasi** >= 95% pada test set CSIC 2010
2. **False positive rate** rendah pada traffic normal
3. **Latensi inferensi** < 100ms per request
4. **Demo end-to-end berhasil**: serangan -> terdeteksi -> tercatat di dashboard -> notifikasi terkirim
5. Dokumentasi batasan scope yang jelas

---

## Non-Goals (Out of Scope)

- Bukan pengganti WAF production-grade
- Tidak menangani serangan level network/infrastruktur (DDoS, port scanning)
- Tidak mencakup remediasi otomatis (auto-block IP, auto-patch)
- Serangan API modern (SSRF, JWT manipulation, GraphQL injection)

---

*Setiap dokumen spec di bawah ini berisi detail teknis implementasi.*
