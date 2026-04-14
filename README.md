# Industrial Energy Consumption Forecasting
## Multi-Capstone AI + Data Engineering Pipeline

---

## Real-World Problem

A heavy industrial facility runs **50+ independent machines** (compressors,
chillers, HVAC units, CNC rigs).  Each consumes kilowatts independently.
The facility needs:

- Real-time anomaly detection **at the machine** without cloud latency
- Seasonal consumption forecasting for capacity planning
- Management dashboards for facility teams
- Scalable data processing that works for 1 building or 1000
- Automated alerting when any machine spikes beyond its prediction

---

## Dataset

**ASHRAE Great Energy Predictor III** (Kaggle)
- Link: https://www.kaggle.com/c/ashrae-energy-prediction/data
- Size: ~1 GB raw, ~10 MB after our 5-machine filter
- Each "building" = one industrial machine in our story

**Download:**
```bash
pip install kaggle
kaggle competitions download -c ashrae-energy-prediction -p ./Dataset_folder
unzip ./Dataset_folder/ashrae-energy-prediction.zip -d ./Dataset_folder/
```

> **No Kaggle account?** Capstone 1 auto-generates synthetic data.
> Capstone 4 can also use the synthetic CSV.

---

## Project Structure

```
industrial_energy/
├── 0_data_prep.py                  ← Run first (shared by all)
│
├── capstone1_tinyml/
│   └── 1_tinyml_pipeline.py        ← Train + TFLite export + edge simulation
│
├── capstone4_spark/
│   └── 4_spark_pipeline.py         ← Distributed processing + GBT model
│
├── capstone5_devops/
│   ├── app/main.py                 ← FastAPI inference server
│   ├── Dockerfile                  ← Multi-stage container build
│   ├── docker-compose.yml          ← Local orchestration
│   ├── requirements.txt
│   ├── tests/test_api.py           ← Pytest unit tests
│   └── .github/workflows/
│       └── ci_deploy.yml           ← GitHub Actions CI/CD
│
├── Dataset_folder/                 ← Raw download
│
├── data/
│   └── processed/                  ← Output of 0_data_prep.py
│
├── models/                         ← Output of Capstone 1
│   ├── anomaly_detector.tflite
│   ├── scaler.pkl
│   └── threshold.txt
│
└── spark_output/                   ← Output of Capstone 4
```

---

## Execution Order

### Step 0 — Environment

```bash
pip install kaggle pandas numpy scikit-learn tensorflow joblib \
            pyspark fastapi uvicorn requests pytest httpx
```

Java 11 required for Spark:
```bash
# Ubuntu
sudo apt install openjdk-11-jre
# macOS
brew install openjdk@11
```

### Step 1 — Shared Data Prep

```bash
python 0_data_prep.py
# Output: data/processed/industrial_energy.csv (~10 MB)
```

### Step 2 — Capstone 1 (TinyML)

```bash
python capstone1_tinyml/1_tinyml_pipeline.py
```

What it does:
1. Loads machine data (or generates synthetic if ASHRAE not found)
2. Scales + creates 24-hour sliding windows
3. Trains LSTM Autoencoder (Encoder → Bottleneck → Decoder)
4. Computes anomaly threshold (mean + 3σ of validation errors)
5. Exports quantized TFLite model (~10-30 KB)
6. Simulates 200 hours of edge inference
7. Saves `models/` artifacts + `capstone1_tinyml/anomaly_log.csv`

### Step 3 — Capstone 4 (Spark)

```bash
python capstone4_spark/4_spark_pipeline.py
```

What it does:
1. Ingests CSV with explicit Spark schema (no inference overhead)
2. Adds window features: lag_1h, lag_24h, rolling_avg/std/max/min
3. Flags anomalies: spike rule + Z-score rule + drop rule
4. Aggregates per-machine KPIs (avg, peak, std, p95, anomaly rate)
5. Computes monthly trends across all machines
6. Trains GBT Regression model (distributed ML)
7. Saves all outputs to `spark_output/`

### Step 4 — Capstone 5 (DevOps API)

**Without Docker (local dev):**
```bash
cd capstone5_devops
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**With Docker:**
```bash
cd capstone5_devops
docker-compose up --build
```

**Test the API:**
```bash
# Health check
curl http://localhost:8000/health

# Normal prediction
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "machine_id": 0,
    "readings": [80,82,85,81,80,83,90,102,118,125,130,128,
                 122,119,115,112,118,125,132,128,115,105,98,90],
    "predicted_kwh": 95.0
  }'

# Simulated anomaly (spike readings)
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "machine_id": 1,
    "readings": [80,82,85,81,80,83,90,102,118,125,130,128,
                 122,119,115,112,118,125,132,128,115,105,98,380],
    "predicted_kwh": 90.0
  }'

# View recent anomalies
curl "http://localhost:8000/anomalies?machine_id=0&last_n=20"

# Metrics dashboard
curl http://localhost:8000/metrics
```

**Interactive API docs:** http://localhost:8000/docs

**Run tests:**
```bash
cd capstone5_devops
pytest tests/ -v
```

---

## Slack Alerting Setup (Optional)

1. Go to https://api.slack.com/apps → Create App → Incoming Webhooks
2. Add webhook to your workspace channel
3. Copy the webhook URL (`https://hooks.slack.com/services/...`)
4. Set it before running:

```bash
# 1. Navigate to the DevOps directory
cd capstone5_devops

# 2. Copy the example environment file
cp .env.example .env

# 3. Edit .env and set your ALERT_WEBHOOK_URL
# 4. Start the backend
python app/start_backend.py

# With Docker
# The docker-compose.yml will automatically load values from .env
docker-compose up
```

---

## How the Capstones Connect

```
ASHRAE Raw Data (1 GB)
         │
         ▼
  0_data_prep.py  ──────────────────────────── data/processed/ (~10 MB)
         │
         ├──► CAPSTONE 1 (TinyML)
         │    LSTM Autoencoder → anomaly_detector.tflite
         │    edge_inference  → anomaly_log.csv ─────────────────────┐
         │                                                            │
         ├──► CAPSTONE 4 (Spark)                                      │
         │    Distributed features → GBT model                       │
         │    → spark_output/ (KPIs, monthly trends, anomalies) ─────┤
         │                                                            │
         └──► CAPSTONE 5 (DevOps)                                     │
              FastAPI wraps TFLite model ◄───────────────────────────┘
              Docker container
              GitHub Actions CI/CD
              Slack alert → actual > predicted × 1.5
```

---

## What the Project Does & How to Verify Each Stage

This project simulates a complete end-to-end industrial data engineering and machine learning lifecycle. Here is how to verify each section:

### 1. Data Preparation
**What it does:** Reads chunks from a heavy raw IoT power dataset (ASHRAE) without crashing local memory, selecting only 5 target machines up to ~40k rows. 
**Verification:**
- Go to `data/processed/`. You should see `industrial_energy.csv`. It contains clean dates, hourly intervals, and kWh. 

### 2. Capstone 1 (TinyML Edge Models)
**What it does:** Trains an LSTM Autoencoder solely on unlabelled data to understand normal power flows. It quantizes the result to an ultra-small TFLite neural network so it can run efficiently on an IoT device like a Raspberry Pi. 
**Verification:**
- Check `models/anomaly_detector.tflite`. It should be <300 KB.
- Check `capstone1_tinyml/anomaly_log.csv`. This file is generated by a simulated rolling 24-hr inference loop checking for anomalies. 

### 3. Capstone 4 (Spark Data Pipeline)
**What it does:** Uses PySpark for distributed multi-node big data processing to handle feature mappings (calculating moving averages, STD deviations, Min, and Max). Employs predefined anomaly flagging rules (e.g., sudden voltage spike, unexplainable drops).
**Verification:**
- View the outputs populated inside `spark_output/`.
- Open `spark_output/machine_kpis/*.csv` to see a summary table outlining percentage limits for machines or `spark_output/monthly_trends/*.csv` for aggregated monthly usage.

### 4. Capstone 5 (DevOps - FastAPI)
**What it does:** Puts the Capstone 1 model into a live production REST API endpoint allowing programmatic access. If an anomalous stream is pushed to the API, it tracks latency metrics and optionally pings a configured webhook. 
**Verification:**
- Run the API locally: `cd capstone5_devops && uvicorn app.main:app --port 8000`
- Predict Normal Energy Flow:
  ```bash
  curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"machine_id":0,"readings":[80,82,85,81,80,83,90,102,118,125,130,128,122,119,115,112,118,125,132,128,115,105,98,90]}'
  ```
- Predict Massive Spike (Anomaly):
  ```bash
  curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"machine_id":1,"readings":[80,82,85,81,80,83,90,102,118,125,130,128,122,119,115,112,118,125,132,128,115,105,98,380],"predicted_kwh": 90.0}'
  ```

---

## GitHub Actions Setup

Secrets needed in your repo (Settings → Secrets → Actions):

| Secret | Value |
|--------|-------|
| `DOCKERHUB_USERNAME` | Your Docker Hub username |
| `DOCKERHUB_TOKEN` | Docker Hub access token |
| `DEPLOY_HOST` | SSH server IP |
| `DEPLOY_USER` | SSH username |
| `DEPLOY_SSH_KEY` | Private SSH key (PEM format) |
| `ALERT_WEBHOOK_URL` | Slack webhook (optional) |

Pipeline stages:
1. **test** — Ruff lint + pytest (runs on every push + PR)
2. **build** — Docker build + push to Docker Hub (main branch only)
3. **deploy** — SSH into server, docker-compose pull + up -d
4. **notify-failure** — Slack alert if any job fails 
