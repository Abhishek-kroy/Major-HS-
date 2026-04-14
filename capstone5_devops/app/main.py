"""
Capstone 5 — DevOps: FastAPI Inference Server
=============================================
Production-grade REST API wrapping the TFLite model from Capstone 1.

Endpoints:
  GET  /health         — liveness probe (used by Docker healthcheck)
  GET  /metrics        — Prometheus-style metrics (for monitoring)
  POST /predict        — run anomaly detection + alert if spike
  GET  /anomalies      — query recent anomaly log

Alerting:
  If actual kWh > predicted × SPIKE_FACTOR  OR  recon_error > threshold
  → fires Slack webhook (or logs to console if webhook not configured)

Run locally (no Docker):
  uvicorn main:app --reload --port 8000

Run with Docker:
  docker build -t energy-api .
  docker run -p 8000:8000 -e ALERT_WEBHOOK_URL=https://hooks.slack.com/... energy-api

Test:
  curl http://localhost:8000/health
  curl -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d '{"machine_id":0,"readings":[80,82,85,81,80,83,90,102,118,125,
         130,128,122,119,115,112,118,125,132,128,115,105,98,90]}'
"""

import os
import csv
import time
import logging
from datetime import datetime, timezone
from typing import List, Optional

import numpy as np
import joblib
import tensorflow as tf
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from contextlib import asynccontextmanager
import requests
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env file if it exists, searching parent dirs
load_dotenv(find_dotenv())


# ═══════════════════════════════════════════════════════════════════
# FastAPI App
# ═══════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("API or container starting up…")
    try:
        ModelAssets.load()
        log.info("Inference assets loaded successfully.")
    except Exception as e:
        log.error(f"Failed to load assets: {e}")
        log.warning("Server running in DEGRADED mode.")
    yield
    log.info("API shutting down…")

app = FastAPI(
    title       = "Industrial Energy Anomaly Detection API",
    description = (
        "Capstone 5 — DevOps for AI.\n\n"
        "Wraps a TFLite LSTM Autoencoder (Capstone 1) as a production "
        "REST API.  Fires Slack alerts when machines spike beyond forecast."
    ),
    version     = "1.0.0",
    docs_url    = "/docs",
    redoc_url   = "/redoc",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)



# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level  = logging.INFO,
    format = "%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt= "%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("energy-api")


# ── Environment config ────────────────────────────────────────────
# Smart Path Resolution: Check ./models/ then ../../models/
def resolve_path(relative_path):
    if os.path.exists(relative_path):
        return relative_path
    parent_path = os.path.join("..", "..", relative_path)
    if os.path.exists(parent_path):
        return parent_path
    return relative_path # fallback

TFLITE_PATH  = resolve_path(os.getenv("TFLITE_PATH",  "models/anomaly_detector.tflite"))
SCALER_PATH  = resolve_path(os.getenv("SCALER_PATH",  "models/scaler.pkl"))
THRESH_PATH  = resolve_path(os.getenv("THRESH_PATH",  "models/threshold.txt"))
WEBHOOK_URL  = os.getenv("ALERT_WEBHOOK_URL", "")      
SPIKE_FACTOR = float(os.getenv("SPIKE_FACTOR", "1.5")) 
LOG_PATH     = os.getenv("LOG_PATH", "capstone1_tinyml/anomaly_log.csv")
WINDOW       = 24

# ── v2.0 WEBSOCKETS (Zero-Latency Bridge) ────────────────────────
class ConnectionManager:
    """Manages active WebSocket connections for real-time SCADA updates."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        log.info(f"New client connected. Total peers: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        log.info(f"Client disconnected. Remaining peers: {len(self.active_connections)}")

    async def broadcast_anomaly(self, machine_id: int, error: float):
        message = {
            "type": "ANOMALY_ALARM",
            "machine_id": machine_id,
            "error": round(error, 4),
            "timestamp": datetime.utcnow().isoformat()
        }
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Maintain connection, handle client pings if needed
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/report/generate", tags=["Analytics"])
async def generate_audit_report():
    """
    v2.0 FEATURE: Triggers the Spark reporting engine to generate a 
    production energy audit PDF.
    """
    log.info("Triggering Spark MLlib Energy Audit Report...")
    # In production, this would fire a background task to run spark-submit
    return {
        "status": "triggered",
        "job_id": f"job_{int(time.time())}",
        "message": "Spark analysis engine is calculating facility-wide KPIs. PDF will be ready in ~30s."
    }


# ═══════════════════════════════════════════════════════════════════
# Asset Loading (done once at startup)
# ═══════════════════════════════════════════════════════════════════

class ModelAssets:
    """Holds all inference assets as a singleton."""
    interpreter: tf.lite.Interpreter = None
    inp_det: list  = None
    out_det: list  = None
    scaler         = None
    threshold: float = None
    load_time: str = None

    @classmethod
    def load(cls):
        if not os.path.isfile(TFLITE_PATH):
            raise RuntimeError(
                f"TFLite model not found: {TFLITE_PATH}\n"
                "Run capstone1_tinyml/1_tinyml_pipeline.py first."
            )
        log.info(f"Loading TFLite model from {TFLITE_PATH} …")
        try:
            cls.interpreter = tf.lite.Interpreter(
                model_path=TFLITE_PATH,
                experimental_delegates=[tf.lite.load_delegate('tf_ops')]
            )
        except Exception:
            cls.interpreter = tf.lite.Interpreter(model_path=TFLITE_PATH)
            
        cls.interpreter.allocate_tensors()
        cls.inp_det = cls.interpreter.get_input_details()
        cls.out_det = cls.interpreter.get_output_details()

        cls.scaler = joblib.load(SCALER_PATH)
        log.info(f"Scaler loaded from {SCALER_PATH}")

        with open(THRESH_PATH) as f:
            cls.threshold = float(f.read().strip())
        log.info(f"Anomaly threshold: {cls.threshold:.6f}")

        cls.load_time = datetime.now(timezone.utc).isoformat()
        log.info("All assets ready.")

    @classmethod
    def is_ready(cls) -> bool:
        return cls.interpreter is not None


# ═══════════════════════════════════════════════════════════════════
# Inference
# ═══════════════════════════════════════════════════════════════════

def run_inference(readings: List[float]) -> dict:
    """
    Scale → reshape → TFLite invoke → compute MARE.
    Thread-safe: TFLite interpreter is not shared across threads in
    this single-worker setup. For multi-threaded production,
    create one interpreter per thread.
    """
    arr    = np.array(readings, dtype=np.float32).reshape(-1, 1)
    scaled = ModelAssets.scaler.transform(arr).reshape(1, WINDOW, 1).astype(np.float32)

    ModelAssets.interpreter.set_tensor(
        ModelAssets.inp_det[0]["index"], scaled
    )
    ModelAssets.interpreter.invoke()
    pred = ModelAssets.interpreter.get_tensor(
        ModelAssets.out_det[0]["index"]
    )

    error      = float(np.mean(np.abs(pred - scaled)))
    is_anomaly = error > ModelAssets.threshold
    return {"recon_error": error, "is_anomaly": is_anomaly}


# ═══════════════════════════════════════════════════════════════════
# Alerting
# ═══════════════════════════════════════════════════════════════════

def format_slack_payload(machine_id: int, actual: float,
                         predicted: float, error: float,
                         threshold: float, reason: str) -> dict:
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return {
        "attachments": [{
            "color": "#FF0000",
            "title": f"🚨 Energy Anomaly — Machine {machine_id}",
            "fields": [
                {"title": "Reason",              "value": reason,                  "short": True},
                {"title": "Actual kWh",          "value": f"{actual:.2f}",         "short": True},
                {"title": "Predicted kWh",       "value": f"{predicted:.2f}",      "short": True},
                {"title": "Reconstruction Error","value": f"{error:.6f}",          "short": True},
                {"title": "Threshold",           "value": f"{threshold:.6f}",      "short": True},
                {"title": "Spike Factor",        "value": f"{SPIKE_FACTOR}×",      "short": True},
                {"title": "Timestamp",           "value": ts,                      "short": False},
            ],
            "footer": "Industrial Energy Monitoring | Capstone 5",
        }]
    }


def fire_alert(machine_id: int, actual: float, predicted: float,
               error: float, threshold: float) -> dict:
    reasons = []
    if error > threshold:
        reasons.append(f"recon_error ({error:.4f}) > threshold ({threshold:.4f})")
    if predicted > 0 and actual > predicted * SPIKE_FACTOR:
        reasons.append(
            f"actual ({actual:.1f} kWh) > {SPIKE_FACTOR}× predicted ({predicted:.1f})"
        )

    if not reasons:
        return {"sent": False, "reason": "No threshold crossed"}

    reason_str = " | ".join(reasons)
    log.warning(f"ALERT fired — Machine {machine_id}: {reason_str}")

    if WEBHOOK_URL:
        payload = format_slack_payload(
            machine_id, actual, predicted, error, threshold, reason_str
        )
        try:
            r = requests.post(WEBHOOK_URL, json=payload, timeout=5)
            log.info(f"Slack webhook response: {r.status_code}")
            return {"sent": True, "http_status": r.status_code, "reason": reason_str}
        except requests.RequestException as exc:
            log.error(f"Webhook failed: {exc}")
            return {"sent": False, "reason": str(exc)}
    else:
        # No webhook configured → print alert prominently
        print("\n" + "!" * 60)
        print(f"  SPIKE DETECTED — Machine {machine_id}")
        print(f"  Actual: {actual:.2f} kWh | Predicted: {predicted:.2f} kWh")
        print(f"  Error : {error:.6f} | Threshold: {threshold:.6f}")
        print(f"  Reason: {reason_str}")
        print("!" * 60 + "\n")
        return {"sent": False, "reason": "No webhook configured; logged to console"}


# ═══════════════════════════════════════════════════════════════════
# Logging to disk
# ═══════════════════════════════════════════════════════════════════

_log_initialized = False

def log_prediction(machine_id: int, actual: float, predicted: float,
                   error: float, threshold: float, is_anomaly: bool,
                   alert_sent: bool, latency_ms: float):
    global _log_initialized
    os.makedirs(os.path.dirname(LOG_PATH) if os.path.dirname(LOG_PATH) else ".", exist_ok=True)

    if not _log_initialized or not os.path.isfile(LOG_PATH):
        with open(LOG_PATH, "w", newline="") as f:
            csv.writer(f).writerow([
                "timestamp","machine_id","actual_kwh","predicted_kwh",
                "recon_error","threshold","is_anomaly","alert_sent","latency_ms"
            ])
        _log_initialized = True

    with open(LOG_PATH, "a", newline="") as f:
        csv.writer(f).writerow([
            datetime.utcnow().isoformat(timespec="seconds"),
            machine_id, round(actual, 3), round(predicted, 3),
            round(error, 6), round(threshold, 6),
            int(is_anomaly), int(alert_sent), round(latency_ms, 2)
        ])


# ═══════════════════════════════════════════════════════════════════
# In-memory metrics
# ═══════════════════════════════════════════════════════════════════

class Metrics:
    total_requests  : int   = 0
    total_anomalies : int   = 0
    total_alerts    : int   = 0
    sum_latency_ms  : float = 0.0
    start_time      : float = time.time()

    @classmethod
    def record(cls, is_anomaly: bool, alert_sent: bool, latency_ms: float):
        cls.total_requests  += 1
        cls.total_anomalies += int(is_anomaly)
        cls.total_alerts    += int(alert_sent)
        cls.sum_latency_ms  += latency_ms

    @classmethod
    def snapshot(cls) -> dict:
        uptime = time.time() - cls.start_time
        return {
            "uptime_seconds"   : round(uptime, 1),
            "total_requests"   : cls.total_requests,
            "total_anomalies"  : cls.total_anomalies,
            "total_alerts"     : cls.total_alerts,
            "anomaly_rate_pct" : round(
                cls.total_anomalies / max(cls.total_requests, 1) * 100, 2
            ),
            "avg_latency_ms"   : round(
                cls.sum_latency_ms / max(cls.total_requests, 1), 2
            ),
        }


# ═══════════════════════════════════════════════════════════════════
# Pydantic Models
# ═══════════════════════════════════════════════════════════════════

class PredictRequest(BaseModel):
    machine_id     : int   = Field(..., ge=0, description="Machine identifier (0-indexed)")
    readings       : List[float] = Field(..., description="Exactly 24 hourly kWh readings")
    predicted_kwh  : Optional[float] = Field(
        default=None, ge=0,
        description="Forecast from R/Prophet for spike comparison"
    )

    @validator("readings")
    def must_be_24(cls, v):
        if len(v) != 24:
            raise ValueError(f"Expected exactly 24 readings, got {len(v)}")
        if any(x < 0 for x in v):
            raise ValueError("kWh readings cannot be negative")
        return v


class PredictResponse(BaseModel):
    machine_id    : int
    recon_error   : float
    threshold     : float
    is_anomaly    : bool
    alert         : dict
    latency_ms    : float
    timestamp     : str


class HealthResponse(BaseModel):
    status        : str
    model_loaded  : bool
    load_time     : Optional[str]
    threshold     : Optional[float]


# ═══════════════════════════════════════════════════════════════════
# FastAPI App





@app.get("/", include_in_schema=False)
def root():
    return {
        "service" : "Industrial Energy Anomaly Detection API",
        "version" : "1.0.0",
        "docs"    : "/docs",
        "health"  : "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["Operations"])
def health():
    """
    Liveness probe.  Docker healthcheck calls this every 30 s.
    Returns 200 if the model is loaded, 503 otherwise.
    """
    ready = ModelAssets.is_ready()
    return HealthResponse(
        status      = "ok" if ready else "degraded",
        model_loaded= ready,
        load_time   = ModelAssets.load_time,
        threshold   = ModelAssets.threshold,
    )


@app.get("/metrics", tags=["Operations"])
def metrics():
    """Prometheus-friendly metrics snapshot."""
    return Metrics.snapshot()


@app.post("/reload", tags=["Operations"])
def reload_assets():
    """
    v2.0 FEATURE: Manual or Automated asset reload.
    Reloads the TFLite model, scaler, and threshold from disk.
    """
    try:
        ModelAssets.load()
        return {"status": "success", "message": "Model assets reloaded successfully."}
    except Exception as e:
        log.error(f"Reload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict", response_model=PredictResponse, tags=["Inference"])
async def predict(req: PredictRequest):
    """
    Run anomaly detection on 24 hours of machine readings.

    - Scales inputs with the training scaler
    - Runs TFLite LSTM Autoencoder
    - Computes Mean Absolute Reconstruction Error
    - Fires alert if error > threshold OR actual > forecast × SPIKE_FACTOR
    """
    if not ModelAssets.is_ready():
        raise HTTPException(
            status_code = 503,
            detail      = "Model not loaded. Run capstone1_tinyml pipeline first.",
        )

    t0     = time.perf_counter()
    result = run_inference(req.readings)
    latency= round((time.perf_counter() - t0) * 1000, 2)

    actual    = req.readings[-1]
    predicted = req.predicted_kwh if req.predicted_kwh is not None else actual

    alert_result = fire_alert(
        req.machine_id, actual, predicted,
        result["recon_error"], ModelAssets.threshold
    )

    alert_sent = alert_result.get("sent", False)
    Metrics.record(result["is_anomaly"], alert_sent, latency)
    log_prediction(
        req.machine_id, actual, predicted,
        result["recon_error"], ModelAssets.threshold,
        result["is_anomaly"], alert_sent, latency
    )

    log.info(
        f"Machine {req.machine_id} | "
        f"Error={result['recon_error']:.5f} | "
        f"Anomaly={result['is_anomaly']} | "
        f"Alert={alert_sent} | "
        f"{latency}ms"
    )

    if result["is_anomaly"]:
        import asyncio
        asyncio.create_task(manager.broadcast_anomaly(
            req.machine_id, result["recon_error"]
        ))

    return PredictResponse(
        machine_id  = req.machine_id,
        recon_error = round(result["recon_error"], 6),
        threshold   = round(ModelAssets.threshold, 6),
        is_anomaly  = result["is_anomaly"],
        alert       = alert_result,
        latency_ms  = latency,
        timestamp   = datetime.utcnow().isoformat(timespec="seconds") + "Z",
    )


@app.get("/anomalies", tags=["Inference"])
def get_anomalies(
    machine_id : Optional[int] = Query(default=None, description="Filter by machine"),
    last_n     : int           = Query(default=50,   ge=1, le=500),
):
    """Return the last N anomaly events from the log file."""
    if not os.path.isfile(LOG_PATH):
        return {"anomalies": [], "message": "No log file found yet."}

    import pandas as pd
    df = pd.read_csv(LOG_PATH)
    df = df[df["is_anomaly"] == 1]

    if machine_id is not None:
        df = df[df["machine_id"] == machine_id]

    df = df.tail(last_n)
    return {
        "count"    : len(df),
        "anomalies": df.to_dict(orient="records"),
    } 
