"""Unit tests untuk infer_attack_class()."""
from src.api.attack_classifier import infer_attack_class


def test_sql_injection_dominant():
    """sql_keyword_count=3, lainnya 0 -> sql_injection."""
    d = {
        "sql_keyword_count": 3,
        "xss_keyword_count": 0,
        "path_traversal_count": 0,
        "crlf_injection_count": 0,
        "cmd_injection_count": 0,
        "file_inclusion_count": 0,
    }
    assert infer_attack_class(d) == "sql_injection"


def test_xss_higher_than_sql():
    """xss=2, sql=1 -> xss (xss lebih tinggi)."""
    d = {
        "sql_keyword_count": 1,
        "xss_keyword_count": 2,
        "path_traversal_count": 0,
        "crlf_injection_count": 0,
        "cmd_injection_count": 0,
        "file_inclusion_count": 0,
    }
    assert infer_attack_class(d) == "xss"


def test_all_zero_returns_unknown():
    """Semua count 0 -> unknown_anomaly."""
    d = {
        "sql_keyword_count": 0,
        "xss_keyword_count": 0,
        "path_traversal_count": 0,
        "crlf_injection_count": 0,
        "cmd_injection_count": 0,
        "file_inclusion_count": 0,
    }
    assert infer_attack_class(d) == "unknown_anomaly"


def test_path_traversal():
    """path_traversal_count=5, lainnya 0 -> path_traversal."""
    d = {
        "sql_keyword_count": 0,
        "xss_keyword_count": 0,
        "path_traversal_count": 5,
        "crlf_injection_count": 0,
        "cmd_injection_count": 0,
        "file_inclusion_count": 0,
    }
    assert infer_attack_class(d) == "path_traversal"


def test_cmd_injection():
    """cmd_injection_count=2, lainnya 1 -> command_injection."""
    d = {
        "sql_keyword_count": 1,
        "xss_keyword_count": 1,
        "path_traversal_count": 0,
        "crlf_injection_count": 0,
        "cmd_injection_count": 2,
        "file_inclusion_count": 0,
    }
    assert infer_attack_class(d) == "command_injection"


if __name__ == "__main__":
    test_sql_injection_dominant()
    print("PASS: test_sql_injection_dominant")
    test_xss_higher_than_sql()
    print("PASS: test_xss_higher_than_sql")
    test_all_zero_returns_unknown()
    print("PASS: test_all_zero_returns_unknown")
    test_path_traversal()
    print("PASS: test_path_traversal")
    test_cmd_injection()
    print("PASS: test_cmd_injection")
    print("\nAll tests passed!")
