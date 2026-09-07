"""
Regression tests untuk guardrail `is_clean_benign` di routes.py.
Memastikan perilaku false-positive guard tidak regresi saat
infer_attack_class() atau feature extractor berubah.

Tests mengirim request langsung ke Inference API (/predict) dan
memverifikasi label + attack_class output.
"""
import pytest
import requests

API_URL = "http://127.0.0.1:8000/predict"


def _predict(method: str, url: str, body: str = "", headers: dict = None):
    """Helper: kirim ke /predict dan return response JSON."""
    payload = {
        "method": method,
        "url": url,
        "headers": headers or {"User-Agent": "pytest-guardrail"},
        "body": body,
    }
    resp = requests.post(API_URL, json=payload, timeout=5)
    assert resp.status_code == 200, f"API returned {resp.status_code}: {resp.text}"
    return resp.json()


class TestCleanBenignGuardrail:
    """Regression tests for is_clean_benign guardrail in routes.py."""

    def test_a_get_home_plain(self):
        """GET /home polos — harus label=normal, attack_class=None."""
        result = _predict("GET", "/home")
        assert result["label"] == "normal", f"Expected normal, got {result}"
        assert result["attack_class"] is None, f"Expected None attack_class, got {result}"

    def test_b_get_search_benign_query(self):
        """GET /search?q=hello — query param benign, TAPI model CSIC 2010
        menganggap anomalous karena domain gap (model hanya tahu pola
        URL tienda1 Spanyol). Guardrail is_clean_benign TIDAK memproteksi
        kasus ini karena num_params > 0 dan query_string_length > 0.
        Ini adalah known false-positive; retrain model jangka panjang."""
        result = _predict("GET", "/search?q=hello")
        # Expected: anomalous + unknown_anomaly (no attack signature tapi model FP)
        assert result["label"] == "anomalous", f"Expected anomalous (CSIC FP), got {result}"
        assert result["attack_class"] == "unknown_anomaly", \
            f"Expected unknown_anomaly, got {result['attack_class']}"

    def test_c_get_home_with_encoded_space(self):
        """GET /home%20page — encoded char ringan.
        Ekspektasi: encoded_char_count=1 atau kecil, guardrail mungkin TIDAK
        memproteksi karena encoded_char_count > 0 — tapi model sebaiknya
        tetap menganggap normal karena tidak ada attack signature.
        Dokumentasi: jika model FP, ini diharapkan (CSIC domain gap).
        Test ini mendokumentasikan behavior aktual."""
        result = _predict("GET", "/home%20page")
        # Ini BISA anomalous karena encoded char, atau normal jika model robust.
        # Yang penting: test berjalan tanpa crash dan label valid.
        assert result["label"] in ("normal", "anomalous")
        if result["label"] == "anomalous":
            # Jika anomalous, attack_class harus unknown_anomaly (bukan specific attack)
            assert result["attack_class"] == "unknown_anomaly", \
                f"Expected unknown_anomaly for non-attack encoded URL, got {result['attack_class']}"

    def test_d_sqli_not_bypassed_by_guardrail(self):
        """GET /search?q=' OR 1=1-- — SQLi harus TETAP terdeteksi.
        Guardrail TIDAK boleh meng-override detection yang benar."""
        result = _predict("GET", "/search?q=' OR 1=1--")
        assert result["label"] == "anomalous", f"Expected anomalous, got {result}"
        assert result["attack_class"] == "sql_injection", \
            f"Expected sql_injection, got {result['attack_class']}"
