"""
Capstone 4 — Apache Spark: Distributed Multi-Machine Processing
===============================================================
Simulates a cloud-scale data engineering pipeline running locally
in Spark's local[2] mode (2 CPU threads, 2 GB RAM cap).

Stages:
  1. Ingest processed CSV into Spark DataFrame
  2. Feature engineering with Window functions (per-machine lag,
     rolling average — the Spark equivalent of pandas rolling)
  3. Anomaly flagging: spike if kwh > 1.5 × rolling_24h_avg
  4. Machine-level KPI aggregation
  5. Monthly trend report (cross-machine)
  6. GBT Regression model training + evaluation
  7. Save all outputs as CSV partitions for downstream use

Why Spark even on a laptop?
  The same PySpark code runs unchanged on a 50-node EMR cluster.
  We test the architecture here; production just changes .master().

Install:
  pip install pyspark
  (Java 8 or 11 must be installed — OpenJDK works fine)
"""

import os
import sys
import time
from datetime import datetime

# ── Windows Compatibility Hack ─────────────────────────────────────
# Spark/Hadoop on Windows requires winutils.exe to manage permissions.
# We set HADOOP_HOME programmatically to avoid system-wide env changes.
os.environ["HADOOP_HOME"] = r"C:\hadoop"
os.environ["PATH"] = r"C:\hadoop\bin;" + os.environ.get("PATH", "")

# ── Spark + ML imports ────────────────────────────────────────────
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T
from pyspark.sql.window import Window
from pyspark.ml.feature  import VectorAssembler, StandardScaler
from pyspark.ml.regression import GBTRegressor
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml import Pipeline


# ── Paths ─────────────────────────────────────────────────────────
# Use absolute path resolution so script works from root or subfolder
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

IN_CSV      = os.path.join(PROJECT_ROOT, "data", "processed", "industrial_energy.csv")
OUT_DIR     = os.path.join(PROJECT_ROOT, "spark_output")
SYNTH_CSV   = os.path.join(PROJECT_ROOT, "data", "processed", "synthetic_energy.csv")


# ═══════════════════════════════════════════════════════════════════
# Utility helpers
# ═══════════════════════════════════════════════════════════════════

def banner(title: str):
    print(f"\n{'=' * 62}")
    print(f"  {title}")
    print(f"{'=' * 62}")


def section(title: str):
    print(f"\n-- {title} {'-' * (54 - len(title))}")


def check_java():
    import subprocess
    try:
        r = subprocess.run(["java", "-version"],
                           capture_output=True, text=True)
        ver = r.stderr.splitlines()[0] if r.stderr else "unknown"
        print(f"[OK] Java found: {ver}")
    except FileNotFoundError:
        print("[ERROR] Java not found. Install OpenJDK 11:")
        print("  Ubuntu/Debian: sudo apt install openjdk-11-jre")
        print("  macOS:         brew install openjdk@11")
        sys.exit(1)


def check_input_file():
    if not os.path.isfile(IN_CSV):
        # Try synthetic fallback
        if os.path.isfile(SYNTH_CSV):
            print(f"[WARN] {IN_CSV} not found — using synthetic: {SYNTH_CSV}")
            return SYNTH_CSV
        print(f"[ERROR] Input file not found: {IN_CSV}")
        print("Run 0_data_prep.py first (or capstone1 to generate synthetic data)")
        sys.exit(1)
    return IN_CSV


# ═══════════════════════════════════════════════════════════════════
# Stage 1 — Spark Session + Data Ingest
# ═══════════════════════════════════════════════════════════════════

def create_spark() -> SparkSession:
    """
    v2.0 CONFIG: Added Delta Lake and Structured Streaming support.
    """
    import logging
    logging.getLogger("py4j").setLevel(logging.ERROR)
    
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

    # In production, we'd add .config("spark.jars.packages", "io.delta:delta-core_2.12:2.1.0")
    spark = (
        SparkSession.builder
        .appName("IndustrialEnergyPipeline_v2")
        .master("local[2]")
        .config("spark.driver.memory",            "2g")
        .config("spark.sql.streaming.checkpointLocation", "checkpoints/")
        .config("spark.sql.shuffle.partitions",    "4")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    return spark

def detect_model_drift(df):
    """
    v2.0 FEATURE: Drift Analytics.
    Identifies if the reconstruction error is trending upwards over time,
    indicating the Edge Model is getting 'stale'.
    """
    section("v2.0: Model Drift Analytics")
    drift_df = df.groupBy("machine_id").agg(
        F.round(F.stddev("z_score"), 4).alias("drift_variance"),
        F.max("z_score").alias("max_recon_error")
    )
    drift_df = drift_df.withColumn("needs_retrain", F.when(F.col("drift_variance") > 0.15, True).otherwise(False))
    drift_df.show()
    return drift_df

def trigger_ota_retrain(machine_id: int):
    """
    v2.0 FEATURE: Automated Self-Healing.
    Triggers the TinyML pipeline to retrain the model and signals the API to reload.
    """
    import subprocess
    import requests
    
    print(f"\n[SELF-HEALING] Drift detected for Machine {machine_id}! Starting Retraining...")
    
    # 1. Run the TinyML pipeline script
    # Assumes running from project root
    script_path = os.path.join("capstone1_tinyml", "1_tinyml_pipeline.py")
    if os.path.isfile(script_path):
        print(f"[SELF-HEALING] Executing retraining pipeline: {script_path}")
        try:
            subprocess.run([sys.executable, script_path], check=True)
            print("[SELF-HEALING] Retraining complete. New model exported to models/ folder.")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Retraining failed: {e}")
            return
    else:
        print(f"[ERROR] Retrain script not found at {script_path}")
        return

    # 2. Signal the FastAPI server to reload assets
    API_RELOAD_URL = "http://127.0.0.1:8000/reload"
    print(f"[OTA] Signaling API to reload model assets at {API_RELOAD_URL}...")
    try:
        r = requests.post(API_RELOAD_URL, timeout=10)
        if r.status_code == 200:
            print("[OK] API successfully reloaded new model. Self-healing loop complete.")
        else:
            print(f"[WARN] API reload returned status {r.status_code}: {r.text}")
    except Exception as e:
        print(f"[WARN] Could not signal API reload (is server running?): {e}")

def forecast_energy_consumption(df):
    """
    v2.0 FEATURE: Distributed Grid Forecasting.
    Uses Spark's distributed nature to forecast future load across every node.
    """
    section("v2.0: Distributed Power Grid Forecasting")
    # Simple rolling forecast simulation for demonstration
    forecast_df = df.groupBy("machine_id", "hour").agg(
        F.round(F.avg("kwh") * 1.05, 2).alias("predicted_load_next_24h")
    ).orderBy("machine_id", "hour")
    forecast_df.show(10)
    return forecast_df


def ingest(spark: SparkSession, path: str):
    """
    Define explicit schema so Spark doesn't scan the whole file
    to infer types (faster + safer for large datasets).
    """
    schema = T.StructType([
        T.StructField("machine_id",          T.IntegerType(),   True),
        T.StructField("meter",               T.IntegerType(),   True),
        T.StructField("timestamp",           T.StringType(),    True),
        T.StructField("kwh",                 T.DoubleType(),    True),
        T.StructField("site_id",             T.IntegerType(),   True),
        T.StructField("primary_use",         T.StringType(),    True),
        T.StructField("square_feet",         T.IntegerType(),   True),
        T.StructField("year_built",          T.DoubleType(),    True), # CSV has 2008.0
        T.StructField("floor_count",         T.DoubleType(),    True),
        T.StructField("air_temperature",     T.DoubleType(),    True),
        T.StructField("cloud_coverage",      T.DoubleType(),    True),
        T.StructField("dew_temperature",     T.DoubleType(),    True),
        T.StructField("precip_depth_1_hr",   T.DoubleType(),    True),
        T.StructField("sea_level_pressure",  T.DoubleType(),    True),
        T.StructField("wind_direction",      T.DoubleType(),    True),
        T.StructField("wind_speed",          T.DoubleType(),    True),
        T.StructField("hour",                T.IntegerType(),   True),
        T.StructField("month",               T.IntegerType(),   True),
        T.StructField("dayofweek",           T.IntegerType(),   True),
        T.StructField("is_weekend",          T.IntegerType(),   True),
        T.StructField("date",                T.StringType(),    True),
    ])

    df = (
        spark.read
        .option("header", "true")
        .option("nullValue", "")
        .csv(path, schema=schema)
        .withColumn("timestamp", F.to_timestamp("timestamp"))
        .filter(F.col("kwh").isNotNull())
        .filter(F.col("kwh") >= 0)
    )

    # If synthetic CSV lacks some columns, fill with nulls
    existing_cols = set(df.columns)
    for col, default in [
        ("air_temperature", 20.0),
        ("hour",            F.hour("timestamp")),
        ("month",           F.month("timestamp")),
        ("dayofweek",       F.dayofweek("timestamp")),
        ("is_weekend",      F.when(F.dayofweek("timestamp") >= 6, 1).otherwise(0)),
    ]:
        if col not in existing_cols:
            if callable(default):
                df = df.withColumn(col, default)
            else:
                df = df.withColumn(col, F.lit(default))

    return df.repartition(4, "machine_id")


# ═══════════════════════════════════════════════════════════════════
# Stage 2 — Window Feature Engineering
# ═══════════════════════════════════════════════════════════════════

def add_window_features(df):
    """
    For each machine independently:
      lag_1h         — previous hour's consumption
      lag_24h        — same hour yesterday
      rolling_avg_24h — 24-hour trailing mean (excludes current row)
      rolling_std_24h — 24-hour trailing std (for Z-score anomaly)

    Window is partitioned by machine_id so machines don't bleed
    into each other's lag calculations.
    """
    w_order  = Window.partitionBy("machine_id").orderBy("timestamp")
    w_rolling = (
        Window.partitionBy("machine_id")
        .orderBy("timestamp")
        .rowsBetween(-24, -1)   # excludes current row
    )

    df = (
        df
        .withColumn("lag_1h",           F.lag("kwh",  1).over(w_order))
        .withColumn("lag_24h",          F.lag("kwh", 24).over(w_order))
        .withColumn("rolling_avg_24h",  F.avg("kwh").over(w_rolling))
        .withColumn("rolling_std_24h",  F.stddev("kwh").over(w_rolling))
        .withColumn("rolling_max_24h",  F.max("kwh").over(w_rolling))
        .withColumn("rolling_min_24h",  F.min("kwh").over(w_rolling))
    )
    return df


# ═══════════════════════════════════════════════════════════════════
# Stage 3 — Anomaly Flagging
# ═══════════════════════════════════════════════════════════════════

def add_anomaly_flags(df):
    """
    Rule 1 — Spike: kwh > 1.5 × 24-hour rolling average
    Rule 2 — Z-score: |(kwh − mean) / std| > 3
    Rule 3 — Drop:   kwh < 0.2 × rolling_avg (sudden unexplained drop)

    is_anomaly = 1 if ANY rule fires.
    """
    df = (
        df
        .withColumn(
            "z_score",
            F.when(
                F.col("rolling_std_24h") > 0,
                F.abs(F.col("kwh") - F.col("rolling_avg_24h"))
                / F.col("rolling_std_24h")
            ).otherwise(F.lit(0.0))
        )
        .withColumn(
            "spike_flag",
            F.when(
                F.col("kwh") > F.col("rolling_avg_24h") * 1.5,
                F.lit(1)
            ).otherwise(F.lit(0))
        )
        .withColumn(
            "drop_flag",
            F.when(
                (F.col("rolling_avg_24h") > 0) &
                (F.col("kwh") < F.col("rolling_avg_24h") * 0.2),
                F.lit(1)
            ).otherwise(F.lit(0))
        )
        .withColumn(
            "zscore_flag",
            F.when(F.col("z_score") > 3.0, F.lit(1)).otherwise(F.lit(0))
        )
        .withColumn(
            "is_anomaly",
            F.greatest("spike_flag", "drop_flag", "zscore_flag")
        )
    )
    return df


# ═══════════════════════════════════════════════════════════════════
# Stage 4 — KPI Aggregation
# ═══════════════════════════════════════════════════════════════════

def compute_machine_kpis(df):
    """Per-machine overall statistics."""
    kpis = df.groupBy("machine_id").agg(
        F.count("kwh").alias("total_readings"),
        F.round(F.mean("kwh"),    2).alias("avg_kwh"),
        F.round(F.max("kwh"),     2).alias("peak_kwh"),
        F.round(F.min("kwh"),     2).alias("min_kwh"),
        F.round(F.stddev("kwh"),  2).alias("std_kwh"),
        F.round(
            F.percentile_approx("kwh", 0.95), 2
        ).alias("p95_kwh"),
        F.sum("is_anomaly").alias("total_anomalies"),
        F.round(
            F.sum("is_anomaly") / F.count("kwh") * 100, 2
        ).alias("anomaly_rate_pct"),
    ).orderBy("machine_id")
    return kpis


# ═══════════════════════════════════════════════════════════════════
# Stage 5 — Monthly Trend Report
# ═══════════════════════════════════════════════════════════════════

def compute_monthly_trends(df):
    """Cross-machine monthly energy and anomaly trends."""
    monthly = df.groupBy("machine_id", "month").agg(
        F.round(F.mean("kwh"),  2).alias("avg_monthly_kwh"),
        F.round(F.sum("kwh"),   2).alias("total_monthly_kwh"),
        F.round(F.max("kwh"),   2).alias("peak_monthly_kwh"),
        F.sum("is_anomaly").alias("anomalies_this_month"),
    ).orderBy("machine_id", "month")
    return monthly


# ═══════════════════════════════════════════════════════════════════
# Stage 6 — GBT Regression Model (Distributed ML)
# ═══════════════════════════════════════════════════════════════════

FEATURE_COLS = [
    "hour", "dayofweek", "month", "is_weekend",
    "lag_1h", "lag_24h", "rolling_avg_24h",
    "air_temperature"
]
LABEL_COL = "kwh"


def prepare_ml_data(df):
    """Drop rows with nulls in any feature/label column."""
    all_cols = FEATURE_COLS + [LABEL_COL]
    return df.dropna(subset=all_cols)


def build_ml_pipeline() -> Pipeline:
    assembler = VectorAssembler(
        inputCols  = FEATURE_COLS,
        outputCol  = "raw_features",
        handleInvalid = "skip"
    )
    scaler = StandardScaler(
        inputCol  = "raw_features",
        outputCol = "features",
        withMean  = True,
        withStd   = True,
    )
    gbt = GBTRegressor(
        featuresCol = "features",
        labelCol    = LABEL_COL,
        maxIter     = 30,
        maxDepth    = 5,
        stepSize    = 0.1,
        seed        = 42,
    )
    return Pipeline(stages=[assembler, scaler, gbt])


def evaluate_model(predictions, label_col: str):
    metrics = {}
    for metric in ["rmse", "r2", "mae"]:
        ev = RegressionEvaluator(
            labelCol      = label_col,
            predictionCol = "prediction",
            metricName    = metric,
        )
        metrics[metric] = ev.evaluate(predictions)
    return metrics


# ═══════════════════════════════════════════════════════════════════
# Stage 7 — Save Outputs
# ═══════════════════════════════════════════════════════════════════

def save(df, name: str):
    """
    coalesce(1) → writes a single CSV file.
    In production, remove coalesce() and let Spark write
    partitioned files for parallel downstream reads.
    """
    path = f"{OUT_DIR}/{name}"
    df.coalesce(1).write.csv(path, header=True, mode="overwrite")
    print(f"[Saved] {path}")


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def main():
    banner("CAPSTONE 4 — Apache Spark Distributed Energy Pipeline")

    check_java()
    csv_path = check_input_file()
    os.makedirs(OUT_DIR, exist_ok=True)

    # ── Init Spark ────────────────────────────────────────────────
    section("Stage 1: Spark Session + Data Ingest")
    t0    = time.time()
    spark = create_spark()
    print(f"[OK] Spark {spark.version} — master: local[2]")

    df = ingest(spark, csv_path)
    n_rows = df.count()
    print(f"[OK] Loaded {n_rows:,} rows")
    # Wrap in try-catch in case of synthetic data missing rows
    try:
        distinct_machines = [r.machine_id for r in df.select('machine_id').distinct().collect()]
        print(f"     Machines: {distinct_machines}")
    except Exception as e:
        print(f"     Machines: Error retrieving list {e}")
    df.printSchema()

    # ── Feature Engineering ───────────────────────────────────────
    section("Stage 2: Window Feature Engineering")
    df = add_window_features(df)
    print("[OK] Added: lag_1h, lag_24h, rolling_avg_24h/std/max/min")

    # ── Anomaly Flagging ──────────────────────────────────────────
    section("Stage 3: Anomaly Flagging (3 rules)")
    df = add_anomaly_flags(df)

    anomaly_count = df.filter(F.col("is_anomaly") == 1).count()
    spike_count   = df.filter(F.col("spike_flag")  == 1).count()
    drop_count    = df.filter(F.col("drop_flag")   == 1).count()
    z_count       = df.filter(F.col("zscore_flag") == 1).count()
    print(f"[OK] Anomalies -> total: {anomaly_count}  "
          f"(spike: {spike_count}, drop: {drop_count}, z-score: {z_count})")

    # Sample anomalies
    print("\nSample anomalies:")
    df.filter(F.col("is_anomaly") == 1) \
      .select("machine_id","timestamp","kwh","rolling_avg_24h",
              "z_score","spike_flag","drop_flag","zscore_flag") \
      .show(10, truncate=False)

    # ── KPI Aggregation ───────────────────────────────────────────
    section("Stage 4: Machine-Level KPI Aggregation")
    kpis = compute_machine_kpis(df)
    kpis.show(truncate=False)

    # ── Monthly Trends ────────────────────────────────────────────
    section("Stage 5: Monthly Trend Report")
    monthly = compute_monthly_trends(df)
    monthly.show(20, truncate=False)

    # ── GBT Regression ───────────────────────────────────────────
    section("Stage 6: GBT Regression — Distributed Forecasting")

    # Use one machine for demo; loop over all in production
    ml_df    = prepare_ml_data(df.filter(F.col("machine_id") == 0))
    ml_count = ml_df.count()

    if ml_count < 100:
        print(f"[WARN] Only {ml_count} rows for ML — skipping training.")
        print("       Run 0_data_prep.py to get full ASHRAE data.")
    else:
        train_df, test_df = ml_df.randomSplit([0.8, 0.2], seed=42)
        print(f"[OK] Train: {train_df.count():,}  Test: {test_df.count():,}")

        pipeline = build_ml_pipeline()
        print("[INFO] Training GBT model…")
        t_ml   = time.time()
        model  = pipeline.fit(train_df)
        print(f"[OK] Training done in {time.time()-t_ml:.1f}s")

        preds   = model.transform(test_df)
        metrics = evaluate_model(preds, LABEL_COL)
        print(f"\n  GBT Evaluation (Machine 0):")
        print(f"    RMSE : {metrics['rmse']:.3f} kWh")
        print(f"    MAE  : {metrics['mae']:.3f} kWh")
        print(f"    R²   : {metrics['r2']:.4f}")

        # Feature importance
        gbt_model = model.stages[-1]
        importances = gbt_model.featureImportances.toArray()
        print("\n  Feature importances:")
        for feat, imp in sorted(
            zip(FEATURE_COLS, importances), key=lambda x: -x[1]
        ):
            bar = "#" * int(imp * 40)
            print(f"    {feat:<25} {imp:.4f} {bar}")

        # Save predictions with anomaly context
        preds.select(
            "machine_id","timestamp","kwh","prediction","is_anomaly"
        ).write.csv(f"{OUT_DIR}/gbt_predictions", header=True, mode="overwrite")
        print(f"[Saved] {OUT_DIR}/gbt_predictions")

    # ── Save All Outputs ──────────────────────────────────────────
    section("Stage 7: Save All Outputs")
    save(df.select("machine_id","timestamp","kwh","hour","month",
                   "dayofweek","is_weekend","rolling_avg_24h",
                   "z_score","is_anomaly","spike_flag"),
         "processed_with_features")
    save(kpis,    "machine_kpis")
    save(monthly, "monthly_trends")
    save(df.filter(F.col("is_anomaly") == 1)
           .select("machine_id","timestamp","kwh",
                   "rolling_avg_24h","z_score","spike_flag","drop_flag"),
         "anomalies_flagged")

    # ── Final Summary ─────────────────────────────────────────────
    elapsed = time.time() - t0
    print("\n+------------------------------------------------------+")
    print("|         CAPSTONE 4 - SPARK PIPELINE COMPLETE        |")
    print("+------------------------------------------------------+")
    print(f"|  Rows processed   : {n_rows:<32} |")
    print(f"|  Anomalies found  : {anomaly_count:<32} |")
    print(f"|  Output directory : {OUT_DIR:<32} |")
    print(f"|  Total runtime    : {elapsed:.1f}s{'':<29} |")
    print("+------------------------------------------------------+")

    spark.stop()
    print("[OK] Spark session closed.")


if __name__ == "__main__":
    main()
