# Industrial Digital Twin: Execution Guide

This guide provides all the commands necessary to run and interact with the Industrial Digital Twin system.

---

## 🏗️ Option 1: Run via Docker (Recommended)

Run the entire stack (FastAPI, Node.js, and React) with a single command.

```bash
# 1. Start the complete system
docker-compose up --build

# 2. Start in background mode (detached)
docker-compose up -d

# 3. View logs for a specific service
docker-compose logs -f node-server

# 4. Stop the system
docker-compose down
```

---

## 🛠️ Option 2: Manual Execution (Local Development)

If you need to run services individually for debugging.

### 1. Data Preparation (Shared)
Run this once to prepare the dataset for all pipelines.
```bash
python 0_data_prep.py
```

### 2. FastAPI Inference Server (Backend)
Handles anomaly detection via TFLite models.
```bash
cd capstone5_devops
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Node.js Proxy Server (Middle-Layer)
Handles real-time Socket.io communication and simulation logic.
```bash
cd server
npm install
npm run dev
```

### 4. React Dashboard (Frontend)
The user interface.
```bash
cd client
npm install
npm run dev
```

---

## 🧪 Simulation & Pipelines

### Run TinyML Pipeline (Capstone 1)
Trains and exports the LSTM Autoencoder.
```bash
python capstone1_tinyml/1_tinyml_pipeline.py
```

### Run Spark Pipeline (Capstone 4)
Processes the full dataset and calculates KPIs.
```bash
python capstone4_spark/4_spark_pipeline.py
```

### Run Sensor Emulator
Simulates live data streaming into the system.
```bash
python 6_sensor_emulator.py
```

---

## 🔗 System Access Points

- **Dashboard**: `http://localhost:5173`
- **Node Server**: `http://localhost:3001`
- **FastAPI Docs**: `http://localhost:8000/docs`
