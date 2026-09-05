"""
Unit tests untuk FeatureExtractor dan HTTPRequestParser.
3 dummy input: normal GET, SQLi payload, XSS payload.
"""
import math
from src.feature_extraction.extractor import FeatureExtractor
from src.feature_extraction.parser import HTTPRequestParser


fe = FeatureExtractor()


def test_normal_get_request():
    """Test request GET normal tanpa payload mencurigakan."""
    parsed = HTTPRequestParser.parse_api_request(
        method="GET",
        url="/home",
        headers={"User-Agent": "Mozilla/5.0", "Host": "localhost:8080"},
        body=""
    )
    features = fe.extract(parsed)
    assert len(features) == 32, f"Expected 32 features, got {len(features)}"
    assert not any(math.isnan(f) if isinstance(f, float) else False for f in features), "NaN detected"
    assert all(isinstance(f, (int, float)) for f in features), "Non-numeric feature detected"

    # Fitur spesifik: method_is_get harus 1, sql/xss counts harus 0
    feature_dict = dict(zip(fe.FEATURE_NAMES, features))
    assert feature_dict["method_is_get"] == 1
    assert feature_dict["method_is_post"] == 0
    assert feature_dict["sql_keyword_count"] == 0
    assert feature_dict["xss_keyword_count"] == 0


def test_sqli_payload():
    """Test request dengan SQL Injection payload — dari contoh Spec 03."""
    parsed = HTTPRequestParser.parse_api_request(
        method="POST",
        url="/search?q=test'+OR+1%3D1--",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0",
        },
        body="username=admin' OR 1=1--&password=anything"
    )
    features = fe.extract(parsed)
    assert len(features) == 32, f"Expected 32 features, got {len(features)}"
    assert not any(math.isnan(f) if isinstance(f, float) else False for f in features), "NaN detected"
    assert all(isinstance(f, (int, float)) for f in features), "Non-numeric feature detected"

    feature_dict = dict(zip(fe.FEATURE_NAMES, features))
    assert feature_dict["sql_keyword_count"] > 0, f"sql_keyword_count should be > 0, got {feature_dict['sql_keyword_count']}"
    assert feature_dict["method_is_post"] == 1
    assert feature_dict["has_content_type_header"] == 1


def test_exact_spec03_sqli_payload():
    """Test payload persis dari specs/03-inference-api.md (dengan URL-encoded values)."""
    parsed = HTTPRequestParser.parse_api_request(
        method="POST",
        url="/search?q=test%27+OR+1%3D1--",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0",
            "Referer": ""
        },
        body="username=admin'%20OR%201%3D1--&password=anything"
    )
    features = fe.extract(parsed)
    assert len(features) == 32
    assert not any(math.isnan(f) if isinstance(f, float) else False for f in features)
    feature_dict = dict(zip(fe.FEATURE_NAMES, features))
    assert feature_dict["sql_keyword_count"] > 0, f"Expected sql_keyword_count > 0, got {feature_dict['sql_keyword_count']}"


def test_xss_payload():
    """Test request dengan XSS payload."""
    parsed = HTTPRequestParser.parse_api_request(
        method="POST",
        url="/comment",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0",
        },
        body="message=<script>alert(document.cookie)</script>"
    )
    features = fe.extract(parsed)
    assert len(features) == 32, f"Expected 32 features, got {len(features)}"
    assert not any(math.isnan(f) if isinstance(f, float) else False for f in features), "NaN detected"
    assert all(isinstance(f, (int, float)) for f in features), "Non-numeric feature detected"

    feature_dict = dict(zip(fe.FEATURE_NAMES, features))
    assert feature_dict["xss_keyword_count"] > 0, f"xss_keyword_count should be > 0, got {feature_dict['xss_keyword_count']}"


def test_feature_names_count_matches_extract_output():
    """FEATURE_NAMES harus punya 32 elemen dan cocok dengan output extract()."""
    assert len(fe.FEATURE_NAMES) == 32, f"Expected 32 FEATURE_NAMES, got {len(fe.FEATURE_NAMES)}"

    parsed = HTTPRequestParser.parse_api_request(
        method="GET", url="/test", headers={}, body=""
    )
    features = fe.extract(parsed)
    assert len(features) == len(fe.FEATURE_NAMES), (
        f"Mismatch: FEATURE_NAMES has {len(fe.FEATURE_NAMES)}, extract() returns {len(features)}"
    )


if __name__ == "__main__":
    test_normal_get_request()
    print("PASS: test_normal_get_request")
    test_sqli_payload()
    print("PASS: test_sqli_payload")
    test_xss_payload()
    print("PASS: test_xss_payload")
    test_feature_names_count_matches_extract_output()
    print("PASS: test_feature_names_count_matches_extract_output")
    print("\nAll tests passed!")
