"""
Feature Extractor — dipindahkan apa adanya dari notebooks/01-xgboost-training.ipynb (cell 29).
Mengekstrak 32 fitur numerik dari satu parsed request dict.
"""
import math
from collections import Counter

import numpy as np

from .patterns import (
    SQL_KEYWORDS_PATTERN,
    XSS_PATTERN,
    PATH_TRAVERSAL_PATTERN,
    CRLF_PATTERN,
    CMD_INJECTION_PATTERN,
    FILE_INCLUSION_PATTERN,
    ENCODED_CHAR_PATTERN,
)


def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = Counter(s)
    length = len(s)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())


class FeatureExtractor:
    '''Ekstraksi 32 fitur numerik dari satu parsed request dict.'''

    FEATURE_NAMES = [
        "url_length", "path_length", "query_string_length", "body_length",
        "num_headers", "num_params",
        "avg_param_name_length", "avg_param_value_length", "max_param_value_length",
        "max_param_name_length", "std_param_value_length",
        "url_entropy", "body_entropy", "param_value_max_entropy",
        "digit_ratio", "uppercase_ratio", "special_char_ratio", "alpha_ratio",
        "whitespace_count", "non_printable_count",
        "sql_keyword_count", "xss_keyword_count", "path_traversal_count",
        "crlf_injection_count", "cmd_injection_count", "file_inclusion_count",
        "encoded_char_count",
        "method_is_get", "method_is_post", "has_cookie_header",
        "has_content_type_header", "content_length_mismatch",
    ]

    def extract(self, parsed: dict) -> list:
        full_url = parsed.get("full_url", "") or ""
        path = parsed.get("path", "") or ""
        query_string = parsed.get("query_string", "") or ""
        body = parsed.get("body", "") or ""
        headers = parsed.get("headers", {}) or {}
        params = parsed.get("query_params", {}) or {}
        method = (parsed.get("method", "") or "").upper()

        combined_text = full_url + body

        # --- Length-based ---
        url_length = len(full_url)
        path_length = len(path)
        query_string_length = len(query_string)
        body_length = len(body)
        num_headers = len(headers)
        num_params = len(params)

        # --- Param stats ---
        param_names = list(params.keys())
        param_values = [str(v) for v in params.values()]
        name_lens = [len(n) for n in param_names] or [0]
        value_lens = [len(v) for v in param_values] or [0]

        avg_param_name_length = float(np.mean(name_lens))
        avg_param_value_length = float(np.mean(value_lens))
        max_param_value_length = float(np.max(value_lens))
        max_param_name_length = float(np.max(name_lens))
        std_param_value_length = float(np.std(value_lens))

        # --- Entropy ---
        url_entropy = shannon_entropy(full_url)
        body_entropy = shannon_entropy(body)
        param_value_max_entropy = max((shannon_entropy(v) for v in param_values), default=0.0)

        # --- Char composition ---
        n_chars = max(len(combined_text), 1)
        digit_ratio = sum(c.isdigit() for c in combined_text) / n_chars
        uppercase_ratio = sum(c.isupper() for c in combined_text) / n_chars
        alpha_ratio = sum(c.isalpha() for c in combined_text) / n_chars
        special_char_ratio = sum((not c.isalnum()) and (not c.isspace()) for c in combined_text) / n_chars
        whitespace_count = sum(c.isspace() for c in combined_text)
        non_printable_count = sum(not c.isprintable() for c in combined_text)

        # --- Signature-based counts ---
        sql_keyword_count = len(SQL_KEYWORDS_PATTERN.findall(combined_text))
        xss_keyword_count = len(XSS_PATTERN.findall(combined_text))
        path_traversal_count = len(PATH_TRAVERSAL_PATTERN.findall(combined_text))
        crlf_injection_count = len(CRLF_PATTERN.findall(combined_text))
        cmd_injection_count = len(CMD_INJECTION_PATTERN.findall(combined_text))
        file_inclusion_count = len(FILE_INCLUSION_PATTERN.findall(combined_text))
        encoded_char_count = len(ENCODED_CHAR_PATTERN.findall(combined_text))

        # --- Structural ---
        method_is_get = 1 if method == "GET" else 0
        method_is_post = 1 if method == "POST" else 0
        has_cookie_header = 1 if "cookie" in headers else 0
        has_content_type_header = 1 if "content-type" in headers else 0

        declared_len = parsed.get("content_length", 0) or 0
        content_length_mismatch = abs(declared_len - len(body))

        return [
            url_length, path_length, query_string_length, body_length,
            num_headers, num_params,
            avg_param_name_length, avg_param_value_length, max_param_value_length,
            max_param_name_length, std_param_value_length,
            url_entropy, body_entropy, param_value_max_entropy,
            digit_ratio, uppercase_ratio, special_char_ratio, alpha_ratio,
            whitespace_count, non_printable_count,
            sql_keyword_count, xss_keyword_count, path_traversal_count,
            crlf_injection_count, cmd_injection_count, file_inclusion_count,
            encoded_char_count,
            method_is_get, method_is_post, has_cookie_header,
            has_content_type_header, content_length_mismatch,
        ]
