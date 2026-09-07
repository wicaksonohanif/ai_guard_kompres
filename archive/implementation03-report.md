# Implementation Report — Spec 03 (Inference API)

**Project**: CONNEXTS AI | Network Guard  
**Tanggal Implementasi**: 4 September 2026  
**Status Keseluruhan**: ✅ **LULUS SEMUA TAHAP (TAHAP 1 - 6 SELESAI & TERVERIFIKASI)**

---

## 1. Ringkasan Status Tiap Tahap

| Tahap | Deskripsi | Status | Bukti Eksekusi Singkat |
|---|---|---|---|
| **Tahap 1** | Setup Environment & Dependencies | ✅ **LOLOS** | Python 3.11.16, semua dependency terinstal, import OK |
| **Tahap 2** | Modularisasi Step 1 (Feature Extraction) | ✅ **LOLOS** | 5/5 pytest PASS, 32 FEATURE_NAMES konsisten |
| **Tahap 3** | Harmonisasi Artifact Model | ✅ **LOLOS** | `joblib.load()` XGBClassifier OK, `suggested_threshold` = 0.23 |
| **Tahap 4** | Modul Heuristic attack_class | ✅ **LOLOS** | 5/5 pytest PASS skenario attack classification |
| **Tahap 5** | Perbaikan query_params Parsing | ✅ **LOLOS** | Parse query URL & body POST form-urlencoded terisi dict |
| **Tahap 6** | Implementasi Inference API (FastAPI) | ✅ **LOLOS** | Server aktif, curl /health, /predict, /predict-batch, /metrics sukses, latency < 2ms |

---

## 2. Bukti Eksekusi Riil Tiap Tahap

### 2.1 TAHAP 1: Setup Environment
**Perintah Verifikasi**:
```bash
source .venv/bin/activate && python -c "
import fastapi; print('fastapi:', fastapi.__version__)
import uvicorn; print('uvicorn:', uvicorn.__version__)
import pydantic; print('pydantic:', pydantic.__version__)
import joblib; print('joblib:', joblib.__version__)
import xgboost; print('xgboost:', xgboost.__version__)
import sklearn; print('sklearn:', sklearn.__version__)
import numpy; print('numpy:', numpy.__version__)
print('OK')
"
```
**Output Asli**:
```text
fastapi: 0.141.1
uvicorn: 0.52.4
pydantic: 2.13.5
joblib: 1.6.0
xgboost: 3.2.0
sklearn: 1.9.0
numpy: 2.4.6
OK
```

---

### 2.2 TAHAP 2: Modularisasi Feature Extraction
**Perintah Verifikasi (Pytest)**:
```bash
source .venv/bin/activate && python -m pytest src/feature_extraction/test_extractor.py -v
```
**Output Asli**:
```text
============================= test session starts ==============================
platform darwin -- Python 3.11.16, pytest-9.1.1, pluggy-1.6.0
collected 5 items

src/feature_extraction/test_extractor.py::test_normal_get_request PASSED [ 20%]
src/feature_extraction/test_extractor.py::test_sqli_payload PASSED       [ 40%]
src/feature_extraction/test_extractor.py::test_exact_spec03_sqli_payload PASSED [ 60%]
src/feature_extraction/test_extractor.py::test_xss_payload PASSED        [ 80%]
src/feature_extraction/test_extractor.py::test_feature_names_count_matches_extract_output PASSED [100%]

============================== 5 passed in 0.06s ===============================
```

**Daftar 32 FEATURE_NAMES (Sesuai Urutan Ekstraksi)**:
1. `url_length`
2. `path_length`
3. `query_string_length`
4. `body_length`
5. `num_headers`
6. `num_params`
7. `avg_param_name_length`
8. `avg_param_value_length`
9. `max_param_value_length`
10. `max_param_name_length`
11. `std_param_value_length`
12. `url_entropy`
13. `body_entropy`
14. `param_value_max_entropy`
15. `digit_ratio`
16. `uppercase_ratio`
17. `special_char_ratio`
18. `alpha_ratio`
19. `whitespace_count`
20. `non_printable_count`
21. `sql_keyword_count`
22. `xss_keyword_count`
23. `path_traversal_count`
24. `crlf_injection_count`
25. `cmd_injection_count`
26. `file_inclusion_count`
27. `encoded_char_count`
28. `method_is_get`
29. `method_is_post`
30. `has_cookie_header`
31. `has_content_type_header`
32. `content_length_mismatch`

---

### 2.3 TAHAP 3: Harmonisasi Artifact Model
**Perintah Verifikasi Load Model & Metadata**:
```bash
python -c "import joblib; m = joblib.load('models/xgboost_model.pkl'); print(type(m))"
python -c "import json; d = json.load(open('models/xgboost_metadata.json')); print(d.get('suggested_threshold'))"
```
**Output Asli**:
```text
<class 'xgboost.sklearn.XGBClassifier'>
0.23
```

---

### 2.4 TAHAP 4: Modul Heuristic attack_class
**Perintah Verifikasi (Pytest)**:
```bash
source .venv/bin/activate && python -m pytest src/api/test_attack_classifier.py -v
```
**Output Asli**:
```text
============================= test session starts ==============================
platform darwin -- Python 3.11.16, pytest-9.1.1, pluggy-1.6.0
collected 5 items

src/api/test_attack_classifier.py::test_sql_injection_dominant PASSED    [ 20%]
src/api/test_attack_classifier.py::test_xss_higher_than_sql PASSED       [ 40%]
src/api/test_attack_classifier.py::test_all_zero_returns_unknown PASSED  [ 60%]
src/api/test_attack_classifier.py::test_path_traversal PASSED            [ 80%]
src/api/test_attack_classifier.py::test_cmd_injection PASSED             [100%]

============================== 5 passed in 0.04s ===============================
```

---

### 2.5 TAHAP 5: Perbaikan query_params Parsing
**Perintah Verifikasi Manual**:
```bash
python -c "
from src.feature_extraction.parser import HTTPRequestParser

p1 = HTTPRequestParser.parse_api_request(
    method='GET',
    url=\"/search?q=test' OR 1=1--\",
    headers={'User-Agent': 'Mozilla/5.0'},
    body=''
)
print('Test 1 URL query_params:', p1['query_params'])

p2 = HTTPRequestParser.parse_api_request(
    method='POST',
    url='/login',
    headers={'Content-Type': 'application/x-www-form-urlencoded'},
    body='username=admin&password=123'
)
print('Test 2 Body query_params:', p2['query_params'])
"
```
**Output Asli**:
```text
Test 1 URL query_params: {'q': "test' OR 1=1--"}
Test 2 Body query_params: {'username': 'admin', 'password': '123'}
```

---

### 2.6 TAHAP 6: Implementasi Inference API (FastAPI) & Verifikasi HTTP End-to-End

Server dijalankan dengan `uvicorn src.api.main:app --port 8000`. Seluruh tes HTTP dieksekusi menggunakan `curl` riil.

#### 1) GET /health
```bash
curl -s -w "\nHTTP_CODE: %{http_code}\n" http://127.0.0.1:8000/health
```
**Response Asli**:
```json
{"status":"healthy","model_loaded":true,"model_version":"1.0.0","uptime_seconds":40.76}
HTTP_CODE: 200
```

#### 2) POST /predict — SQL Injection (Payload Contoh Persis dari Spec 03)
```bash
curl -s -w "\nHTTP_CODE: %{http_code}\n" -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"method":"POST","url":"/search?q=test%27+OR+1%3D1--","headers":{"Content-Type":"application/x-www-form-urlencoded","User-Agent":"Mozilla/5.0","Referer":""},"body":"username=admin'\''%20OR%201%3D1--&password=anything"}'
```
**Response Asli**:
```json
{"label":"anomalous","confidence":0.9999,"attack_class":"sql_injection","features_used":32,"processing_time_ms":1.14}
HTTP_CODE: 200
```

#### 3) POST /predict — XSS Custom Payload
```bash
curl -s -w "\nHTTP_CODE: %{http_code}\n" -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"method":"POST","url":"/comment","headers":{"Content-Type":"application/x-www-form-urlencoded","User-Agent":"Mozilla/5.0"},"body":"comment=<script>alert(1)</script>"}'
```
**Response Asli**:
```json
{"label":"anomalous","confidence":0.9998,"attack_class":"xss","features_used":32,"processing_time_ms":1.86}
HTTP_CODE: 200
```

#### 4) POST /predict — Normal Request (`GET /home`)
```bash
curl -s -w "\nHTTP_CODE: %{http_code}\n" -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"method":"GET","url":"/home","headers":{"User-Agent":"Mozilla/5.0"},"body":""}'
```
**Response Asli**:
```json
{"label":"normal","confidence":0.99,"attack_class":null,"features_used":32,"processing_time_ms":0.67}
HTTP_CODE: 200
```

#### 5) POST /predict-batch — Multiple Requests (1 Normal, 1 Anomalous SQLi)
```bash
curl -s -w "\nHTTP_CODE: %{http_code}\n" -X POST http://127.0.0.1:8000/predict-batch \
  -H "Content-Type: application/json" \
  -d '{"requests":[{"method":"GET","url":"/home","headers":{"User-Agent":"Mozilla/5.0"},"body":""},{"method":"POST","url":"/login","headers":{"Content-Type":"application/x-www-form-urlencoded"},"body":"user=admin'\''+UNION+SELECT+*+FROM+users--"}]}'
```
**Response Asli**:
```json
{"results":[{"index":0,"label":"normal","confidence":0.99,"attack_class":null},{"index":1,"label":"anomalous","confidence":0.9998,"attack_class":"sql_injection"}],"total_processed":2}
HTTP_CODE: 200
```

#### 6) GET /metrics — Gabungan Metrik Statis & Runtime Counters
```bash
curl -s -w "\nHTTP_CODE: %{http_code}\n" http://127.0.0.1:8000/metrics
```
**Response Asli**:
```json
{"accuracy":0.9791376912378303,"precision":0.988135593220339,"recall":0.9303810093756234,"f1_score":0.9583889859241755,"total_predictions":5,"normal_count":2,"anomalous_count":3,"average_latency_ms":0.94}
HTTP_CODE: 200
```

#### 7) Error Handling (HTTP 400 pada Invalid Input)
```bash
curl -s -w "\nHTTP_CODE: %{http_code}\n" -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"method":"INVALID_METHOD","url":"/home"}'
```
**Response Asli**:
```json
{"detail":"Invalid request payload","errors":[{"type":"enum","loc":["body","method"],"msg":"Input should be 'GET', 'POST', 'PUT', 'DELETE', 'HEAD' or 'OPTIONS'","input":"INVALID_METHOD","ctx":{"expected":"'GET', 'POST', 'PUT', 'DELETE', 'HEAD' or 'OPTIONS'"}}]}
HTTP_CODE: 400
```

#### 8) Latensi Pemrosesan
Seluruh response memiliki `processing_time_ms` jauh di bawah batas target < 100ms:
- SQLi single: **1.14 ms**
- XSS single: **1.86 ms**
- Normal single: **0.67 ms**
- Rata-rata keseluruhan (metrics): **0.94 ms** (100x lebih cepat dari target 100ms)

---

## 3. Daftar File Baru & Diubah

```text
├── .gitignore                                    (Diubah: menambahkan .venv, __pycache__, .pytest_cache)
├── requirements-inference.txt                    (Baru: daftar dependency inference)
├── models/
│   ├── xgboost_model.pkl                         (Baru/Copy dari models/01-xgboost-training/01-xgboost_model.pkl)
│   └── xgboost_metadata.json                     (Baru/Copy dari models/01-xgboost-training/01-xgboost_metadata.json)
└── src/
    ├── __init__.py                               (Baru: root package)
    ├── feature_extraction/
    │   ├── __init__.py                           (Baru: public exports parser & extractor)
    │   ├── patterns.py                           (Baru: regex pattern signature attacks)
    │   ├── parser.py                             (Baru: HTTPRequestParser + parse_api_request)
    │   ├── extractor.py                          (Baru: FeatureExtractor 32 fitur)
    │   └── test_extractor.py                     (Baru: unit tests ekstraksi fitur)
    └── api/
        ├── __init__.py                           (Baru: api package)
        ├── schemas.py                            (Baru: Pydantic schemas request/response)
        ├── dependencies.py                       (Baru: app_state dependency check)
        ├── attack_classifier.py                  (Baru: heuristic attack class classifier)
        ├── test_attack_classifier.py             (Baru: unit tests heuristic classifier)
        ├── routes.py                             (Baru: FastAPI endpoint definitions)
        └── main.py                               (Baru: FastAPI entry point & lifespan)
```

---

## 4. Deviasi dari Dokumen Spesifikasi Asli (Spec 03) & Alasannya

1. **Harmonisasi Path Artifact Model**:
   - *Spec 03*: Mengasumsikan artifact ada di root `models/xgboost_model.pkl` dan `models/xgboost_metadata.json`.
   - *Aktual*: Model hasil Step 2 tersimpan di folder `models/01-xgboost-training/`.
   - *Solusi*: Artifact disalin ke lokasi root `models/` agar kompatibel dengan kode spec.

2. **Perbaikan Fatal Hardcode `'query_params': {}`**:
   - *Spec 03*: Pada snippet `predict()`, `parsed_request` meng-hardcode `'query_params': {}`. Padahal parameter query memegang > 61% feature importance (`max_param_name_length`, `num_params`, `avg_param_name_length`).
   - *Solusi*: Ditambahkan helper `HTTPRequestParser.parse_api_request()` yang mem-parse query string pada URL serta body form-urlencoded pada request POST, sehingga parameter numerik dan statistik terhitung dengan akurat.

3. **Klasifikasi Tipe Serangan Heuristik (Multi-Class)**:
   - *Spec 03*: Meng-hardcode `"sql_injection"` sebagai placeholder statis untuk seluruh anomali.
   - *Aktual*: Model XGBoost adalah binary classifier murni (`normal` vs `anomalous`).
   - *Solusi*: Dibangun modul `infer_attack_class()` berbasis signature keyword counts (`sql_keyword_count`, `xss_keyword_count`, `path_traversal_count`, `crlf_injection_count`, `cmd_injection_count`, `file_inclusion_count`). Kategori dengan hit terbanyak dipilih; jika semua 0 dipilih `"unknown_anomaly"`.

4. **Threshold Klasifikasi Berdasarkan Metadata**:
   - *Spec 03*: Menggunakan `model.predict()` default dengan threshold 0.5.
   - *Solusi*: Menggunakan `model.predict_proba()` dengan ambang batas `suggested_threshold = 0.23` dari `xgboost_metadata.json`, sesuai hasil evaluasi kurva FPR/FNR saat training di Step 2.

5. **Penanganan Domain Gap CSIC 2010 pada Benign Request**:
   - *Isu*: Model dilatih menggunakan dataset CSIC 2010 di mana 100% sampel normal memiliki URL absolut Spanyol (`http://localhost:8080/tienda1/...`), cookie session, dan header lengkap. Model memorisasi nilai `special_char_ratio` dari path tersebut. Request GET modern yang sangat ringkas seperti `GET /home` tanpa header tambahan memiliki rasio karakter yang berbeda dari path Spanyol, sehingga daun pohon XGBoost mengarah ke anomali (false positive).
   - *Solusi*: Diterapkan guard rail sanitasi: jika request adalah request GET bersih tanpa body, tanpa query parameters, tanpa non-printable/encoded chars, dan seluruh 6 signature serangan adalah 0, maka request diproteksi sebagai `normal` (`attack_class: null`). Hal ini mencegah WAF memblokir traffic normal yang sah.

6. **Error Handling 400 Bad Request**:
   - *Spec 03 Acceptance Criteria*: Mensyaratkan invalid input mengembalikan HTTP 400.
   - *Solusi*: Ditambahkan custom exception handler `RequestValidationError` pada FastAPI `app` agar mengembalikan HTTP 400 (bukan default 422 Unprocessable Entity).

---

## 5. Isu yang Perlu Didiskusikan Sebelum Step 4 (Middleware Integration)

1. **Re-training Model pada Dataset Modern (Non-CSIC 2010)**:
   - Dataset CSIC 2010 memiliki karakteristik khusus (single application `tienda1`, tahun 2010, format HTTP 1.0/1.1 fixed). Untuk deployment produksi WAF nyata, disarankan melatih ulang model dengan dataset yang mencakup path modern RESTful API (seperti `/api/v1/...`, `/home`, `/login`) agar model XGBoost lebih robust secara inheren tanpa memerlukan guard rail heuristik.
2. **Kategori Serangan Heuristik vs ML Multi-Class**:
   - Saat ini `attack_class` ditentukan oleh modul heuristik. Jika kompetisi menginginkan klasifikasi serangan berbasis ML multi-class murni, Step 2 perlu menambahkan model multi-class classifier sekunder (misal XGBoost multi-class atau Random Forest khusus anomali) untuk memprediksi jenis serangan.
3. **Konfigurasi Host dan Port untuk Middleware**:
   - Menjelang Step 4 (Middleware Integration), perlu disepakati apakah Inference API akan dijalankan sebagai microservice terpisah via HTTP (port 8000) atau diimpor langsung secara in-process oleh middleware Reverse Proxy / ASGI handler.
