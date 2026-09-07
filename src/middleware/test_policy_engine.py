"""Unit tests untuk PolicyEngine — 3 skenario sesuai Tahap 2."""
import pytest
from src.middleware.policy_engine import PolicyEngine


@pytest.fixture
def engine():
    return PolicyEngine(block_threshold=0.7)


def test_normal_returns_allow(engine):
    assert engine.decide("normal", 0.9) == "allow"
    assert engine.decide("normal", 0.1) == "allow"


def test_anomalous_below_threshold_returns_flag(engine):
    """confidence 0.6 (antara 0.5-0.7) → flag."""
    assert engine.decide("anomalous", 0.6) == "flag"
    assert engine.decide("anomalous", 0.5) == "flag"
    assert engine.decide("anomalous", 0.7) == "flag"


def test_anomalous_above_threshold_returns_block(engine):
    """confidence 0.9 (> 0.7) → block."""
    assert engine.decide("anomalous", 0.9) == "block"
    assert engine.decide("anomalous", 0.71) == "block"
    assert engine.decide("anomalous", 1.0) == "block"
