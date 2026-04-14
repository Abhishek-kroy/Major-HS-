# Project Explanation Document: Industrial Energy Anomaly Detection

## 1. Project Overview

**What the project is:**
This project is an end-to-end, multi-stage AI and Data Engineering pipeline. It continuously monitors energy consumption data from heavy industrial machines, learns their normal power usage patterns, and flags sudden anomalies or spikes in real-time using machine learning.

**What real-world problem it solves:**
In heavy industries (manufacturing, HVAC, CNC operating), sudden spikes or drops in energy consumption indicate equipment failure, unoptimized usage, or impending breakdowns. Traditionally, monitoring requires expensive centralized servers that suffer from cloud latency and high bandwidth costs. 

**Why this problem is important:**
Detecting these anomalies instantly (at the machine level) prevents catastrophic equipment failure, reduces energy waste, and saves companies thousands of dollars in downtime and electrical bills. 

---

## 2. System Architecture 

The architecture is divided into the Edge (the machine) and the Cloud (central processing).

### Part A: The Edge (Hardware & AI)
* **ESP32 (Microcontroller):** 
  * *What it does:* Acts as the brain attached to the industrial machine, collecting power readings.
  * *Why it is used:* It is extremely cheap, uses very low power, and has WiFi capabilities.
* **TinyML (LSTM Autoencoder):**
  * *What it does:* A highly compressed neural network (~250 KB) running directly on the ESP32. It calculates a "reconstruction error" to determine if current power usage is normal.
  * *Why it is used:* Running the AI on the device itself means no cloud latency. It makes decisions in milliseconds even if the internet goes down.

### Part B: The Cloud (Big Data & Backend)
* **Apache Spark (Data Pipeline):**
  * *What it does:* Processes vast amounts of historical data across all machines to calculate facility-wide KPIs, rolling averages, and long-term trends.
  * *Why it is used:* When we have 10,000 machines sending data, standard Python fails. Spark distributes the workload across multiple servers. 
* **FastAPI Backend (DevOps):**
  * *What it does:* A production-grade REST API server wrapped in a Docker container. It receives alerts from the ESP32 and routes them to monitoring systems like Slack.
  * *How it works:* It exposes endpoints (like `/predict` and `/health`). If it detects an anomaly, it hits a webhook to send an instant notification to floor managers.

### Part C: The Visuals (Dashboard)
* **MERN / React Frontend (or PowerBI):**
  * *What it does:* A visual dashboard displaying live energy consumption, active anomalies, and historical spark data.
  * *Why it is used:* Provides an intuitive interface for human operators to monitor the facility.

---

## 3. Component Interaction & Data Flow

1. **Sensing:** The **ESP32** reads power data (kWh) from the machine every hour.
2. **Edge Processing:** The ESP32 passes the last 24 hours of data into the **TinyML Autoencoder**. 
3. **Local Decision:** The model attempts to reconstruct the data. If the error is higher than the established threshold, the ESP32 flags an **Anomaly**.
4. **Cloud Alerting:** The ESP32 sends a JSON payload to the **FastAPI Backend** (`/predict`).
5. **Notification:** The FastAPI server logs the anomaly and pushes a real-time alert to a **Slack Webhook**.
6. **Big Data Aggregation:** Periodically, **Apache Spark** ingests all logs to generate monthly trends and cross-machine analytics.
7. **Visualization:** The **React Dashboard** fetches data from the backend to display visual charts to the user.

---

## 4. Technologies Used

* **TensorFlow Lite (TinyML):** For compressing the deep learning model to run on microcontrollers.
* **Apache Spark / PySpark:** For big data feature engineering and aggregation.
* **FastAPI & Uvicorn:** For building the high-performance Python web server.
* **Docker:** To containerize the application for easy deployment anywhere.
* **React / MERN Stack:** Used for building the interactive client-side presentation and dashboard.
* **GitHub Actions:** CI/CD pipelines to automatically test the code before it reaches production.

---

## 5. Workflow Explanation (Step-by-Step)

When the system goes live:
1. **At 10:00 AM**, Machine A hums along perfectly. The ESP32 evaluates the power draw, gets a low error score, and does nothing.
2. **At 11:00 AM**, a motor bearings fail, causing a massive unexplained spike in power.
3. The ESP32 feeds this spike into the TinyML model. The model has never seen this pattern, resulting in a **high reconstruction error**.
4. The ESP32 immediately triggers an HTTP POST request to the **FastAPI Server**.
5. The Server processes the request, saves it to the database/log, and instantly pings the Slack channel: *"🚨 SPIKE DETECTED - Machine A"*.
6. The floor manager sees the alert on their phone and shuts down the machine before it catches fire.

---

## 8. Industrial v2.0: Expert Enhancements

To move from a Prototype to a **Production-Grade Industrial System**, we have implemented several enterprise-level features:

### 🟢 Capstone 1: IoT & Hardware (ESP32)
*   **OTA (Over-the-Air) Updates:** Enabled remote wireless updating of the TinyML model. This allows us to re-tune sensors without unmounting them from the machines.
*   **Hardware Watchdog:** Implemented a system-level timer that automatically reboots the ESP32 if it hangs for more than 60 seconds, ensuring 99.9% uptime.
*   **Local SD Persistence:** Logic to cache data locally if WiFi is lost, preventing data gaps during network outages.

### 🔵 Capstone 2: TinyML (On-Device AI)
*   **INT8 Quantization:** Optimized the LSTM Autoencoder to use 8-bit integers, reducing model size by 75% and increasing inference speed on the ESP32.
*   **Adaptive Thresholding:** The model "learns" the unique noise profile of its specific machine during its first 24 hours of operation, setting its own anomaly sensitivity.
*   **Model Drift Tracking:** The system calculates "Reconstruction Variance" over time to detect if the model needs retraining due to mechanical wear-and-tear.

### 🟡 Capstone 3: Big Data (Apache Spark)
*   **Structured Streaming:** Replaced periodic batch processing with a continuous Spark stream for sub-second KPI updates.
*   **MLlib Predictive Maintenance:** Uses historical failure data to predict *when* a machine will breakdown (RUL - Remaining Useful Life) instead of just detecting current faults.
*   **Delta Lake:** Implemented for ACID transactions, ensuring our energy records are never corrupted during high-volume ingest.

### 🔴 Capstone 4: Backend & UI (FastAPI & Dashboard)
*   **WebSocket Protocol:** Migrated from polling to full-duplex WebSockets for instantaneous UI updates.
*   **Professional PDF Reporting:** Integrated a reporting engine that generates ISO-compliant energy audit PDFs based on Spark analysis.
*   **Container Orchestration:** The backend is designed for Kubernetes (K8s) to scale from 1 to 10,000 machines automatically.

---

## 9. Key Features (Uniqueness)

* **No Cloud Dependency for AI:** The AI runs *on the machine*. We don't send raw data to the cloud for inference, saving massive bandwidth and ensuring privacy.
* **Unsupervised Learning:** We used an Autoencoder. We didn't need to manually label thousands of "anomalies" by hand. The model simply taught itself what "normal" looks like.
* **Enterprise Scalability:** By using Spark and Docker, the architecture scales from 1 machine to 10,000 seamlessly.

---

## 10. How to Explain This to a Teacher (Speaking Script)

### Step 1: The Hook (Start with the Problem)
> *"Hi [Teacher's Name], for our Capstone, we tackled a massive problem in the industrial sector: catastrophic machine failure. When a factory machine breaks, it costs thousands of dollars per minute. We built a system to catch symptoms of failure—sudden power spikes—instantly."*

### Step 2: The Core Innovation (TinyML & IoT)
> *"Instead of sending all data to the cloud, we put an AI brain directly ON the machine using an ESP32 chip and TinyML. Our model is **INT8 Quantized**, meaning it is 4 times smaller than a standard model but performs at the same speed. We've also added a **Hardware Watchdog** to ensure the sensors never stay offline if they crash."*

### Step 3: The Big Picture (Spark Streaming & DevOps)
> *"When a spike is detected, our **FastAPI server** receives an alert via **WebSockets** for zero-latency. Meanwhile, our **Apache Spark engine** uses **Structured Streaming** to monitor long-term trends across the entire factory grid, predicting when a machine might fail 48 hours before it actually does."*

### Step 4: Show, Don't Tell
> *"Let me show you our digital twin dashboard, where you can see the data flowing from the edge to our Spark cloud..."*

### Handling Possible Questions:

**Q:** *Why use an Autoencoder instead of standard classification?*
**A:** "Because in the real world, anomalies are super rare. We didn't have enough 'broken machine' data to train a classifier. An Autoencoder only needs 'normal' data to learn. Anything that doesn't fit the normal pattern is flagged."

**Q:** *Why Spark if the AI is on the Edge?*
**A:** "The Edge AI is for instant, real-time alerts. Spark is for historical, big-data analytics. E.g., comparing Machine A's performance against Machine B over the last 5 years."

**Q:** *Why MERN/React for the frontend?*
**A:** "We wanted a highly interactive, component-driven dashboard that can poll our APIs in real-time, which React handles perfectly via state variables and hooks."
