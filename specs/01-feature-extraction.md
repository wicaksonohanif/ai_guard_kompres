# Spec 01: Feature Extraction Engine

**Version**: 1.1 (Updated to match sample data format)
**Date**: 31 Agustus 2026
**Related PRD**: FR-1

---

## Tujuan

Mengekstrak fitur numerik dari setiap HTTP request masuk secara konsisten, baik pada pipeline training (dataset CSIC 2010) maupun pipeline inference (traffic live). Fungsi ekstraksi fitur harus identik di kedua pipeline.

---

## Format Input Data

Dataset menggunakan **raw HTTP request log text** (format CSIC 2010 asli).

### Contoh Data Normal (`sample/raw/normal.txt`)

```
GET http://localhost:8080/tienda1/index.jsp HTTP/1.1
User-Agent: Mozilla/5.0 (compatible; Konqueror/3.5; Linux) KHTML/3.5.8 (like Gecko)
Pragma: no-cache
Cache-control: no-cache
Accept: text/xml,application/xml,...
Accept-Encoding: x-gzip, x-deflate, gzip, deflate
Accept-Charset: utf-8, utf-8;q=0.5, *;q=0.5
Accept-Language: en
Host: localhost:8080
Cookie: JSESSIONID=EA414B3E327DED6875848530C864BD8F
Connection: close

[blank line = separator antara requests]

POST http://localhost:8080/tienda1/publico/anadir.jsp HTTP/1.1
User-Agent: Mozilla/5.0 ...
Content-Type: application/x-www-form-urlencoded
Content-Length: 74
Connection: close

id=1&nombre=Jam%F3n+Ib%E9rico&precio=39&cantidad=41&B1=A%F1adir+al+carrito
```

### Contoh Data Anomalous (`sample/raw/anomalous.txt`)

```
GET http://localhost:8080/tienda1/publico/anadir.jsp?id=2&nombre=Jam%F3n+Ib%E9rico&precio=85&cantidad=%27%3B+DROP+TABLE+usuarios%3B+SELECT+*+FROM+datos+WHERE+nombre+LIKE+%27%25&B1=A%F1adir+al+carrito HTTP/1.1
User-Agent: Mozilla/5.0 ...
[headers...]
Connection: close

[dan seterusnya]
```
like somewhere.
### Karakteristik Format

| Aspek | Detail |
|-------|--------|
| Baris pertama | `METHOD full_url HTTP/version` (full URL termasuk scheme + host) |
| Headers | Key-value pairs, dipisah newline |
| Pemisah request | Double newline (`\n\n`) |
| Body (POST) | Teks setelah blank line terakhir pada block |
| Label | Ditentukan dari **nama file**: `normal.txt` → "normal", `anomalous.txt` → "anomalous" |
| Source IP | **Tidak tersedia** (hanya raw HTTP request, bukan connection log) |

---

## Langkah 1: HTTP Request Parser

Parser ini mengubah raw HTTP text menjadi dict terstruktur yang dapat diproses oleh extractor.

### Lokasi File

```
src/
├── feature_extraction/
│   ├── __init__.py
│   ├── parser.py             # HTTP request parser (NEW)
│   ├── extractor.py          # Kelas utama FeatureExtractor
│   ├── patterns.py           # Regex patterns untuk keyword detection
│   ├── utilities.py          # Helper functions (entropy, normalization)
│   └── test_extractor.py     # Unit tests
```

### HTTP Request Parser Implementation

```python
# src/feature_extraction/parser.py
import re
from typing import Optional, List


class HTTPRequestParser:
    """Parse raw HTTP request text into structured dict."""
    
    REQUEST_LINE_PATTERN = re.compile(
        r'^(GET|POST|PUT|DELETE|HEAD|OPTIONS|PATCH)\s+(\S+)\s+HTTP/\d+\.\d+$'
    )
    
    HEADER_PATTERN = re.compile(r'^([^:]+):\s*(.*)$')
    
    @staticmethod
    def parse(raw_text: str) -> Optional[dict]:
        """
        Parse a single raw HTTP request text into structured dict.
        
        Args:
            raw_text: Raw HTTP request string (one request block)
        
        Returns:
            Dict dengan keys: method, full_url, url, path, query_string,
                            query_params, headers, body, content_length
            Returns None jika parsing gagal.
        """
        if not raw_text or not raw_text.strip():
            return None
        
        lines = raw_text.split('\n')
        if not lines:
            return None
        
        # Parse request line (first line)
        request_line_match = HTTPRequestParser.REQUEST_LINE_PATTERN.match(lines[0].strip())
        if not request_line_match:
            return None
        
        method = request_line_match.group(1)
        full_url = request_line_match.group(2)
        
        # Split headers and body (separated by double newline)
        # Find the first empty line that separates headers from body
        body_start_idx = None
        headers_lines = []
        i = 1
        while i < len(lines):
            if lines[i].strip() == '':
                body_start_idx = i + 1
                break
            header_match = HTTPRequestParser.HEADER_PATTERN.match(lines[i])
            if header_match:
                headers_lines.append((header_match.group(1), header_match.group(2)))
            i += 1
        
        # Parse headers into dict
        headers = {}
        for key, value in headers_lines:
            headers[key.lower()] = value
        
        # Parse body
        body = ''
        if body_start_idx is not None and body_start_idx < len(lines):
            body = '\n'.join(lines[body_start_idx:])
        
        # Parse URL components
        parsed_url = HTTPRequestParser.parse_url(full_url)
        
        return {
            'method': method,
            'full_url': full_url,
            'url': parsed_url['url'],
            'path': parsed_url['path'],
            'query_string': parsed_url['query_string'],
            'query_params': parsed_url['query_params'],
            'headers': headers,
            'body': body,
            'content_length': int(headers.get('content-length', 0))
        }
    
    @staticmethod
    def parse_full_file(file_path: str) -> List[tuple]:
        """
        Parse an entire CSIC 2010 style file containing multiple requests.
        
        Args:
            file_path: Path to .txt file with multiple HTTP requests separated by blank lines
        
        Returns:
            List of dicts, each representing one parsed HTTP request
        """
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        # Split by double newline (blank line separator between requests)
        blocks = re.split(r'\n\s*\n', content)
        
        parsed_requests = []
        for block in blocks:
            parsed = HTTPRequestParser.parse(block)
            if parsed is not None:
                parsed_requests.append(parsed)
        
        return parsed_requests
    
    @staticmethod
    def parse_url(full_url: str) -> dict:
        """
        Parse full URL into components.
        
        Examples from sample data:
            http://localhost:8080/tienda1/index.jsp
            http://localhost:8080/tienda1/publico/anadir.jsp?id=1&nombre=Jam%F3n+Ib%E9rico&precio=39
        """
        from urllib.parse import urlparse, parse_qs, unquote_plus
        
        try:
            parsed = urlparse(full_url)
            
            # Normalize: remove fragment, keep query
            url_path = parsed.path
            
            # Handle case where full_url IS the path (no scheme/host)
            if not parsed.scheme:
                # Could be relative URL like "/tienda1/index.jsp?param=value"
                url_path = full_url.split('?')[0] if '?' in full_url else full_url
                query_string = full_url.split('?', 1)[1] if '?' in full_url else ''
            else:
                query_string = parsed.query
            
            query_params = parse_qs(query_string, keep_blank_values=True)
            # Flatten single-value params
            flat_params = {}
            for k, v in query_params.items():
                flat_params[k] = v[0] if len(v) == 1 else v
            
            return {
                'url': full_url if parsed.scheme else f"{parsed.scheme}//{parsed.netloc}{url_path}",
                'path': url_path if parsed.scheme else ('/' + full_url.split('?')[0] if '?' in full_url else full_url),
                'query_string': query_string,
                'query_params': flat_params,
                'scheme': parsed.scheme if parsed.scheme else '',
                'host': parsed.hostname if parsed.hostname else '',
                'port': parsed.port if parsed.port else 80
            }
        except Exception:
            return {
                'url': full_url,
                'path': '/',
                'query_string': '',
                'query_params': {},
                'scheme': '',
                'host': '',
                'port': 80
            }
```

### Sample Usage

```python
from feature_extraction.parser import HTTPRequestParser

# Parse single request
raw_request = """GET http://localhost:8080/tienda1/index.jsp HTTP/1.1
User-Agent: Mozilla/5.0 (compatible; Konqueror/3.5; Linux)
Host: localhost:8080
Cookie: JSESSIONID=ABC123
Connection: close"""

parsed = HTTPRequestParser.parse(raw_request)
print(parsed)
# Output:
# {
#     'method': 'GET',
#     'full_url': 'http://localhost:8080/tienda1/index.jsp',
#     'url': 'http://localhost:8080/tienda1/index.jsp',
#     'path': '/tienda1/index.jsp',
#     'query_string': '',
#     'query_params': {},
#     'headers': {'user-agent': 'Mozilla/5.0...', 'host': 'localhost:8080', 
#                 'cookie': 'JSESSIONID=ABC123', 'connection': 'close'},
#     'body': '',
#     'content_length': 0
# }

# Parse POST request with body
raw_post = """POST http://localhost:8080/tienda1/publico/anadir.jsp HTTP/1.1
User-Agent: Mozilla/5.0
Content-Type: application/x-www-form-urlencoded
Content-Length: 74
Connection: close

id=1&nombre=Jam%F3n+Ib%E9rico&precio=39&cantidad=41&B1=A%F1adir+al+carrito"""

parsed_post = HTTPRequestParser.parse(raw_post)
print(parsed_post['body'])
# Output: 'id=1&nombre=Jam%F3n+Ib%E9rico&precio=39&cantidad=41&B1=A%F1adir+al+carrito'

# Parse entire file (batch mode)
requests = HTTPRequestParser.parse_full_file('sample/raw/normal.txt')
print(f"Parsed {len(requests)} requests")
# Output: Parsed 3 requests

# For anomalous file
anomalous_requests = HTTPRequestParser.parse_full_file('sample/raw/anomalous.txt')
print(f"Parsed {len(anomalous_requests)} anomalous requests")
```

---

## Langkah 2: Dataset Loader (Training Pipeline Only)

Untuk membaca dan menyiapkan dataset CSIC 2010 saat training.

```python
# src/feature_extraction/dataset_loader.py
import os
import pandas as pd
from typing import Tuple, List
from .parser import HTTPRequestParser


class CSICDatasetLoader:
    """Load and prepare CSIC 2010 dataset for training."""
    
    def __init__(self, data_dir: str, output_format: str = 'pandas'):
        """
        Args:
            data_dir: Directory containing normal.txt and anomalous.txt
            output_format: 'pandas' untuk DataFrame, 'features' untuk array numpy
        """
        self.data_dir = data_dir
        self.output_format = output_format
    
    def load(self) -> pd.DataFrame:
        """
        Load both normal and anomalous files, parse, add labels, combine.
        
        Returns:
            DataFrame dengan kolom:
            - parsed_json: dict hasil parsing HTTP request
            - label: 'normal' atau 'anomalous'
            - filename: nama file sumber
        """
        records = []
        
        for filename in ['normal.txt', 'anomalous.txt']:
            filepath = os.path.join(self.data_dir, filename)
            if not os.path.exists(filepath):
                print(f"Warning: {filepath} not found, skipping.")
                continue
            
            label = 'normal' if 'normal' in filename else 'anomalous'
            
            # Parse all requests in file
            parsed_list = HTTPRequestParser.parse_full_file(filepath)
            
            for parsed in parsed_list:
                records.append({
                    'parsed_json': parsed,
                    'label': label,
                    'filename': filename
                })
        
        df = pd.DataFrame(records)
        print(f"Loaded {len(df)} total requests ({df['label'].value_counts().to_dict()})")
        return df
    
    def extract_features(self, df: pd.DataFrame, feature_extractor) -> Tuple:
        """
        Extract features from parsed dataframe.
        
        Args:
            df: DataFrame from load()
            feature_extractor: FeatureExtractor instance
        
        Returns:
            X: np.ndarray shape (n_samples, n_features)
            y: np.ndarray shape (n_samples,) labels (0=normal, 1=anomalous)
            feature_names: list[str]
        """
        features = []
        labels = []
        failures = 0
        
        for _, row in df.iterrows():
            try:
                feat = feature_extractor.extract(row['parsed_json'])
                features.append(feat)
                labels.append(1 if row['label'] == 'anomalous' else 0)
            except Exception as e:
                failures += 1
                continue
        
        import numpy as np
        X = np.array(features)
        y = np.array(labels)
        feature_names = feature_extractor.get_feature_names()
        
        print(f"Extracted {len(X)} features successfully ({failures} failures)")
        print(f"Shape: X={X.shape}, y={y.shape}")
        print(f"Class distribution: {dict(zip(*np.unique(y, return_counts=True)))}")
        
        return X, y, feature_names
```

### Sample Usage (Training)

```python
from feature_extraction.dataset_loader import CSICDatasetLoader
from feature_extraction.extractor import FeatureExtractor

# Load dataset
loader = CSICDatasetLoader('data/raw')
df = loader.load()
# Output: Loaded 46 total requests ({'anomalous': 24, 'normal': 22})

# Extract features
extractor = FeatureExtractor()
X, y, feature_names = loader.extract_features(df, extractor)
# Output: Extracted 46 features successfully (0 failures)
#         Shape: X=(46, 32), y=(46,)
#         Class distribution: {0: 22, 1: 24}
```

---

## Fitur Utama

### Updated Features (32 fitur, bertambah dari 25)

| # | Fitur | Tipe | Sumber | Deskripsi |
|---|-------|------|--------|-----------|
| 1 | `request_method` | Categorical | HTTP Method | GET, POST, PUT, DELETE, HEAD, OPTIONS |
| 2 | `url_length` | Numeric | Full URL | Panjang total URL (termasuk scheme+host) |
| 3 | `path_length` | Numeric | URL Path | Panjang path saja (tanpa query) |
| 4 | `query_string_length` | Numeric | Query String | Panjang query string saja |
| 5 | `url_parameter_count` | Numeric | Query Params | Jumlah query parameters |
| 6 | `url_special_char_count` | Numeric | Full URL | Jumlah karakter spesial (`'`, `"`, `<`, `>`, `%`, `\`, `;`, `--`, `/*`, `*/`) |
| 7 | `payload_length` | Numeric | Body | Panjang body payload (POST data) |
| 8 | `payload_entropy` | Numeric | Body | Shannon entropy dari payload string |
| 9 | `combined_entropy` | Numeric | URL + Body | Shannon entropy dari gabungan URL + body |
| 10 | `payload_has_sql_keywords` | Binary | Payload/URL | Deteksi keyword SQL (`SELECT`, `UNION`, `INSERT`, `DROP`, `UPDATE`, `DELETE`, `OR 1=1`, dll.) |
| 11 | `payload_has_xss_tags` | Binary | Payload/URL | Deteksi tag XSS (`<script>`, `javascript:`, `onerror=`, `onclick=`, dll.) |
| 12 | `payload_has_path_traversal` | Binary | Payload/URL | Deteksi path traversal (`../`, `..\\`, `/etc/passwd`) |
| 13 | `payload_has_crlf` | Binary | Payload/URL | Deteksi CRLF characters (`%0d%0a`, `\r\n`) |
| 14 | `payload_has_ssi` | Binary | Payload/URL | Deteksi SSI tags (`<!--#`, `<!--#exec`) |
| 15 | `url_has_double_encoding` | Binary | Full URL | Deteksi double URL encoding (`%25`) |
| 16 | `url_has_null_byte` | Binary | Full URL | Deteksi null byte (`%00`) |
| 17 | `referer_header_present` | Binary | Header | Apakah header Referer ada |
| 18 | `user_agent_unusual` | Binary | Header | User-Agent tidak standar atau kosong |
| 19 | `content_type_missing` | Binary | Header | Content-Type hilang pada POST request |
| 20 | `max_consecutive_special_chars` | Numeric | URL/Payload | Jumlah maksimum karakter spesial berturut-turut |
| 21 | `normalized_url_length` | Numeric | URL | URL setelah decoding |
| 22 | `number_of_encoded_chars` | Numeric | URL/Body | Jumlah karakter yang di-encode (`%XX`) |
| 23 | `has_long_parameter_name` | Binary | Query Params | Parameter name > 50 karakter |
| 24 | `has_empty_parameter` | Binary | Query Params | Ada parameter tanpa value |
| 25 | `method_not_allowed` | Binary | Method + Path | Method tidak sesuai endpoint (placeholder, perlu config) |
| 26 | `url_directory_depth` | Numeric | Path | Kedalaman direktori dalam URL |
| 27 | `has_server_side_number` | Numeric | URL | Angka besar di URL (indikasi buffer overflow attempt) |
| 28 | `content_type_application_form` | Binary | Header | Content-Type `application/x-www-form-urlencoded` |
| 29 | `has_cookie_header` | Binary | Header | Apakah ada header Cookie |
| 30 | `cookie_value_length` | Numeric | Header | Panjang nilai cookie |
| 31 | `accept_header_present` | Binary | Header | Apakah ada header Accept |
| 32 | `host_header_present` | Binary | Header | Apakah ada header Host |

> **Catatan**: 7 fitur baru ditambahkan berdasarkan observasi sampel data:
> - `path_length` & `query_string_length`: URL berisi full URL (scheme+host+path+query), penting memisahkan analisis
> - `combined_entropy`: menggabungkan URL dan body untuk menangkap anomaly di manapun
> - `has_cookie_header` & `cookie_value_length`: sampel menunjukkan banyak request memiliki cookie session
> - `accept_header_present` & `host_header_present`: header umum pada sampel data

---

## Algoritma Detail

### 3.1 Shannon Entropy Calculation

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

### 3.2 Keyword Detection Patterns

```python
SQL_KEYWORDS = re.compile(
    r"(\b(SELECT|UNION|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|"
    r"EXEC|EXECUTE|xp_|sp_|DECLARE|CURSOR|CAST|CONVERT)\b|"
    r"(OR\s+1\s*=\s*1|AND\s+1\s*=\s*1|'\s*OR\s*'|\"\s*OR\s*\")",
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

### 3.3 URL Decoding

```python
from urllib.parse import unquote, unquote_plus

def normalize_url(url: str) -> str:
    """Decode URL dua kali untuk detect double encoding (seperti CSIC 2010)."""
    decoded_once = unquote_plus(url)
    decoded_twice = unquote(decoded_once)
    return decoded_twice
```

---

## Interface Class (FeatureExtractor)

```python
class FeatureExtractor:
    """Ekstrak fitur numerik dari HTTP request (parsed dict)."""

    def extract(self, parsed_request: dict) -> list[float]:
        """
        Args:
            parsed_request: dict hasil HTTPRequestParser.parse() dengan keys:
                - method: str (HTTP method)
                - full_url: str (full URL including scheme+host)
                - url: str (same as full_url)
                - path: str (URL path without query)
                - query_string: str (query parameters part)
                - query_params: dict (parsed query params)
                - headers: dict (lowercased keys)
                - body: str (request body for POST)
                - content_length: int
        Returns:
            list[float]: array fitur numerik (32 features)
        """
        raise NotImplementedError

    def get_feature_names(self) -> list[str]:
        """Return nama setiap fitur untuk interpretability."""
        raise NotImplementedError
```

---

## Output Format

Output berupa dictionary/array numerik siap input model:

```json
{
    "request_method": 1,
    "url_length": 145,
    "path_length": 42,
    "query_string_length": 103,
    "url_parameter_count": 5,
    "url_special_char_count": 7,
    "payload_length": 62,
    "payload_entropy": 4.18,
    "combined_entropy": 4.52,
    "payload_has_sql_keywords": 1,
    "payload_has_xss_tags": 0,
    "payload_has_path_traversal": 0,
    "payload_has_crlf": 0,
    "payload_has_ssi": 0,
    "url_has_double_encoding": 0,
    "url_has_null_byte": 0,
    "referer_header_present": 0,
    "user_agent_unusual": 0,
    "content_type_missing": 0,
    "max_consecutive_special_chars": 3,
    "normalized_url_length": 128,
    "number_of_encoded_chars": 12,
    "has_long_parameter_name": 0,
    "has_empty_parameter": 0,
    "method_not_allowed": 0,
    "url_directory_depth": 3,
    "has_server_side_number": 0,
    "content_type_application_form": 1,
    "has_cookie_header": 1,
    "cookie_value_length": 36,
    "accept_header_present": 1,
    "host_header_present": 1
}
```

Encoding categorical:
- `request_method`: Label encode (GET=0, POST=1, PUT=2, DELETE=3, HEAD=4, OPTIONS=5)

---

## Konsistensi Pipeline

- Gunakan **class yang sama** (`FeatureExtractor` + `HTTPRequestParser`) untuk training dan inference
- Simpan instance/config extractor sebagai singleton
- Test bahwa output feature training == output feature inference untuk request yang sama
- Untuk live traffic (middleware), request sudah berbentuk dict → skip parser, langsung ke extractor
