# 🏗️ Industrial Digital Twin: System Architecture Deep Dive

This document explains the technical "Why" and "How" behind each component of the capstone project.

---

## 1. How the System Works (End-to-End Flow)

The system follows a **"Hierarchical Intelligence"** pattern:

1.  **THE EDGE (Sensor + ESP32):** Real-time energy data is captured at 1000Hz. The TinyML model sitting on the ESP32 checks every millisecond for "weird" pulse patterns.
2.  **THE BRIDGE (FastAPI + WebSockets):** If the Edge AI finds an anomaly, it sends a tiny JSON packet to the FastAPI server. WebSockets then "push" this alert to the Dashboard in <50ms.
3.  **THE CLOUD (Apache Spark):** All data—normal and anomalous—is pushed to the database. Spark "watches" the database globally.
4.  **THE UI (React Digital Twin):** Managers see a 1:1 spatial mapping of the machines, with live "Health Scores" calculated by Spark.

---

## 2. How TinyML is Used (The "Edge" AI)

TinyML is the **First Line of Defense**. 

*   **Model Type:** LSTM Autoencoder (running on TensorFlow Lite Micro).
*   **The Logic:** We don't tell the AI what an "error" looks like. We only show it "normal" operation. It learns the "standard heartbeat" of the machine.
*   **Detection:** It tries to "recreate" the current signal. If the signal is weird, the "Reconstruction Error" becomes giant, triggering an alert.
*   **Optimization:** We used **INT8 Quantization**. This reduces the model from 32-bit floats to 8-bit integers, allowing a low-power ESP32 chip to run AI that usually requires a laptop.

---

## 3. How Spark is Used (The "Global" Intelligence)

While TinyML looks at *one machine* in *one second*, Spark looks at **1,000 machines** over **30 days**.

*   **KPI Calculation:** Spark aggregates data from every machine to find the "Factory Efficiency Score."
*   **Correlation:** Spark asks: *"When Machine A spikes, does Machine B also spike 5 minutes later?"* (Root Cause Analysis).
*   **Structured Streaming:** It processes data in continuous "micro-batches," ensuring the dashboard stays live with global statistics.

---

## 4. Why Spark? Could it be removed?

**Short Answer:** For 1 machine, yes. For a factory, No.

| Feature | Standard Python (Pandas) | Apache Spark |
| :--- | :--- | :--- |
| **Data Limit** | Limited by RAM (~8-16GB) | Infinite (Scales across Servers) |
| **Speed** | Sequential (One by one) | Distributed (Parallel) |
| **Fail-Safety** | If it crashes, data is lost | Fault-tolerant (recovers automatically) |

**Conclusion:** We could remove Spark and use a simple script if we only had 5 sensors. But for an **Industrial Scale** application where thousands of sensors send data, Spark is the only way to prevent the server from crashing under the data weight.

---

## 5. Spark for "Remodelling" (The AI Feedback Loop)

This is the most advanced part of the architecture. Spark is the **Trainer** for the TinyML model.

1.  **Model Drift Detection:** Spark notices that the "Reconstruction Error" on the ESP32 is slowly rising, even though the machine is fine. This is **Model Drift** (the model is getting old or the machine's signature is shifting due to normal wear).
2.  **Automated Retraining:** Spark takes the last 7 days of "new normal" data and **automatically retrains** a new `.tflite` model using its massive distributed CPU power.
3.  **OTA Deployment:** The system then pushes this new model back to the ESP32 wirelessly (Over-the-Air).

**This means the system is "Self-Healing"—it improves its own AI over time without human intervention.**

---

## 6. Distributed Energy Forecasting (The Power Grid View)

To optimize factory spending, we don't just react to anomalies; we **forecast** future energy bills.

*   **Complex Modeling:** We use Spark to run **Time-Series Forecasting (ARIMA/Prophet)** across every machine simultaneously. 
*   **Grid Balancing:** Spark calculates the "Peak Load" for the next 48 hours. If it predicts a massive power spike at 2 PM tomorrow, it can alert the manager to reschedule machine start-times to save on energy costs.
*   **Large-Scale Inference:** Running a forecast for 1 machine is easy. Running 10,000 independent forecasts for a global power grid requires **Spark's Partitioned Parallelism**.

---

## 7. Why Spark is MANDATORY (The "Million Node" Scale)

| Task | Why Standard Python Fails | Why Spark Wins |
| :--- | :--- | :--- |
| **Global Forecasting** | Takes ~2 hours to forecast 1,000 machines. | Processes 1,000 machine forecasts in **seconds** using worker nodes. |
| **Remodelling Loop** | Cannot retrain 50 models at once without freezing. | Can retrain **hundreds of TinyML models** in parallel. |
| **Multi-Source Data** | Struggles to join 1TB of historical logs with live streams. | Built for **Large-Scale Data Shuffling** and joining. |

**Final Verdict:** Spark is the **Orchestrator**. Without it, the system would be a collection of isolated sensors. **With Spark, it becomes a unified, intelligent power grid.**
