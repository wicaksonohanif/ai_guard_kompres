# Spec 01: Feature Extraction Engine

**Version**: 1.0
**Date**: 29 Agustus 2026
**Related PRD**: FR-1

---

## Tujuan

Mengekstrak fitur numerik dari setiap HTTP request masuk secara konsisten, baik pada pipeline training (dataset CSIC 2010) maupun pipeline inference (traffic live). Fungsi ekstraksi fitur harus identik di kedua pipeline.

---

## Fitur Utama

### Fetched Features

| # | Fitur | Tipe | Sumber | Deskripsi |
|---|-------|------|--------|-----------|
| 1 | `request_method` | Categorical | HTTP Method | GET, POST, PUT, DELETE, HEAD, OPTIONS |
| 2 | `url_length` | Numeric | Request URL | Panjang total URL dalam karakter |
| 3 | `url_parameter_count` | Numeric | Request URL | Jumlah query parameters (`?key=value&...`) |
| 4 | `url_special_char_count` | Numeric | Request URL | Jumlah karakter spesial (`'`, `"`, `<`, `>`, `%`, `\`, `;`, `--`, `/*`, `*/`) |
| 5 | `payload_length` | Numeric | Request Body | Panjang body payload (POST data) |
| 6 | `payload_entropy` | Numeric | Request Body | Shannon entropy dari payload string |
| 7 | `payload_has_sql_keywords` | Binary | Payload/URL | Deteksi keyword SQL (`SELECT`, `UNION`, `INSERT`, `DROP`, `UPDATE`, `DELETE`, `OR 1=1`, dll.) |
| 8 | `payload_has_xss_tags` | Binary | Payload/URL | Deteksi tag XSS (`<script>`, `javascript:`, `onerror=`, `onclick=`, dll.) |
| 9 | `payload_has_path_traversal` | Binary | Payload/URL | Deteksi path traversal (`../`, `..\\`, `/etc/passwd`) |
| 10 | `payload_has_crlf` | Binary | Payload/URL | Deteksi CRLF characters (`%0d%0a`, `\r\n`) |
| 11 | `payload_has_ssi` | Binary | Payload/URL | Deteksi SSI tags (`<!--#`, `<!--#exec`) |
| 12 | `url_has_double_encoding` | Binary | Request URL | Deteksi double URL encoding (`%25`) |
| 13 | `url_has_null_byte` | Binary | Request URL | Deteksi null byte (`%00`) |
| 14 | `referer_header_present` | Binary | HTTP Header | Apakah header Referer ada |
| 15 | `user_agent_unusual` | Binary | HTTP Header | User-Agent tidak standar atau kosong |
| 16 | `content_type_missing` | Binary | HTTP Header | Content-Type hilang pada POST request |
| 17 | `max_consecutive_special_chars` | Numeric | URL/Payload | Jumlah maksimum karakter spesial berturut-turut |
| 18 | `normalized_url_length` | Numeric | URL | URL setelah decoding |
| 19 | `number_of_encoded_chars` | Numeric | URL/Payload | Jumlah karakter yang di-encode (`%XX`) |
| 20 | `has_long_parameter_name` | Binary | URL | Parameter name > 50 karakter |
| 21 | `has_empty_parameter` | Binary | URL | Ada parameter tanpa value |
| 22 | `method_not_allowed` | Binary | HTTP Method | Method yang digunakan tidak sesuai endpoint (misal PUT pada resource read-only) |
| 23 | `url_directory_depth` | Numeric | URL | Kedalaman direktori dalam URL |
| 24 | `has_server_side_number` | Numeric | URL | Angka besar di URL (indikasi buffer overflow attempt) |
| 25 | `content_type_application_form` | Binary | HTTP Header | Content-Type `application/x-www-form-urlencoded` |

---

## Algoritma Detail

### 2.1 Shannon Entropy Calculation

```python
import math
from collections import Counter

def shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    freq = Counter(text)
    length = len(text)
    entropy = 0.0
    for count in freq.values():
        p = count / length
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy
```

### 2.2 Keyword Detection Patterns

```python
SQL_KEYWORDS = re.compile(
    r"(\b(SELECT|UNION|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|"
    r"EXEC|EXECUTE|xp_|sp_|DECLARE|CURSOR|CAST|CONVERT)\b|"
    r"(OR\s+1\s*=\s*1|AND\s+1\s*=\s*1|'\s*OR\s*'|"\s*OR\s*")",
    re.IGNORECASE
)

XSS_PATTERNS = re.compile(
    r"(<script|javascript:|on(error|click|mouseover|load|focus|blur)="
    r"|<iframe|<object|<embed|alert\(|document\.cookie|document\.location)",
    re.IGNORECASE
)

PATH_TRAVERSAL_PATTERNS = re.compile(
    r"(\.\./|\.\.\\|%2e%2e%2f|%2e%2e/|\.\.%2f|%2e%2e%5c)",
    re.IGNORECASE
)

CRLF_PATTERNS = re.compile(r"(%0d%0a|\r\n|\n|\r)", re.IGNORECASE)

SSI_PATTERNS = re.compile(r" (\<!--|#)(\s*exec|include|cmd|shell)", re.IGNORECASE)
```

### 2.3 URL Decoding

```python
from urllib.parse import unquote, unquote_plus

def normalize_url(url: str) -> str:
    """Decode URL两次以检测double encoding"""
    decoded_once = unquote_plus(url)
    decoded_twice = unquote(decoded_once)
    return decoded_twice
```

---

## Output Format

Output berupa dictionary/array numerik siap input model:

```json
{
    "request_method": 0,
    "url_length": 127,
    "url_parameter_count": 3,
    "url_special_char_count": 5,
    "payload_length": 256,
    "payload_entropy": 4.32,
    "payload_has_sql_keywords": 1,
    "payload_has_xss_tags": 0,
    "payload_has_path_traversal": 0,
    "payload_has_crlf": 0,
    "payload_has_ssi": 0,
    "url_has_double_encoding": 0,
    "url_has_null_byte": 0,
    "referer_header_present": 0,
    "user_agent_unusual": 1,
    "content_type_missing": 0,
    "max_consecutive_special_chars": 3,
    "normalized_url_length": 115,
    "number_of_encoded_chars": 8,
    "has_long_parameter_name": 0,
    "has_empty_parameter": 0,
    "method_not_allowed": 0,
    "url_directory_depth": 4,
    "has_server_side_number": 0,
    "content_type_application_form": 1
}
```

Encoding categorical:
- `request_method`: One-hot encode atau label encode (GET=0, POST=1, PUT=2, DELETE=3, HEAD=4, OPTIONS=5)

---

## Implementasi

### Lokasi File

```
src/
├── feature_extraction/
│   ├── __init__.py
│   ├── extractor.py          # Kelas utama FeatureExtractor
│   ├── patterns.py           # Regex patterns untuk keyword detection
│   ├── utilities.py          # Helper functions (entropy, normalization)
│   └── test_extractor.py     # Unit tests
```

### Interface Class

```python
class FeatureExtractor:
    """Ekstrak fitur numerik dari HTTP request."""

    def extract(self, request_data: dict) -> list[float]:
        """
        Args:
            request_data: dict dengan keys:
                - method: str (HTTP method)
                - url: str
                - headers: dict
                - body: str (empty jika GET)
        Returns:
            list[float]: array fitur numerik
        """
        raise NotImplementedError

    def get_feature_names(self) -> list[str]:
        """Return nama setiap fitur untuk interpretability."""
        raise NotImplementedError
```

### Konsistensi Pipeline

- Gunakan **class yang sama** (`FeatureExtractor`) untuk training dan inference
- Simpan instance/config extractor sebagai singleton
- Test bahwa output feature training == output feature inference untuk request yang sama

---

## Acceptance Criteria

- [ ] Semua 25 fitur terekstrak sesuai tabel di atas
- [ ] Output feature extraction identical antara pipeline training dan inference untuk input yang sama
- [ ] Unit test coverage >= 90% untuk setiap fitur
- [ ] Processing time < 5ms per request (terpisah dari latency inference)
- [ ] Feature names dapat dipetakan kembali ke deskripsi (untuk interpretability)
