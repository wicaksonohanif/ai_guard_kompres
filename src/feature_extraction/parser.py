"""
HTTP Request Parser — dipindahkan apa adanya dari notebooks/01-xgboost-training.ipynb (cell 8).
Parse raw HTTP request text (format CSIC 2010) menjadi dict terstruktur.
"""
import re
from urllib.parse import urlsplit


HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH", "TRACE", "CONNECT"}


class HTTPRequestParser:
    '''Parser untuk raw HTTP request log format CSIC 2010.'''

    @staticmethod
    def parse_raw_text(raw_text: str):
        '''Parse seluruh isi file (banyak request) menjadi list of dict terstruktur.'''
        # Normalisasi line ending
        raw_text = raw_text.replace("\r\n", "\n")
        lines = raw_text.split("\n")

        requests = []
        current_lines = []

        def flush():
            if current_lines:
                parsed = HTTPRequestParser._parse_single(current_lines)
                if parsed is not None:
                    requests.append(parsed)

        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            if line.strip() == "":
                # Cek apakah baris non-kosong berikutnya adalah AWAL request baru.
                # Jumlah baris kosong sebelum request berikutnya bisa 1 (setelah body POST)
                # atau 2+ (setelah header GET tanpa body) -> keduanya harus dilewati sama-sama.
                j = i + 1
                while j < n and lines[j].strip() == "":
                    j += 1
                is_new_request = False
                if j < n:
                    next_line_stripped = lines[j].strip()
                    first_token = next_line_stripped.split(None, 1)[0].upper() if next_line_stripped else ""
                    is_new_request = first_token in HTTP_METHODS
                if is_new_request:
                    # akhir dari request saat ini; lewati SEMUA baris kosong sekaligus
                    flush()
                    current_lines = []
                    i = j
                    continue
                else:
                    # blank line adalah pemisah header/body dalam request yang sama -> simpan
                    current_lines.append(line)
                    i += 1
                    continue
            else:
                current_lines.append(line)
                i += 1
        flush()
        return requests

    @staticmethod
    def _parse_single(block_lines):
        '''Parse satu blok baris menjadi dict request. Return None jika tidak valid.'''
        # buang leading/trailing blank lines
        while block_lines and block_lines[0].strip() == "":
            block_lines = block_lines[1:]
        while block_lines and block_lines[-1].strip() == "":
            block_lines = block_lines[:-1]
        if not block_lines:
            return None

        method_line = block_lines[0].strip()

        # Kasus 1: format "METHOD url HTTP/1.1" dalam satu baris
        method, full_url = None, None
        m = re.match(r"^(GET|POST|PUT|DELETE|HEAD|OPTIONS|PATCH|TRACE|CONNECT)\s+(\S+)(\s+HTTP/\d\.\d)?$",
                     method_line, re.IGNORECASE)
        idx_after_request_line = 1
        if m:
            method = m.group(1).upper()
            full_url = m.group(2)
        else:
            # Kasus 2 (format asli CSIC): baris 1 = method saja, baris 2 = full url
            if method_line.upper() in HTTP_METHODS and len(block_lines) > 1:
                method = method_line.upper()
                full_url = block_lines[1].strip()
                idx_after_request_line = 2
            else:
                return None  # tidak bisa diparse, skip

        if not full_url:
            return None

        # Sisa baris: header sampai ketemu blank line, setelah itu body
        headers = {}
        body_lines = []
        in_body = False
        for line in block_lines[idx_after_request_line:]:
            if not in_body and line.strip() == "":
                in_body = True
                continue
            if in_body:
                body_lines.append(line)
            else:
                if ":" in line:
                    key, _, value = line.partition(":")
                    headers[key.strip().lower()] = value.strip()
        body = "\n".join(body_lines).strip()

        # Pecah URL menjadi path (relatif, tanpa scheme/host) + query string + query params
        url_parts = urlsplit(full_url)
        if url_parts.scheme and url_parts.netloc:
            path = url_parts.path or "/"
            query_string = url_parts.query
        elif "?" in full_url:
            # full_url tanpa scheme/host (mis. relative path), fallback split manual
            path, query_string = full_url.split("?", 1)
        else:
            path, query_string = full_url, ""

        query_params = HTTPRequestParser._parse_query_string(query_string)

        # Untuk POST, body juga sering berupa form-urlencoded params -> gabungkan ke query_params
        # sebagai representasi payload (tanpa menghapus body mentahnya)
        if method == "POST" and body and "=" in body:
            body_params = HTTPRequestParser._parse_query_string(body)
            merged_params = dict(query_params)
            merged_params.update(body_params)
        else:
            merged_params = query_params

        content_length = 0
        if "content-length" in headers:
            try:
                content_length = int(headers["content-length"])
            except ValueError:
                content_length = len(body)
        else:
            content_length = len(body)

        return {
            "method": method,
            "full_url": full_url,
            "path": path,
            "query_string": query_string,
            "query_params": merged_params,
            "headers": headers,
            "body": body,
            "content_length": content_length,
        }

    @staticmethod
    def _parse_query_string(qs: str):
        params = {}
        if not qs:
            return params
        for pair in qs.split("&"):
            if not pair:
                continue
            if "=" in pair:
                k, v = pair.split("=", 1)
            else:
                k, v = pair, ""
            params[k] = v
        return params

    @staticmethod
    def parse_api_request(method: str, url: str, headers: dict, body: str) -> dict:
        """
        Bangun parsed_request dict dari input API (SingleRequest schema).
        Digunakan oleh endpoint /predict agar query_params terisi dengan benar,
        bukan di-hardcode {} seperti cacat di Spec 03 asli.
        """
        method = method.upper()

        # Parse URL components
        url_parts = urlsplit(url)
        if url_parts.scheme and url_parts.netloc:
            path = url_parts.path or "/"
            query_string = url_parts.query
        elif "?" in url:
            path, query_string = url.split("?", 1)
        else:
            path, query_string = url, ""

        query_params = HTTPRequestParser._parse_query_string(query_string)

        # Untuk POST, body form-urlencoded juga di-merge ke query_params
        if method == "POST" and body and "=" in body:
            body_params = HTTPRequestParser._parse_query_string(body)
            merged_params = dict(query_params)
            merged_params.update(body_params)
        else:
            merged_params = query_params

        # Normalize headers to lowercase keys
        normalized_headers = {k.lower(): v for k, v in headers.items()}

        content_length = len(body) if body else 0
        if "content-length" in normalized_headers:
            try:
                content_length = int(normalized_headers["content-length"])
            except ValueError:
                content_length = len(body) if body else 0

        return {
            "method": method,
            "full_url": url,
            "path": path,
            "query_string": query_string,
            "query_params": merged_params,
            "headers": normalized_headers,
            "body": body or "",
            "content_length": content_length,
        }
