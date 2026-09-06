# Hardcoded Configuration — Baseline untuk Migrasi Spec 05

**Project**: CONNEXTS AI | Network Guard  
**Tanggal**: 7 September 2026  
**Tujuan**: Mendokumentasikan semua konfigurasi middleware yang saat ini hardcode
di `config/middleware_config.py`, sebagai baseline untuk migrasi ke tabel
`configuration` di SQLite (Spec 05).

---

## Status Konfigurasi Saat Ini

| Field | Lokasi Hardcode | Nilai Saat Ini | Target Migrasi (Spec 05) |
|---|---|---|---|
| `block_threshold` | `config/middleware_config.py` | `0.7` | Tabel `configuration` di SQLite |
| `fallback_mode` | `config/middleware_config.py` | `"allow"` | Tabel `configuration` |
| `enabled` | `config/middleware_config.py` | `True` | Tabel `configuration` |
| `skip_paths` | `config/middleware_config.py` | `["/health", "/dashboard/api/metrics", "/admin/*"]` | Tabel `configuration` |
| `inference_api_url` | ENV `INFERENCE_API_URL` / fallback di `config/middleware_config.py` | `http://127.0.0.1:8000/predict` | ENV + tabel (opsional) |
| `inference_timeout_ms` | `config/middleware_config.py` | `100` | Tabel `configuration` |
| `rate_limit_per_second` | `config/middleware_config.py` | `1000` | Tabel `configuration` |

---

## Catatan Migrasi

1. **Prioritas baca**: Saat migrasi ke SQLite, middleware sebaiknya membaca
   config dari database dengan fallback ke hardcode jika database belum siap.
2. **Cache**: Pertimbangkan cache config di memory dengan TTL (mis. 60 detik)
   untuk menghindari query SQLite pada setiap request.
3. **`inference_api_url`** sudah menggunakan ENV variable (LANGKAH 3 revisi)
   dan TIDAK perlu dipindah ke SQLite — cukup ENV saja.
4. **`skip_paths`** perlu disimpan sebagai JSON array di kolom TEXT SQLite.
