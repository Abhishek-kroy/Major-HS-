"""
capstone5_devops/tests/test_api.py
===================================
Unit tests for the FastAPI app.

These run WITHOUT the actual TFLite model by mocking ModelAssets,
so they work in CI even when model files are not present.

Run:  pytest tests/ -v
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Mock TensorFlow BEFORE importing app ──────────────────────────
# This prevents TF from crashing in CI where there is no GPU / full TF
tf_mock = MagicMock()
sys.modules.setdefault("tensorflow", tf_mock)
sys.modules.setdefault("tensorflow.lite", tf_mock.lite)
sys.modules.setdefault("joblib", MagicMock())

import numpy as np
from fastapi.testclient import TestClient

# Patch ModelAssets before importing main
with patch("app.main.ModelAssets") as mock_assets:
    mock_assets.is_ready.return_value = True
    mock_assets.threshold = 0.05
    mock_assets.load_time = "2024-01-01T00:00:00+00:00"

    from app.main import app

client = TestClient(app)

VALID_READINGS = [
    80, 82, 85, 81, 80, 83, 90, 102,
    118, 125, 130, 128, 122, 119, 115, 112,
    118, 125, 132, 128, 115, 105, 98, 90
]


# ═══════════════════════════════════════════════════════════════════
# Health + Root
# ═══════════════════════════════════════════════════════════════════

def test_root():
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert "service" in data
    assert "docs" in data


def test_health_ok():
    with patch("app.main.ModelAssets") as ma:
        ma.is_ready.return_value = True
        ma.threshold = 0.05
        ma.load_time = "2024-01-01T00:00:00"
        r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True


def test_metrics_shape():
    r = client.get("/metrics")
    assert r.status_code == 200
    keys = {"uptime_seconds","total_requests","total_anomalies",
            "total_alerts","anomaly_rate_pct","avg_latency_ms"}
    assert keys.issubset(r.json().keys())


# ═══════════════════════════════════════════════════════════════════
# Predict endpoint — validation
# ═══════════════════════════════════════════════════════════════════

def test_predict_wrong_length():
    """API must reject readings that are not exactly 24 values."""
    r = client.post("/predict", json={
        "machine_id": 0,
        "readings": [100.0] * 10     # wrong length
    })
    assert r.status_code == 422


def test_predict_negative_reading():
    """Negative kWh values must be rejected."""
    bad = VALID_READINGS.copy()
    bad[0] = -5.0
    r = client.post("/predict", json={
        "machine_id": 0,
        "readings": bad
    })
    assert r.status_code == 422


def test_predict_normal(monkeypatch):
    """Normal reading → is_anomaly=False, no alert."""
    monkeypatch.setattr(
        "app.main.run_inference",
        lambda readings: {"recon_error": 0.01, "is_anomaly": False}
    )
    monkeypatch.setattr(
        "app.main.fire_alert",
        lambda *a, **kw: {"sent": False, "reason": "No threshold crossed"}
    )
    monkeypatch.setattr("app.main.log_prediction", lambda *a, **kw: None)
    monkeypatch.setattr("app.main.ModelAssets.is_ready", lambda: True)
    monkeypatch.setattr("app.main.ModelAssets.threshold", 0.05)

    r = client.post("/predict", json={
        "machine_id": 0,
        "readings": VALID_READINGS
    })
    assert r.status_code == 200
    body = r.json()
    assert body["is_anomaly"] is False
    assert body["machine_id"] == 0
    assert "recon_error" in body
    assert "latency_ms" in body


def test_predict_anomaly(monkeypatch):
    """High reconstruction error → is_anomaly=True."""
    monkeypatch.setattr(
        "app.main.run_inference",
        lambda readings: {"recon_error": 0.99, "is_anomaly": True}
    )
    monkeypatch.setattr(
        "app.main.fire_alert",
        lambda *a, **kw: {"sent": False, "reason": "No webhook configured"}
    )
    monkeypatch.setattr("app.main.log_prediction", lambda *a, **kw: None)
    monkeypatch.setattr("app.main.ModelAssets.is_ready", lambda: True)
    monkeypatch.setattr("app.main.ModelAssets.threshold", 0.05)

    r = client.post("/predict", json={
        "machine_id": 2,
        "readings": VALID_READINGS,
        "predicted_kwh": 95.0
    })
    assert r.status_code == 200
    body = r.json()
    assert body["is_anomaly"] is True
    assert body["recon_error"] == pytest.approx(0.99, abs=0.01)


def test_predict_with_forecast(monkeypatch):
    """predicted_kwh field should be accepted and used in alert logic."""
    monkeypatch.setattr(
        "app.main.run_inference",
        lambda readings: {"recon_error": 0.02, "is_anomaly": False}
    )
    monkeypatch.setattr(
        "app.main.fire_alert",
        lambda *a, **kw: {"sent": False, "reason": "No threshold crossed"}
    )
    monkeypatch.setattr("app.main.log_prediction", lambda *a, **kw: None)
    monkeypatch.setattr("app.main.ModelAssets.is_ready", lambda: True)
    monkeypatch.setattr("app.main.ModelAssets.threshold", 0.05)

    r = client.post("/predict", json={
        "machine_id": 1,
        "readings": VALID_READINGS,
        "predicted_kwh": 88.5
    })
    assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════
# Anomaly log endpoint
# ═══════════════════════════════════════════════════════════════════

def test_anomalies_no_log(tmp_path, monkeypatch):
    """If no log file exists, return empty list gracefully."""
    monkeypatch.setattr("app.main.LOG_PATH", str(tmp_path / "missing.csv"))
    r = client.get("/anomalies")
    assert r.status_code == 200
    assert r.json()["anomalies"] == []


def test_anomalies_with_data(tmp_path, monkeypatch):
    """Return filtered anomalies from log."""
    log_file = tmp_path / "anomaly_log.csv"
    log_file.write_text(
        "timestamp,machine_id,actual_kwh,predicted_kwh,"
        "recon_error,threshold,is_anomaly,alert_sent,latency_ms\n"
        "2024-01-01T10:00:00,0,200.0,90.0,0.99,0.05,1,0,3.2\n"
        "2024-01-01T11:00:00,1,85.0,90.0,0.01,0.05,0,0,2.1\n"
        "2024-01-01T12:00:00,0,210.0,90.0,0.95,0.05,1,1,3.8\n"
    )
    monkeypatch.setattr("app.main.LOG_PATH", str(log_file))
    r = client.get("/anomalies?machine_id=0")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 2
    assert all(row["machine_id"] == 0 for row in data["anomalies"])
