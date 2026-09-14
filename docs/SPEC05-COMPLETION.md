# Spec 05 — Catatan Penyelesaian (Login, Block Validation, Telegram)

**Tanggal**: 13 September 2026
**Status**: Selesai — semua item "Masih belum selesai" di status sebelumnya sudah diimplementasikan dan diuji end-to-end.

---

## 1. Root cause "ANOMALY masih bisa masuk ke /my/courses"

Setelah investigasi langsung (jalankan Inference API + Website, kirim payload nyata),
**bukan** AI Guard middleware/PolicyEngine yang bermasalah:

- Payload serangan yang **sesuai pola dataset CSIC 2010** (`<script>...</script>`,
  `UNION SELECT ... FROM ...`) sudah terdeteksi `anomalous` dengan confidence ~99.9%
  dan **sudah** menghasilkan `403 Blocked` di endpoint mana pun (`/search`,
  `/my/courses`, dst) — lihat `scripts/e2e_login_and_guard_test.py`.
- `PolicyEngine` (confidence > 0.7 → block, else flag) adalah desain yang **disengaja**
  dan sudah dicakup unit test (`src/middleware/test_policy_engine.py`) — **tidak diubah**.
- Penyebab sebenarnya: endpoint `/login` **tidak punya autentikasi sungguhan**
  ("semua kredensial dianggap valid"). Kombinasi dengan payload SQLi klasik berbasis
  kutip (`' OR '1'='1`) yang **tidak match** regex `SQL_KEYWORDS_PATTERN` (hanya
  menangkap `OR 1=1` numerik — keterbatasan dataset CSIC 2010, sudah didokumentasikan
  di `docs/KNOWN-LIMITATIONS.md` #2) membuat request lolos AI **dan** lolos login palsu
  sekaligus, sehingga tampak seperti "AI Guard gagal".

**Kesimpulan**: perbaikan yang dibutuhkan adalah **layer autentikasi sungguhan**
sebagai defense-in-depth, bukan mengubah threshold/PolicyEngine.

---

## 2. Perubahan yang diimplementasikan

### a. Login sungguhan (`src/website/auth.py`, `src/website/app.py`)
- Tabel baru `students` (username, password **hash** via `werkzeug.security`).
- `authenticate(username, password)` mengembalikan salah satu dari:
  `success` / `invalid_username` / `invalid_password` — pesan berbeda ditampilkan
  di `login.html`.
- Session Flask (`session["student_id"]`) menggerbang akses `/dashboard` dan
  `/my/courses` via decorator `login_required`.
- Akun demo di-seed lewat `scripts/seed_students.py` (idempotent).

### b. Audit trail login (`login_attempts` table)
- Setiap percobaan login (berhasil atau gagal) dicatat: timestamp, username,
  source IP, hasil (`success`/`invalid_username`/`invalid_password`).

### c. Block validation
- Tidak ada perubahan pada `PolicyEngine`. Divalidasi ulang end-to-end bahwa
  payload sesuai dataset (XSS, SQLi `UNION SELECT`, dst) selalu berujung `403`.
- `skip_paths` ditambah `/static/*` dan `/logout` (murni efisiensi — aset statis
  & logout tidak perlu discan AI, tidak mengubah keputusan block/allow untuk
  endpoint lain).

### d. Notifikasi Telegram (`src/notifier/`)
- Paket baru: `aggregator.py` (rate limiting & burst aggregation),
  `templates.py` (format single/aggregated alert), `telegram_bot.py`
  (`TelegramNotifier`), sesuai `specs/07-notifications.md`.
- Dipasang di `AIGuardMiddleware` — **hanya** trigger saat
  `label == "anomalous" AND action == "block"` (sesuai target: notifikasi
  hanya saat ANOMALY, bukan setiap flag).
- **Mode disabled**: jika `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` belum
  diset (env var), notifier tidak memanggil Telegram API sungguhan — hanya
  log pesan yang *akan* dikirim, dan tetap mencatat ke `notification_logs`
  (status `aggregated`). Ini membuat sistem tetap jalan tanpa bot Telegram
  sungguhan saat development.
- Hasil notifikasi (sent/aggregated/failed + preview pesan) dicatat ke tabel
  `notification_logs` via `TrafficLogger.log_notification()`.

### e. Database & logging
- `StubDBLogger` diganti `TrafficLogger` (SQLite asli) + `init_db()` dipanggil
  saat `create_app()`.
- `source_ip` sekarang benar-benar diisi (sebelumnya kosong — middleware tidak
  pernah mengirim field ini ke logger).
- Tabel baru: `students`, `login_attempts`.

### f. Privasi hasil AI ke mahasiswa
- Response body & template mahasiswa (`login.html`, `dashboard.html`) **tidak
  pernah** memuat `label`/`confidence`/`attack_class`.
- Header debug `X-AI-Guard` hanya berisi aksi kasar (`allow`/`flag`); response
  `403` (block) tetap tidak memiliki header ini (lihat keputusan yang sudah
  ada di `docs/KNOWN-LIMITATIONS.md` #1 — dipertahankan apa adanya).

---

## 3. Cara menjalankan & menguji

```bash
# 1) Setup
pip install -r requirements-inference.txt -r requirements-website.txt
python3 -m scripts.seed_students          # seed akun demo

# 2) Jalankan kedua server (terminal terpisah)
python3 -m uvicorn src.api.main:app --port 8000
python3 -m src.website.app                # port 5000

# 3) (Opsional) aktifkan Telegram sungguhan
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...

# 4) Jalankan uji end-to-end
python3 -m scripts.e2e_login_and_guard_test
python3 -m scripts.inspect_db             # lihat isi DB (login/traffic/notifikasi)
```

Akun demo: `student1` / `student2` / `student3`, password `Passw0rd123`.

## 4. Item yang masih di luar scope (tidak diminta di target akhir)
- Dashboard admin (Spec 06) belum direvisi untuk membaca dari `traffic_logs`
  secara real-time (masih pakai `courses=[]` statis) — di luar 8 target akhir
  yang diminta.
- Retrain model untuk menutup celah kutip-SQLi (`' OR '1'='1`) — sudah
  didokumentasikan sebagai limitation dataset, bukan bug kode.
