"""
Capstone 1 — TinyML: On-Premise Edge Anomaly Detection
=======================================================
Pipeline stages (run in order, all in this single script):

  Stage A: Generate synthetic data  <- use when ASHRAE not available
  Stage B: Train LSTM Autoencoder
  Stage C: Export quantized TFLite model (~30 KB)
  Stage D: Simulate edge inference  (mimics Raspberry Pi deployment)
  Stage E: Write anomaly_log.csv    (consumed by Capstone 3 + 5)

Architecture:
  Normal hourly readings -> LSTM Autoencoder -> reconstruction error
  If error > threshold (mean + 3*std of validation set) -> ANOMALY

Why an autoencoder?
  * It learns what "normal" looks like from unlabelled data.
  * No need for pre-labelled anomalies in the training set.
  * Tiny enough to run on a Raspberry Pi 4 (< 50 KB after quantization).
"""

import os
import csv
import time
import numpy as np
import pandas as pd
import tensorflow as tf
import joblib
from datetime import datetime, timedelta
from sklearn.preprocessing import MinMaxScaler


# -- Paths ---------------------------------------------------------
DATA_CSV    = "data/processed/industrial_energy.csv"
SYNTH_CSV   = "data/processed/synthetic_energy.csv"
MODELS_DIR  = "models"
TFLITE_PATH = f"{MODELS_DIR}/anomaly_detector.tflite"
SCALER_PATH = f"{MODELS_DIR}/scaler.pkl"
THRESH_PATH = f"{MODELS_DIR}/threshold.txt"
LOG_PATH    = "capstone1_tinyml/anomaly_log.csv"

# -- Hyperparameters -----------------------------------------------
WINDOW      = 24     # 1 day of hourly readings = one sequence
LSTM_UNITS  = 8      # small -> fits on microcontroller
EPOCHS      = 15
BATCH       = 32
TRAIN_SPLIT = 0.80
MACHINE_ID  = 0      # which machine to train on


# =====================================================================
# Stage A - Data Loading (ASHRAE or Synthetic fallback)
# =====================================================================

def generate_synthetic_data(n_days: int = 365) -> pd.DataFrame:
    """
    Creates realistic-looking industrial electricity data with:
      * Clear daily cycle (peak at 10:00-14:00)
      * Weekly pattern (lower on weekends)
      * Slow seasonal drift (higher in summer for HVAC)
      * Random Gaussian noise
      * ~2% injected anomaly spikes for testing

    Returns a DataFrame with columns: timestamp, machine_id, kwh
    """
    print("[Stage A] Generating synthetic energy data...")
    np.random.seed(42)

    timestamps = []
    values     = []
    base_start = datetime(2023, 1, 1)

    n_hours = n_days * 24
    for h in range(n_hours):
        ts  = base_start + timedelta(hours=h)
        dow = ts.weekday()          # 0=Mon … 6=Sun
        hr  = ts.hour
        mon = ts.month

        # Daily profile: ramp up 06:00, peak 10:00-14:00, wind down
        if 0 <= hr < 6:
            base = 60.0
        elif 6 <= hr < 10:
            base = 60.0 + (hr - 6) * 18.0
        elif 10 <= hr < 14:
            base = 132.0
        elif 14 <= hr < 18:
            base = 132.0 - (hr - 14) * 12.0
        elif 18 <= hr < 22:
            base = 84.0 - (hr - 18) * 8.0
        else:
            base = 52.0

        # Weekend reduction
        if dow >= 5:
            base *= 0.65

        # Seasonal boost (summer = more HVAC)
        seasonal = 1.0 + 0.25 * np.sin((mon - 1) / 12 * 2 * np.pi - np.pi / 2)
        base *= seasonal

        # Gaussian noise ±8%
        noise = np.random.normal(0, base * 0.08)
        kwh   = max(0.0, base + noise)

        # Inject anomalies randomly (~2% of readings)
        if np.random.random() < 0.02:
            kwh *= np.random.uniform(2.5, 4.0)   # large spike

    # Add realistic temperature (seasonal + noise)
    temps = [20.0 + 8.0 * np.sin((ts.month - 1) / 12 * 2 * np.pi - np.pi / 2) + np.random.normal(0, 2) for ts in timestamps]

    df = pd.DataFrame({
        "timestamp":       timestamps,
        "machine_id":      0,
        "kwh":             values,
        "air_temperature": [round(t, 2) for t in temps]
    })
    os.makedirs("data/processed", exist_ok=True)
    df.to_csv(SYNTH_CSV, index=False)
    print(f"[Stage A] Synthetic data: {len(df)} rows -> {SYNTH_CSV}")
    return df


def load_machine_data() -> np.ndarray:
    """
    Load kWh series for MACHINE_ID.
    Falls back to synthetic data if ASHRAE CSV not present.
    """
    if os.path.isfile(DATA_CSV):
        print(f"[Stage A] Loading ASHRAE data from {DATA_CSV}")
        df = pd.read_csv(DATA_CSV)
        series = df[df["machine_id"] == MACHINE_ID]["kwh"].dropna().values
    else:
        print(f"[Stage A] ASHRAE CSV not found — using synthetic data.")
        df = generate_synthetic_data()
        series = df["kwh"].values

    print(f"[Stage A] Loaded {len(series)} hourly readings for Machine {MACHINE_ID}")
    return series


# =====================================================================
# Stage B - Preprocessing + Model Training
# =====================================================================

def build_scaler_and_windows(series: np.ndarray):
    """
    MinMax-scale the raw kWh series, then slice into overlapping
    windows of length WINDOW.  Returns (X, scaler).
    """
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled = scaler.fit_transform(series.reshape(-1, 1))

    X = np.array([
        scaled[i : i + WINDOW]
        for i in range(len(scaled) - WINDOW)
    ])
    print(f"[Stage B] Windows: {X.shape}  (samples × timesteps × features)")
    return X, scaler


def build_autoencoder(window: int, units: int) -> tf.keras.Model:
    """
    Encoder: window -> latent vector (dim=units)
    Decoder: latent vector -> reconstructed window
    """
    inp = tf.keras.Input(shape=(window, 1), name="input")

    # Encoder
    enc = tf.keras.layers.GRU(
        units, activation="relu", return_sequences=False, name="encoder", unroll=True
    )(inp)

    # Bottleneck
    rep = tf.keras.layers.RepeatVector(window, name="bottleneck")(enc)

    # Decoder
    dec = tf.keras.layers.GRU(
        units, activation="relu", return_sequences=True, name="decoder", unroll=True
    )(rep)

    # Output reconstruction
    out = tf.keras.layers.TimeDistributed(
        tf.keras.layers.Dense(1), name="output"
    )(dec)

    model = tf.keras.Model(inp, out, name="TinyAutoencoder")
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="mse")
    return model


def train_model(X_train: np.ndarray, model: tf.keras.Model) -> tf.keras.callbacks.History:
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=3, restore_best_weights=True
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=2, min_lr=1e-5
        ),
    ]
    history = model.fit(
        X_train, X_train,
        epochs          = EPOCHS,
        batch_size      = BATCH,
        validation_split= 0.10,
        callbacks       = callbacks,
        verbose         = 1,
    )
    return history


def compute_threshold(model: tf.keras.Model, X_val: np.ndarray) -> float:
    """
    Predict on validation set, compute mean absolute reconstruction
    error per sample, set threshold at mean + 3 × std.
    """
    preds  = model.predict(X_val, verbose=0)
    errors = np.mean(np.abs(preds - X_val), axis=(1, 2))

    mu     = float(np.mean(errors))
    sigma  = float(np.std(errors))
    thresh = mu + 3.0 * sigma

    print(f"[Stage B] Validation errors — mean: {mu:.6f}  std: {sigma:.6f}")
    print(f"[Stage B] Anomaly threshold set to: {thresh:.6f}")
    return thresh


# =====================================================================
# Stage C - TFLite Export
# =====================================================================

def export_tflite(model: tf.keras.Model, X_train: np.ndarray) -> int:
    """
    v2.0 UPDATE: Switched to FP32 + SELECT_TF_OPS for LSTM compatibility.
    INT8 quantization + LSTM + TensorLists causes conversion failures.
    Returns file size in bytes.
    """
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    
    # Enable Flex delegate for LSTM ops (TensorList, etc.)
    converter.target_spec.supported_ops = [
        tf.lite.OpsSet.TFLITE_BUILTINS,
        tf.lite.OpsSet.SELECT_TF_OPS
    ]
    
    # This prevents the converter from trying to lower TensorList ops 
    # into a form that SELECT_TF_OPS doesn't yet support with INT8.
    converter._experimental_lower_tensor_list_ops = False

    tflite_model = converter.convert()

    os.makedirs(MODELS_DIR, exist_ok=True)
    with open(TFLITE_PATH, "wb") as f:
        f.write(tflite_model)

    size_kb = len(tflite_model) / 1024
    print(f"[Stage C] TFLite model saved: {TFLITE_PATH}  ({size_kb:.1f} KB)")
    return len(tflite_model)


def save_artifacts(scaler: MinMaxScaler, threshold: float):
    joblib.dump(scaler, SCALER_PATH)
    with open(THRESH_PATH, "w") as f:
        f.write(str(threshold))
    print(f"[Stage C] Scaler -> {SCALER_PATH}")
    print(f"[Stage C] Threshold -> {THRESH_PATH}")


# =====================================================================
# Stage D - Edge Inference Simulation
# =====================================================================

def load_tflite_interpreter() -> tf.lite.Interpreter:
    # Use the Flex delegate to support Select TF ops (like TensorLists in LSTM)
    try:
        interp = tf.lite.Interpreter(
            model_path=TFLITE_PATH,
            experimental_delegates=[tf.lite.load_delegate('tf_ops')]
        )
    except Exception:
        # Fallback for systems where the standard load fails
        interp = tf.lite.Interpreter(model_path=TFLITE_PATH)
        
    interp.allocate_tensors()
    return interp


def run_single_inference(interp: tf.lite.Interpreter,
                         window_raw: np.ndarray,
                         scaler: MinMaxScaler) -> float:
    """
    Scale a raw 24-hour window, run TFLite inference,
    return Mean Absolute Reconstruction Error (MARE).
    """
    scaled   = scaler.transform(window_raw.reshape(-1, 1))
    inp_data = scaled.reshape(1, WINDOW, 1).astype(np.float32)

    inp_det  = interp.get_input_details()
    out_det  = interp.get_output_details()

    interp.set_tensor(inp_det[0]["index"], inp_data)
    interp.invoke()
    pred = interp.get_tensor(out_det[0]["index"])

    return float(np.mean(np.abs(pred - inp_data)))


def write_log_header(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        csv.writer(f).writerow(
            ["timestamp", "machine_id", "hour_index",
             "kwh_last", "recon_error", "threshold", "is_anomaly"]
        )


def append_log_row(path: str, ts: str, machine: int, hour_idx: int,
                   kwh: float, error: float, thresh: float, is_anom: bool):
    for attempt in range(5):
        try:
            with open(path, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(
                    [ts, machine, hour_idx, round(kwh, 3),
                     round(error, 6), round(thresh, 6), int(is_anom)]
                )
            break
        except PermissionError:
            time.sleep(0.1)


def run_edge_simulation(series: np.ndarray,
                        interp: tf.lite.Interpreter,
                        scaler: MinMaxScaler,
                        threshold: float,
                        n_hours: int = 200):
    """
    Slide a 24-hour window across the test portion of the series,
    run TFLite inference at each step, log every decision.
    n_hours = how many inference steps to run (one per simulated hour).
    """
    print(f"\n[Stage D] Edge inference simulation — {n_hours} hours")
    print("-" * 62)
    write_log_header(LOG_PATH)

    n_anomalies = 0
    start_idx   = int(len(series) * TRAIN_SPLIT) + WINDOW

    for step in range(n_hours):
        idx       = start_idx + step
        if idx >= len(series):
            break

        window    = series[idx - WINDOW : idx]
        error     = run_single_inference(interp, window, scaler)
        is_anom   = error > threshold
        kwh_now   = float(series[idx - 1])
        ts        = datetime.utcnow().isoformat(timespec="seconds")

        if is_anom:
            n_anomalies += 1

        status    = "[!] ANOMALY" if is_anom else "[OK] Normal "
        print(
            f"  Hour {idx:5d} | kWh={kwh_now:7.2f} | "
            f"Error={error:.5f} | Thresh={threshold:.5f} | {status}"
        )
        append_log_row(LOG_PATH, ts, MACHINE_ID, idx,
                       kwh_now, error, threshold, is_anom)

        time.sleep(0.01)   # remove on actual Pi for real-time speed

    print("-" * 62)
    print(f"[Stage D] Done. Anomalies detected: {n_anomalies}/{n_hours}")
    print(f"[Stage D] Log saved -> {LOG_PATH}\n")


# =====================================================================
# Stage E - Summary Report
# =====================================================================

def print_summary_report(history: tf.keras.callbacks.History,
                         threshold: float,
                         tflite_size: int):
    log_df = pd.read_csv(LOG_PATH)
    n_total = len(log_df)
    n_anom  = log_df["is_anomaly"].sum()

    final_val_loss = min(history.history.get("val_loss", [float("nan")]))

    print("\n+------------------------------------------------------+")
    print("|           CAPSTONE 1 - SUMMARY REPORT               |")
    print("+------------------------------------------------------+")
    print(f"|  Model architecture : GRU Autoencoder               |")
    print(f"|  GRU units          : {LSTM_UNITS:<30} |")
    print(f"|  Window size        : {WINDOW} hours{'':<24} |")
    print(f"|  Best val_loss      : {final_val_loss:.6f}{'':<23} |")
    print(f"|  Anomaly threshold  : {threshold:.6f}{'':<23} |")
    print(f"|  TFLite model size  : {tflite_size/1024:.1f} KB{'':<25} |")
    print(f"|  Inference steps    : {n_total:<30} |")
    print(f"|  Anomalies flagged  : {n_anom}/{n_total}{'':<27} |")
    print(f"|  Log path           : {LOG_PATH:<30} |")
    print("+------------------------------------------------------+\n")


# ===================================================================
# Main
# ===================================================================

def main():
    print("=" * 62)
    print("  CAPSTONE 1 — TinyML Edge Anomaly Detection Pipeline")
    print("=" * 62)

    # Stage A — Load data
    series = load_machine_data()

    # Stage B — Scale, window, train
    X, scaler       = build_scaler_and_windows(series)
    split_idx       = int(len(X) * TRAIN_SPLIT)
    X_train, X_val  = X[:split_idx], X[split_idx:]

    print(f"\n[Stage B] Training samples: {len(X_train)}  Val: {len(X_val)}")
    model   = build_autoencoder(WINDOW, LSTM_UNITS)
    model.summary()

    history   = train_model(X_train, model)
    threshold = compute_threshold(model, X_val)

    # Stage C — Export + save artifacts
    tflite_size = export_tflite(model, X_train)
    save_artifacts(scaler, threshold)

    # Stage D — Edge inference on test data
    interp = load_tflite_interpreter()
    run_edge_simulation(series, interp, scaler, threshold, n_hours=200)

    # Stage E — Report
    print_summary_report(history, threshold, tflite_size)


if __name__ == "__main__":
    main()
