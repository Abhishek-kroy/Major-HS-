# ── Stage 1: Builder (install heavy deps with build tools) ────────
FROM python:3.10-slim AS builder

WORKDIR /build

# System deps needed to compile some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

COPY capstone5_devops/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Runtime (lean final image) ───────────────────────────
FROM python:3.10-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy app source
COPY capstone5_devops/app/main.py ./main.py

# Copy trained model artifacts (built by Capstone 1)
COPY models/ ./models/

# Copy anomaly log dir (will be volume-mounted in production)
RUN mkdir -p capstone1_tinyml

# ── Environment defaults (override with -e or docker-compose.yml) ─
ENV TFLITE_PATH=models/anomaly_detector.tflite
ENV SCALER_PATH=models/scaler.pkl
ENV THRESH_PATH=models/threshold.txt
ENV SPIKE_FACTOR=1.5
ENV LOG_PATH=capstone1_tinyml/anomaly_log.csv
# Set ALERT_WEBHOOK_URL at runtime: docker run -e ALERT_WEBHOOK_URL=https://...

EXPOSE 8000

# ── Healthcheck (Docker will call this every 30s) ─────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ── Start server ──────────────────────────────────────────────────
CMD ["uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "info"]
