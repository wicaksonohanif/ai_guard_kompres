# Product Requirements Document (PRD)
## CONNEXTS AI | Network Guard: Embedded Web Security Feature dengan AI-based Traffic Classification

**Versi**: 1.0
**Status**: Draft untuk Kompetisi AI Innovation Kampus
**Tanggal**: 29 Agustus 2026

---

## 1. Ringkasan Eksekutif

**CONNEXTS AI | Network Guard** adalah fitur keamanan berbasis AI yang tertanam di dalam prototipe website kampus, dirancang untuk mengklasifikasikan traffic HTTP masuk sebagai **normal** atau **anomalous** secara real-time. Sistem ini dilengkapi dengan dashboard monitoring untuk admin dan notifikasi otomatis via Telegram ketika terdeteksi traffic mencurigakan.

Tujuan proyek ini adalah mendemonstrasikan penerapan machine learning untuk deteksi serangan web tingkat aplikasi (application-layer attack detection) dalam bentuk prototipe yang dapat didemonstrasikan secara end-to-end: dari simulasi serangan, deteksi oleh model, hingga notifikasi ke admin.

---

## 2. Latar Belakang & Masalah

Website, termasuk website institusi seperti kampus, rentan terhadap serangan berbasis payload seperti SQL Injection, XSS, dan parameter tampering. Mekanisme keamanan konvensional (WAF berbasis rule/signature) sering kali:

- Sulit mendeteksi variasi serangan yang tidak sesuai signature yang sudah didefinisikan.
- Tidak memberikan visibilitas real-time yang mudah dipahami admin non-teknis.
- Tidak memiliki mekanisme notifikasi proaktif ke pengelola sistem.

CONNEXTS AI mencoba menjawab celah ini dengan pendekatan machine learning dengan model yang ringan untuk deteksi anomali, dipadukan dengan monitoring dan notifikasi yang actionable.

---

## 3. Tujuan Produk (Goals)

1. Membangun model klasifikasi yang dapat membedakan traffic HTTP normal vs anomalous dengan akurasi dan precision/recall yang baik pada kelas serangan yang menjadi scope.
2. Mengintegrasikan model ke dalam prototipe website kampus sebagai middleware yang memproses request secara real-time.
3. Menyediakan dashboard admin untuk memonitor traffic dan riwayat deteksi anomali.
4. Mengirim notifikasi otomatis ke Telegram saat anomali terdeteksi.
5. Mendemonstrasikan sistem secara end-to-end dalam sesi presentasi kompetisi.

### Non-Goals (Di Luar Scope)
- Bukan pengganti WAF (Web Application Firewall) production-grade.
- Tidak menangani serangan level network/infrastruktur (DDoS, port scanning).
- Tidak dirancang untuk deployment ke sistem produksi kampus yang sesungguhnya.
- Tidak mencakup remediasi otomatis (auto-block IP, auto-patch) pada versi prototipe ini.

---

## 4. Target Pengguna

| Persona | Kebutuhan |
|---|---|
| **Admin/IT Kampus (simulasi)** | Memantau traffic mencurigakan, menerima notifikasi cepat, melihat riwayat insiden di dashboard |
| **Juri Kompetisi** | Melihat demonstrasi teknis yang jelas, memahami metodologi, menilai orisinalitas dan kelayakan solusi |
| **Pengguna Website Prototipe** | Mengalami traffic normal tanpa gangguan (false positive minim) |

---

## 5. Ruang Lingkup & Batasan (Scope)

### 5.1 Jenis Serangan yang Dicakup
Berdasarkan dataset CSIC 2010 HTTP Dataset, sistem difokuskan mendeteksi kelas serangan berbasis payload injection pada level HTTP request:

1. SQL Injection
2. Cross-Site Scripting (XSS)
3. Parameter Tampering
4. CRLF Injection
5. Buffer Overflow (payload berlebihan)
6. Information Gathering / File Disclosure
7. Server-Side Include (SSI) Injection

### 5.2 Batasan Eksplisit
- Serangan level network/infrastruktur (DDoS, port scanning, brute force login berbasis volume) **di luar scope**.
- Serangan API modern (SSRF, JWT manipulation, GraphQL injection, insecure deserialization) **di luar scope**, karena tidak terepresentasi dalam dataset training (CSIC 2010 dari tahun 2010).
- Model dilatih pada traffic sintetis (CSIC 2010) yang disupplementasi dengan traffic self-generated dari prototipe; bukan traffic produksi nyata.
- Sistem berjalan di environment sandbox/lokal untuk keperluan demo, bukan deployment publik.

---

## 6. Fitur Utama (Functional Requirements)

### FR-1: Feature Extraction Engine
- Sistem mengekstraksi fitur dari setiap HTTP request masuk (method, panjang URL, jumlah parameter, entropy payload, keyword mencurigakan, karakter spesial, dll).
- Fungsi ekstraksi fitur harus identik antara pipeline training (dataset CSIC) dan pipeline inference (traffic live) untuk menjaga konsistensi.

### FR-2: Model Klasifikasi (CONNEXT)
- Model utama: **XGBoost**, dilatih pada dataset CSIC 2010 (+ data self-generated dari prototipe).
- Output: label (`normal` / `anomalous`) beserta confidence score.
- Model harus dapat dipanggil secara real-time dengan latensi rendah (target < 100ms per request).

### FR-3: Middleware Integrasi di Prototipe Website
- Middleware menangkap setiap request masuk ke website prototipe sebelum diproses oleh aplikasi.
- Request diteruskan ke Feature Extractor → Inference API → hasil klasifikasi diteruskan ke logging.

### FR-4: Inference API
- REST API (FastAPI) dengan endpoint `/predict` yang menerima fitur request dan mengembalikan hasil klasifikasi.
- Stateless, dapat di-scale terpisah dari aplikasi utama.

### FR-5: Logging & Database
- Setiap hasil klasifikasi (normal maupun anomalous) dicatat dengan metadata: timestamp, source IP, endpoint, jenis payload (jika anomalous), confidence score.
- Database ringan (SQLite/PostgreSQL) untuk kebutuhan prototipe.

### FR-6: Dashboard Admin
- Visualisasi traffic real-time (jumlah request normal vs anomalous).
- Tabel riwayat deteksi anomali dengan detail (waktu, sumber, jenis serangan terdeteksi).
- Filter berdasarkan rentang waktu/jenis serangan.

### FR-7: Notifikasi Telegram
- Saat traffic anomalous terdeteksi, sistem mengirim notifikasi ke Telegram Bot berisi ringkasan insiden (waktu, IP, endpoint, jenis serangan, confidence score).
- Mekanisme agregasi/rate-limiting notifikasi untuk mencegah spam saat terjadi burst serangan.

### FR-8: Simulasi Serangan (Demo Tool)
- Modul/skrip untuk mengirim payload serangan (SQLi, XSS, dll) ke prototipe website sebagai bahan demonstrasi live saat presentasi.

---

## 7. Kebutuhan Non-Fungsional (Non-Functional Requirements)

| Kategori | Kebutuhan |
|---|---|
| **Performa** | Inferensi model < 100ms per request agar tidak mengganggu UX website |
| **Reliabilitas Demo** | Seluruh sistem dikemas dengan Docker Compose agar dapat dijalankan konsisten saat presentasi |
| **Akurasi Model** | Precision & recall dilaporkan per kelas (bukan hanya akurasi keseluruhan), mengingat pentingnya false positive rate yang rendah |
| **Interpretability** | Feature importance dari model harus dapat ditampilkan untuk kebutuhan penjelasan ke juri |
| **Keamanan Demo** | Prototipe berjalan di environment terisolasi, tidak terhubung ke sistem produksi kampus |

---

## 8. Arsitektur Sistem (High-Level)

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

Seluruh komponen dikemas dengan **Docker Compose** untuk kemudahan eksekusi saat demo.

---

## 9. Metodologi & Model

| Aspek | Keputusan |
|---|---|
| **Dataset Utama** | CSIC 2010 HTTP Dataset |
| **Dataset Tambahan** | Traffic self-generated dari prototipe (normal + simulasi serangan) |
| **Model Produksi** | XGBoost (akurat, ringan, interpretable, cepat inferensi) |
| **Evaluasi** | Precision, Recall, F1-score per kelas serangan; feature importance; uji ketahanan terhadap payload ter-obfuscate |

---

## 10. Metrik Keberhasilan (Success Metrics)

1. **Akurasi klasifikasi** ≥ 95% pada test set CSIC 2010 (target berdasar benchmark literatur).
2. **False positive rate** rendah pada traffic normal dari prototipe (agar tidak mengganggu UX saat demo).
3. **Latensi inferensi** < 100ms per request.
4. **Demo end-to-end berhasil**: serangan tersimulasi → terdeteksi → tercatat di dashboard → notifikasi Telegram terkirim, seluruhnya real-time saat presentasi.
5. Kejelasan dokumentasi batasan scope (dinilai secara kualitatif oleh juri sebagai bagian dari akademik defensibility).

---

## 11. Risiko & Mitigasi

| Risiko | Mitigasi |
|---|---|
| Dataset CSIC 2010 sudah usang, model tidak mendeteksi serangan modern | Dijelaskan eksplisit sebagai batasan scope; tambahkan data self-generated |
| False positive mengganggu demo | Tuning threshold confidence, uji dengan traffic normal ekstensif sebelum demo |
| Kegagalan environment saat presentasi | Packaging via Docker Compose, latihan run-through sebelum hari-H |
| Notifikasi Telegram flooding saat burst serangan | Implementasi agregasi/rate-limiting notifikasi |
| Overclaim kemampuan sistem ke juri | Bagian "Ruang Lingkup & Batasan" ditulis eksplisit dan jujur di proposal/laporan |

---

## 12. Rencana Pengembangan Lanjutan (Future Work)

- Perluasan dataset dengan traffic real-world/CICIDS untuk kelas serangan lebih luas.
- Continuous learning/retraining otomatis dari traffic prototipe yang terus terkumpul.
- Deteksi serangan API modern (SSRF, JWT manipulation, GraphQL injection).
- Mekanisme respons otomatis (auto-block sementara, rate-limiting adaptif).
- Skalabilitas ke arsitektur microservice dengan load balancer untuk kebutuhan produksi.

---

## 13. Timeline Indikatif (untuk Kompetisi)

| Tahap | Output |
|---|---|
| Minggu 1 | Preprocessing dataset CSIC 2010 + feature extraction pipeline |
| Minggu 2 | Training & evaluasi model XGBoost |
| Minggu 3 | Bangun prototipe website + middleware integrasi + inference API |
| Minggu 4 | Dashboard admin + notifikasi Telegram + integrasi Docker Compose |
| Minggu 5 | Testing end-to-end, simulasi serangan, penyusunan laporan & slide presentasi |

---

*Dokumen ini adalah working draft dan dapat disesuaikan seiring perkembangan implementasi teknis.*
