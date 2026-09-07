# Validation Report — Spec 03 Inference API

**Tanggal Validasi**: 4 September 2026  
**Target Spesifikasi**: [specs/03-inference-api.md](file:///Users/michaelarhdyn/Library/CloudStorage/GoogleDrive-23.michaelaristio@gmail.com/My%20Drive/Project%20Michael/Lomba%20Kompres/ai_guard_kompres/specs/03-inference-api.md)  
**Tujuan**: Memvalidasi kesiapan repository dan dependensi Step 1 & 2 sebelum implementasi Spec 03 (Inference API).

---

## 1. Ringkasan Status Kesiapan

**Status**: 🔴 **BELUM SIAP (NOT READY)**

### Alasan Singkat:
1. **Dependency Step 1 Belum Dimodularisasi**: Direktori `src/` dan paket `src/feature_extraction/` sama sekali **belum ada** di repository. Kode `FeatureExtractor` dan `HTTPRequestParser` saat ini hanya hidup di dalam sel Jupyter Notebook ([notebooks/01-xgboost-training.ipynb](file:///Users/michaelarhdyn/Library/CloudStorage/GoogleDrive-23.michaelaristio@gmail.com/My%20Drive/Project%20Michael/Lomba%20Kompres/ai_guard_kompres/notebooks/01-xgboost-training.ipynb)). Import `from ..feature_extraction...` yang diasumsikan oleh Spec 03 akan menghasilkan `ModuleNotFoundError`.
2. **Struktur & Penamaan Artifact Model Berbeda**: Artifact model hasil training Step 2 berada di [models/01-xgboost-training/01-xgboost_model.pkl](file:///Users/michaelarhdyn/Library/CloudStorage/GoogleDrive-23.michaelaristio@gmail.com/My%20Drive/Project%20Michael/Lomba%20Kompres/ai_guard_kompres/models/01-xgboost-training/01-xgboost_model.pkl) dan [models/01-xgboost-training/01-xgboost_metadata.json](file:///Users/michaelarhdyn/Library/CloudStorage/GoogleDrive-23.michaelaristio@gmail.com/My%20Drive/Project%20Michael/Lomba%20Kompres/ai_guard_kompres/models/01-xgboost-training/01-xgboost_metadata.json), bukan di root `models/xgboost_model.pkl` dan `models/xgboost_metadata.json` seperti yang di-load oleh kode contoh Spec 03.
3. **Cacat Logika Kritis pada Snippet `predict()` di Spec 03**: Pada [specs/03-inference-api.md (L266)](file:///Users/michaelarhdyn/Library/CloudStorage/GoogleDrive-23.michaelaristio@gmail.com/My%20Drive/Project%20Michael/Lomba%20Kompres/ai_guard_kompres/specs/03-inference-api.md#L266), pembuatan `parsed_request` meng-hardcode `'query_params': {}`. Padahal dalam model XGBoost yang telah dilatih, 3 fitur terpenting berkaitan langsung dengan parameter (`max_param_name_length` 29.0%, `num_params` 18.7%, `avg_param_name_length` 13.3% — total > 61% feature importance). Jika parameter tidak diparsing, inferensi real-time akan rusak parah.
4. **Ketiadaan Multi-class / Attack Type Classifier**: Model XGBoost yang tersedia adalah binary classifier murni (`normal` vs `anomalous`). Tidak ada model klasifikasi sub-tipe serangan dari Step 2. Spec 03 saat ini meng-hardcode `"sql_injection"` sebagai placeholder untuk semua anomali.
5. **Environment & Dependency Manager Belum Ada**: Tidak ada file `requirements.txt`, `pyproject.toml`, atau virtual environment di repository. Library `fastapi`, `uvicorn`, `pydantic`, `joblib`, `xgboost`, dan `scikit-learn` belum terpasang di environment lokal.

---

## 2. Hasil Verifikasi Dependency Step 1 (Feature Extraction)

### 2.1 Status `FeatureExtractor`
- **Keberadaan File Modul**: **TIDAK ADA** di `src/feature_extraction/extractor.py`. Direktori `src/` belum ada pada filesystem repo.
- **Dapat Di-import?**: **TIDAK BISA**. Menjalankan `from ..feature_extraction.extractor import FeatureExtractor` akan gagal (`ModuleNotFoundError`).
- **Implementasi Aktual**: Kode kelas `FeatureExtractor` saat ini hanya ada di cell 29 pada file [notebooks/01-xgboost-training.ipynb](file:///Users/michaelarhdyn/Library/CloudStorage/GoogleDrive-23.michaelaristio@gmail.com/My%20Drive/Project%20Michael/Lomba%20Kompres/ai_guard_kompres/notebooks/01-xgboost-training.ipynb) dan deskripsi konseptual di [specs/01-feature-extraction.md](file:///Users/michaelarhdyn/Library/CloudStorage/GoogleDrive-23.michaelaristio@gmail.com/My%20Drive/Project%20Michael/Lomba%20Kompres/ai_guard_kompres/specs/01-feature-extraction.md).

### 2.2 Status `HTTPRequestParser`
- **Keberadaan File Modul**: **TIDAK ADA** di `src/feature_extraction/parser.py`.
- **Dapat Di-import?**: **TIDAK BISA**. Menjalankan `from ..feature_extraction.parser import HTTPRequestParser` akan gagal.
- **Implementasi Aktual**: Kode kelas `HTTPRequestParser` saat ini berada di cell 6-8 pada file [notebooks/01-xgboost-training.ipynb](file:///Users/michaelarhdyn/Library/CloudStorage/GoogleDrive-23.michaelaristio@gmail.com/My%20Drive/Project%20Michael/Lomba%20Kompres/ai_guard_kompres/notebooks/01-xgboost-training.ipynb).

### 2.3 Kompatibilitas Method `.extract()` dan Input Dict
- **Signature Method**: Pada notebook, signature-nya adalah `extract(self, parsed: dict) -> list`.
- **Field yang Diharapkan oleh Extractor**:
  - `full_url` (str)
  - `path` (str)
  - `query_string` (str)
  - `body` (str)
  - `headers` (dict)
  - `query_params` (dict) ⚠️
  - `method` (str)
  - `content_length` (int)
- **Kompatibilitas dengan Spec 03**:
  Di [specs/03-inference-api.md (L260-L270)](file:///Users/michaelarhdyn/Library/CloudStorage/GoogleDrive-23.michaelaristio@gmail.com/My%20Drive/Project%20Michael/Lomba%20Kompres/ai_guard_kompres/specs/03-inference-api.md#L260-L270):
  ```python
  parsed_request = {
      'method': request.method.value if hasattr(request.method, 'value') else request.method,
      'full_url': request.url,
      'url': request.url,
      'path': request.url.split('?')[0] if '?' in request.url else request.url,
      'query_string': request.url.split('?', 1)[1] if '?' in request.url else '',
      'query_params': {},  # <-- INI SUMBER MASALAH
      'headers': {k.lower(): v for k, v in request.headers.items()},
      'body': request.body,
      'content_length': len(request.body)
  }
  ```
  Spec 03 mengoper `'query_params': {}` kosong dan tidak memanggil method parser URL/query parameter apapun. Padahal `HTTPRequestParser._parse_query_string()` yang ada di notebook mem-parse query string dan body POST form-urlencoded menjadi key-value dictionary.

### 2.4 Jumlah Fitur Aktual vs Klaim 32
- **Hasil Pengujian Aktual**: Telah dieksekusi script pengujian menggunakan implementasi `FeatureExtractor` dari notebook pada dummy input HTTP request:
  - Jumlah elemen array output: **32 fitur numerik** (float/int).
  - Tipe data return: `list` beranggotakan 32 angka, tanpa nilai NaN.
- **Inkonsistensi Antara Dokumen Spec 01 vs Model Notebook**:
  Daftar 32 fitur yang tercatat di tabel [specs/01-feature-extraction.md (L421-L454)](file:///Users/michaelarhdyn/Library/CloudStorage/GoogleDrive-23.michaelaristio@gmail.com/My%20Drive/Project%20Michael/Lomba%20Kompres/ai_guard_kompres/specs/01-feature-extraction.md#L421-L454) **TIDAK COCOK** dengan 32 fitur yang sebenarnya dipakai saat training di [models/01-xgboost-training/01-xgboost_metadata.json](file:///Users/michaelarhdyn/Library/CloudStorage/GoogleDrive-23.michaelaristio@gmail.com/My%20Drive/Project%20Michael/Lomba%20Kompres/ai_guard_kompres/models/01-xgboost-training/01-xgboost_metadata.json#L5-L38) dan notebook:
  - *Fitur di Spec 01*: `request_method`, `url_parameter_count`, `url_special_char_count`, `payload_entropy`, `combined_entropy`, `payload_has_sql_keywords`, `payload_has_xss_tags`, `payload_has_path_traversal`, `payload_has_crlf`, `payload_has_ssi`, `url_has_double_encoding`, `url_has_null_byte`, `referer_header_present`, `user_agent_unusual`, `content_type_missing`, `max_consecutive_special_chars`, `normalized_url_length`, `number_of_encoded_chars`, `has_long_parameter_name`, `has_empty_parameter`, `method_not_allowed`, `url_directory_depth`, `has_server_side_number`, `content_type_application_form`, `cookie_value_length`, `accept_header_present`, `host_header_present`.
  - *Fitur Aktual di Model & Notebook*: `url_length`, `path_length`, `query_string_length`, `body_length`, `num_headers`, `num_params`, `avg_param_name_length`, `avg_param_value_length`, `max_param_value_length`, `max_param_name_length`, `std_param_value_length`, `url_entropy`, `body_entropy`, `param_value_max_entropy`, `digit_ratio`, `uppercase_ratio`, `special_char_ratio`, `alpha_ratio`, `whitespace_count`, `non_printable_count`, `sql_keyword_count`, `xss_keyword_count`, `path_traversal_count`, `crlf_injection_count`, `cmd_injection_count`, `file_inclusion_count`, `encoded_char_count`, `method_is_get`, `method_is_post`, `has_cookie_header`, `has_content_type_header`, `content_length_mismatch`.
  - **Kesimpulan**: Feature Extractor yang wajib diimplementasikan untuk Spec 03 adalah versi **32 fitur dari notebook & metadata**, bukan versi tabel Spec 01, agar sesuai dengan bobot model yang sudah dilatih.

---

## 3. Hasil Verifikasi Dependency Step 2 (Model Training)

### 3.1 Status Keberadaan Artifact Model & Metadata
- `models/xgboost_model.pkl`: **TIDAK ADA** di path ini.
  - *Lokasi Aktual*: [models/01-xgboost-training/01-xgboost_model.pkl](file:///Users/michaelarhdyn/Library/CloudStorage/GoogleDrive-23.michaelaristio@gmail.com/My%20Drive/Project%20Michael/Lomba%20Kompres/ai_guard_kompres/models/01-xgboost-training/01-xgboost_model.pkl) (Ukuran: 1.655.908 bytes / ~1.65 MB).
- `models/xgboost_metadata.json`: **TIDAK ADA** di path ini.
  - *Lokasi Aktual*: [models/01-xgboost-training/01-xgboost_metadata.json](file:///Users/michaelarhdyn/Library/CloudStorage/GoogleDrive-23.michaelaristio@gmail.com/My%20Drive/Project%20Michael/Lomba%20Kompres/ai_guard_kompres/models/01-xgboost-training/01-xgboost_metadata.json) (Ukuran: 4.686 bytes).

### 3.2 Tipe Model & Jumlah Kelas
- Berdasarkan inspeksi opcode biner pickle (`pickletools`):
  - Model class: `xgboost.sklearn.XGBClassifier`
  - Parameter `objective`: `'binary:logistic'`
  - Parameter `n_classes_`: `2`
- Berdasarkan metadata ([models/01-xgboost-training/01-xgboost_metadata.json](file:///Users/michaelarhdyn/Library/CloudStorage/GoogleDrive-23.michaelaristio@gmail.com/My%20Drive/Project%20Michael/Lomba%20Kompres/ai_guard_kompres/models/01-xgboost-training/01-xgboost_metadata.json#L51)) dan notebook cell 31:
  - `set(np.unique(y)) <= {0, 1}` (0 = normal, 1 = anomalous)
  - Evaluasi metrik biner: `precision_normal`, `precision_anomalous`, dll.
- **Kesimpulan**: Model adalah **BINARY CLASSIFIER MURNI**. Model tidak memiliki kemampuan bawaan untuk membedakan kategori serangan secara multi-class.

### 3.3 Kelengkapan Metadata JSON untuk Endpoint API
- **Untuk `/health`**:
  - Field `version` ada pada metadata: `"version": "1.0.0"`. Ini siap dikonsumsi langsung oleh `/health`.
- **Untuk `/metrics`**:
  - Metadata menyediakan metrik evaluasi model offline:
    - `accuracy`: 0.9791 (97.91%)
    - `roc_auc`: 0.9977
    - `precision_normal`: 0.9762 | `recall_normal`: 0.9961 | `f1_normal`: 0.9861
    - `precision_anomalous`: 0.9881 | `recall_anomalous`: 0.9304 | `f1_anomalous`: 0.9584
    - `suggested_threshold`: 0.23
  - *Perbedaan dengan Skema Spec 03*: Endpoint `/metrics` pada Spec 03 mengharapkan gabungan metrik model (`accuracy`, `precision`, `recall`, `f1_score`) dan runtime statistics (`total_predictions`, `normal_count`, `anomalous_count`, `average_latency_ms`). Metadata JSON hanya menyimpan evaluasi statis; statistik runtime harus diakumulasikan secara dinamis di memory aplikasi API (`app.state`).

### 3.4 Ketersediaan Mapping / Classifier `attack_class`
- **Apakah ada model atau label encoder attack type di Step 2?**: **TIDAK ADA**.
  - Pipeline di [notebooks/01-xgboost-training.ipynb](file:///Users/michaelarhdyn/Library/CloudStorage/GoogleDrive-23.michaelaristio@gmail.com/My%20Drive/Project%20Michael/Lomba%20Kompres/ai_guard_kompres/notebooks/01-xgboost-training.ipynb) hanya memetakan 3 file dataset CSIC 2010 ke 2 label:
    - `normalTrafficTraining.txt` -> `normal`
    - `normalTrafficTest.txt` -> `normal`
    - `anomalousTrafficTest.txt` -> `anomalous`
  - Dokumen sprint backlog [backlog/week-1.md (L12)](file:///Users/michaelarhdyn/Library/CloudStorage/GoogleDrive-23.michaelaristio@gmail.com/My%20Drive/Project%20Michael/Lomba%20Kompres/ai_guard_kompres/backlog/week-1.md#L12) menyatakan:
    > *"Kelas yang dapat diprediksi hanya bersifat biner yaitu kelas anomalous dan normal saja, jika kelas anomalous mau dijabarkan lagi jadi serangan apa saja kayaknya cukup sulit karena kelasnya pasti terlalu banyak."*
  - Oleh karena itu, Spec 03 mencantumkan `attack_class = "sql_injection"` dengan tanda komentar `# Placeholder`. Semua jenis anomali (XSS, Path Traversal, CRLF, Command Injection) akan salah teridentifikasi sebagai SQL Injection jika placeholder ini dibiarkan.

---

## 4. Dependency & Environment Check

### 4.1 Ketersediaan Library
| Library yang Dibutuhkan Spec 03 | Status di Environment Lokal | Status di Requirements File |
|---|---|---|
| `fastapi` | ❌ Belum terpasang | ❌ Tidak ada `requirements.txt` |
| `uvicorn` | ❌ Belum terpasang | ❌ Tidak ada `requirements.txt` |
| `pydantic` | ❌ Belum terpasang | ❌ Tidak ada `requirements.txt` |
| `joblib` | ❌ Belum terpasang | ❌ Tidak ada `requirements.txt` |
| `xgboost` | ❌ Belum terpasang | ❌ Tidak ada `requirements.txt` |
| `scikit-learn` | ❌ Belum terpasang | ❌ Tidak ada `requirements.txt` |
| `numpy` | ✅ Terpasang (v2.5.2) | ❌ Tidak ada `requirements.txt` |
| `pandas` | ✅ Terpasang (v3.0.5) | ❌ Tidak ada `requirements.txt` |

### 4.2 Versi Python
- **Requirement Proyek**: `Python 3.10+` (sesuai [specs/00-overview.md](file:///Users/michaelarhdyn/Library/CloudStorage/GoogleDrive-23.michaelaristio@gmail.com/My%20Drive/Project%20Michael/Lomba%20Kompres/ai_guard_kompres/specs/00-overview.md#L58)) dan base image Docker `python:3.10-slim` (sesuai [specs/09-docker-deployment.md](file:///Users/michaelarhdyn/Library/CloudStorage/GoogleDrive-23.michaelaristio@gmail.com/My%20Drive/Project%20Michael/Lomba%20Kompres/ai_guard_kompres/specs/09-docker-deployment.md#L33)).
- **Versi Python di Host Machine**:
  - `/Library/Frameworks/Python.framework/Versions/Current/bin/python3`: **Python 3.14.6**
  - `/usr/bin/python3`: **Python 3.9.6**
- **Perhatian Khusus**: Python 3.14 merupakan versi sangat baru / pra-rilis. Banyak library C-extension seperti `xgboost` dan `scikit-learn` belum memiliki pre-compiled binary wheel yang stabil untuk Python 3.14. Sebaiknya gunakan environment virtual (venv/conda) berbasis Python 3.10 atau 3.11.

---

## 5. Gap & Inkonsistensi Ditemukan

Berikut adalah daftar gap yang ditemukan, diurutkan berdasarkan prioritas:

1. **[Prioritas 1 — Kritis / Blocker] Ketiadaan Modul `src/feature_extraction`**  
   File `parser.py` dan `extractor.py` belum diekstrak dari notebook ke modul Python mandiri di bawah `src/`. Tanpa modul ini, API tidak dapat dijalankan.
2. **[Prioritas 1 — Kritis / Logic Flaw] `query_params` Dikosongkan pada Endpoint `/predict`**  
   Snippet implementasi Spec 03 mengabaikan parsing query parameters dan meng-hardcode `'query_params': {}`. Padahal fitur `max_param_name_length`, `num_params`, dan `avg_param_name_length` adalah 3 fitur dengan bobot kepentingan tertinggi pada model (mencakup 61% bobot XGBoost). Hal ini akan menyebabkan akurasi prediksi inference API menyimpang drastis dari hasil training.
3. **[Prioritas 2 — Tinggi] Path Artifact Model Tidak Sesuai**  
   Kode Spec 03 memanggil `"models/xgboost_model.pkl"` dan `"models/xgboost_metadata.json"`. Sedangkan file fisik berada di `"models/01-xgboost-training/01-xgboost_model.pkl"` dan `"models/01-xgboost-training/01-xgboost_metadata.json"`.
4. **[Prioritas 2 — Tinggi] `attack_class` Ter-hardcode `"sql_injection"`**  
   Model hanya menghasilkan binary classification (`anomalous` / `normal`). Karena tidak ada multi-class model dari Step 2, response `attack_class` saat ini selalu `"sql_injection"`, yang keliru untuk serangan jenis XSS, Path Traversal, CRLF, dsb.
5. **[Prioritas 2 — Tinggi] Ketiadaan File Manajemen Dependensi**  
   Repo belum memiliki file `requirements.txt` atau `requirements-inference.txt` untuk menginstal `fastapi`, `uvicorn`, `pydantic`, `joblib`, `xgboost`, `scikit-learn`.
6. **[Prioritas 3 — Sedang] Inkonsistensi Definisi Fitur Antara Dokumen Spec 01 dan Model Aktual**  
   Dokumen markdown `specs/01-feature-extraction.md` masih mencantumkan nama dan jenis 32 fitur yang berbeda dari apa yang sebenarnya diterapkan di notebook `01-xgboost-training.ipynb` dan `01-xgboost_metadata.json`.
7. **[Prioritas 3 — Sedang] Akumulasi Metrik Real-time pada Endpoint `/metrics`**  
   Spec 03 `/metrics` menggabungkan model performance static dengan counter live request (`total_predictions`, `average_latency_ms`). Diperlukan in-memory tracker pada state FastAPI saat implementasi.

---

## 6. Pertanyaan Terbuka untuk Didiskusikan Sebelum Coding

Sebelum menulis kode implementasi Spec 03, keputusan berikut harus disepakati:

1. **Strategi Penentuan `attack_class`**:
   Karena model ML hanya biner (`normal` vs `anomalous`), bagaimana `attack_class` sebaiknya ditentukan pada respon API jika request terdeteksi anomalous?
   - **Opsi A (Heuristic Signature Matching - Direkomendasikan)**: Gunakan nilai fitur deteksi signature yang sudah ada di FeatureExtractor (`sql_keyword_count`, `xss_keyword_count`, `path_traversal_count`, `crlf_injection_count`, `cmd_injection_count`, `file_inclusion_count`). Jika salah satu > 0, set label serangan sesuai keyword yang dominan. Jika tidak ada keyword yang cocok, set `"anomalous_payload"` atau `"unknown_anomaly"`.
   - **Opsi B (Null / Generic)**: Kembalikan `attack_class: null` atau `attack_class: "anomalous"` dan ubah schema `PredictionResponse` agar jujur bahwa klasifikasi saat ini murni biner.
   - **Opsi C (Retrain Multi-class)**: Kembali ke Step 2 dan melatih model multi-class terpisah (membutuhkan waktu & relabeling dataset).
2. **Resolusi Path Artifact Model**:
   Apakah kita:
   - **Opsi A**: Mengubah path di kode Spec 03 agar membaca dari `models/01-xgboost-training/01-xgboost_model.pkl` dan `models/01-xgboost-training/01-xgboost_metadata.json`, ATAU
   - **Opsi B**: Menyalin/membuat symlink artifact tersebut ke root folder `models/xgboost_model.pkl` dan `models/xgboost_metadata.json`?
3. **Perbaikan Parsing Parameter di `/predict`**:
   Apakah diizinkan mengintegrasikan helper URL query & body parameter parser (dari `HTTPRequestParser`) ke dalam endpoint `/predict` agar `query_params` terisi dengan benar dan fitur `max_param_name_length` / `num_params` dapat dihitung akurat?
4. **Sumber Kebenaran Feature Extractor**:
   Apakah disepakati bahwa implementasi `FeatureExtractor` dan `HTTPRequestParser` yang akan dibuat di `src/feature_extraction/` harus mengacu 100% pada kode yang ada di cell 6-8 & cell 29 [notebooks/01-xgboost-training.ipynb](file:///Users/michaelarhdyn/Library/CloudStorage/GoogleDrive-23.michaelaristio@gmail.com/My%20Drive/Project%20Michael/Lomba%20Kompres/ai_guard_kompres/notebooks/01-xgboost-training.ipynb) (karena model dilatih dengan logika tersebut)?
5. **Standar Lingkungan Python**:
   Apakah tim ingin mengelola dependensi melalui `requirements.txt` di root repo atau `requirements-inference.txt` (sesuai konvensi Docker di Spec 09)?

---

## 7. Rekomendasi Langkah Selanjutnya

Urutan tindakan konkret sebelum dan saat mulai membangun Spec 03:

```
[Langkah 1: Klarifikasi Keputusan Desain]
  - Putuskan penanganan attack_class (Opsi A Heuristic disarankan)
  - Sepakati perbaikan parsing query_params di /predict
  - Sepakati standardisasi path model artifact
         │
         ▼
[Langkah 2: Setup Environment & Dependencies]
  - Buat file requirements.txt / requirements-inference.txt
    (fastapi, uvicorn, pydantic, joblib, xgboost, scikit-learn, numpy)
  - Setup virtual environment Python 3.10 atau 3.11
         │
         ▼
[Langkah 3: Modularisasi Step 1 (Feature Extraction)]
  - Buat folder src/feature_extraction/
  - Ekstrak HTTPRequestParser ke src/feature_extraction/parser.py
  - Ekstrak FeatureExtractor (32 fitur versi notebook) ke src/feature_extraction/extractor.py
  - Buat regex pattern constants di src/feature_extraction/patterns.py
  - Buat unit test src/feature_extraction/test_extractor.py untuk memastikan output 32 fitur konsisten
         │
         ▼
[Langkah 4: Harmonisasi Model Artifact]
  - Sinkronkan lokasi model pkl dan metadata json (atau buat symlink/copy ke models/xgboost_model.pkl)
         │
         ▼
[Langkah 5: Implementasi Spec 03 (Inference API)]
  - Buat src/api/schemas.py (SingleRequest, PredictionResponse, BatchRequest, HealthResponse)
  - Buat src/api/dependencies.py (model loading & state check)
  - Buat src/api/routes.py (/predict, /predict-batch, /health, /metrics)
  - Buat src/api/main.py (lifespan event, router inclusion)
  - Implementasikan perbaikan query_params parsing & heuristic attack_class
         │
         ▼
[Langkah 6: Pengujian & Validasi End-to-End]
  - Uji response schema dan status code (200, 400, 503)
  - Uji latensi endpoint < 100ms
  - Uji batch prediction
```
