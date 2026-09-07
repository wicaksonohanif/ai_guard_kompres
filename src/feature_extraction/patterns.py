"""
Regex patterns untuk keyword/signature detection.
Dipindahkan apa adanya dari notebooks/01-xgboost-training.ipynb (cell 25 & cell 29).
"""
import re

# Dari cell 25 notebook — SQL keyword detection
SQL_KEYWORDS_PATTERN = re.compile(
    r"(SELECT|UNION|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|"
    r"EXEC|EXECUTE|xp_|sp_|DECLARE|CURSOR|CAST|CONVERT|"
    r"OR(?:\s+|\+|%20)+1(?:\s*|\+|%20)*(?:=|%3D)(?:\s*|\+|%20)*1|"
    r"AND(?:\s+|\+|%20)+1(?:\s*|\+|%20)*(?:=|%3D)(?:\s*|\+|%20)*1)",
    re.IGNORECASE
)

# Dari cell 29 notebook — attack signature patterns
XSS_PATTERN = re.compile(r"(<script|javascript:|onerror\s*=|onload\s*=|<img|<iframe|alert\s*\(|document\.cookie)", re.IGNORECASE)
PATH_TRAVERSAL_PATTERN = re.compile(r"(\.\./|\.\.\\|%2e%2e%2f|%2e%2e/|\.\.%2f)", re.IGNORECASE)
CRLF_PATTERN = re.compile(r"(%0d%0a|%0d|%0a|\r\n)", re.IGNORECASE)
CMD_INJECTION_PATTERN = re.compile(r"(;|\||&&|`|\$\(|wget\s|curl\s|nc\s|/bin/sh|/bin/bash|cmd\.exe)", re.IGNORECASE)
FILE_INCLUSION_PATTERN = re.compile(r"(\betc/passwd\b|\bboot\.ini\b|php://|file://|include\s*\(|require\s*\()", re.IGNORECASE)
ENCODED_CHAR_PATTERN = re.compile(r"%[0-9A-Fa-f]{2}")
