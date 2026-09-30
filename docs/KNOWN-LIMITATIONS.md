# Known Limitations — CONNEXTS AI | Network Guard

---

## 1. `X-AI-Guard` Header Tidak Ada pada Response 403

**Tanggal Dicatat**: 7 September 2026  
**Spec Terkait**: Spec 04 — Middleware Integration  
**Acceptance Criteria Terkait**: Poin 6 — "Headers X-AI-Guard ditambahkan ke semua response"

### Deskripsi

Saat middleware memutuskan `action == "block"`, response 403 dikembalikan
SEBELUM `g.ai_guard_action` di-set. Akibatnya `after_request` hook tidak
menambahkan header `X-AI-Guard`.

### Dampak

- Response 200 dan response ber-`flag` memiliki `X-AI-Guard: allow|flag`.
- Response 403 (block) **TIDAK** memiliki header `X-AI-Guard`.
- Klien tidak bisa membedakan "block karena AI Guard" vs "block karena
  endpoint" hanya dari header (mereka harus parse body JSON).

### Keputusan

Dibiarkan apa adanya. Response 403 sudah self-explanatory:
```json
{"error": "Request blocked by AI Guard", "reason": "Anomalous traffic detected"}
```

Perubahan akan menambah kompleksitas tanpa nilai observability yang signifikan.

---

## 2. CSIC 2010 Domain Gap — False Positive pada Request Modern

**Tanggal Dicatat**: 4 September 2026 (Spec 03), diverifikasi 7 September 2026  
**Spec Terkait**: Spec 03 — Inference API

### Deskripsi

Model XGBoost dilatih pada dataset CSIC 2010 di mana 100% sampel normal
memiliki URL absolut Spanyol (`http://localhost:8080/tienda1/...`). Request
modern sederhana (mis. `GET /search?q=hello`) bisa dikategorikan anomalous
meskipun benign, karena pola statistik fitur tidak cocok dengan data training.

### Mitigasi Saat Ini

- **Guard rail `is_clean_benign`**: Mendeteksi GET request bersih tanpa body,
  query params, encoded chars, atau attack signature — dipaksa return `normal`.
- Guard rail **TIDAK** melindungi kasus dengan query params benign
  (`GET /search?q=hello` tetap FP).

### Solusi Jangka Panjang

Retrain model dengan dataset traffic modern yang mencakup pola URL RESTful.
