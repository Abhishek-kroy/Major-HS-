"""
Step 0 — Data Preparation
=========================
Reads ASHRAE dataset in memory-safe chunks and extracts a
"pilot facility" of 5 machines.  Output: ~10 MB CSV used
by ALL five capstones.

Run first, once.  Everything else depends on this output.

Expected files (after Kaggle download):
    Dataset_folder/train.csv
    Dataset_folder/building_metadata.csv
    Dataset_folder/weather_train.csv

Produces:
    data/processed/industrial_energy.csv
"""

import pandas as pd
import numpy as np
import os
import sys


# ── Config ────────────────────────────────────────────────────────
TARGET_MACHINES = [0, 1, 2, 3, 4]   # 5 buildings → 5 "machines"
CHUNK_SIZE      = 500_000
ASHRAE_DIR      = "Dataset_folder"
OUT_DIR         = "data/processed"
OUT_PATH        = f"{OUT_DIR}/industrial_energy.csv"


def check_raw_files():
    needed = [
        f"{ASHRAE_DIR}/train.csv",
        f"{ASHRAE_DIR}/building_metadata.csv",
        f"{ASHRAE_DIR}/weather_train.csv",
    ]
    missing = [f for f in needed if not os.path.isfile(f)]
    if missing:
        print("[ERROR] Missing raw files:")
        for f in missing:
            print(f"  {f}")
        print("\nDownload with:")
        print("  kaggle competitions download -c ashrae-energy-prediction -p ./Dataset_folder")
        print("  unzip ./Dataset_folder/ashrae-energy-prediction.zip -d ./Dataset_folder/")
        sys.exit(1)
    print("[OK] All raw files found.")


def load_meta_weather():
    meta    = pd.read_csv(f"{ASHRAE_DIR}/building_metadata.csv")
    weather = pd.read_csv(f"{ASHRAE_DIR}/weather_train.csv")
    meta    = meta[meta["building_id"].isin(TARGET_MACHINES)]
    print(f"[INFO] Metadata rows after filter: {len(meta)}")
    return meta, weather


def stream_electricity_readings():
    """
    Read train.csv in chunks so we never load the full ~1 GB into RAM.
    Keep only electricity meter (meter==0) for our 5 target machines.
    """
    kept = []
    total_read = 0
    print(f"[INFO] Streaming train.csv in chunks of {CHUNK_SIZE:,} rows…")
    for i, chunk in enumerate(pd.read_csv(f"{ASHRAE_DIR}/train.csv",
                                           chunksize=CHUNK_SIZE)):
        total_read += len(chunk)
        sub = chunk[
            (chunk["meter"] == 0) &
            (chunk["building_id"].isin(TARGET_MACHINES))
        ].copy()
        kept.append(sub)
        print(f"  chunk {i+1}: read {len(chunk):,} rows, kept {len(sub):,}")

    df = pd.concat(kept, ignore_index=True)
    print(f"[INFO] Total rows read: {total_read:,}  |  Kept: {len(df):,}")
    return df


def engineer_features(df, meta, weather):
    df = df.merge(meta,     on="building_id",         how="left")
    df = df.merge(weather,  on=["site_id","timestamp"], how="left")

    df["timestamp"]  = pd.to_datetime(df["timestamp"])
    df["hour"]       = df["timestamp"].dt.hour
    df["month"]      = df["timestamp"].dt.month
    df["dayofweek"]  = df["timestamp"].dt.dayofweek
    df["is_weekend"] = (df["dayofweek"] >= 5).astype(int)
    df["date"]       = df["timestamp"].dt.date

    # Rename to match the "industrial machine" narrative
    df.rename(columns={
        "building_id":    "machine_id",
        "meter_reading":  "kwh"
    }, inplace=True)

    # Sort for downstream windowing operations
    df.sort_values(["machine_id","timestamp"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def print_summary(df):
    print("\n── Dataset Summary ─────────────────────────────────────")
    print(f"  Shape       : {df.shape}")
    print(f"  Machines    : {sorted(df['machine_id'].unique())}")
    print(f"  Date range  : {df['timestamp'].min()} → {df['timestamp'].max()}")
    print(f"  kWh range   : {df['kwh'].min():.2f} – {df['kwh'].max():.2f}")
    print(f"  Null kWh    : {df['kwh'].isnull().sum()}")
    print("────────────────────────────────────────────────────────\n")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    check_raw_files()

    meta, weather = load_meta_weather()
    raw           = stream_electricity_readings()
    df            = engineer_features(raw, meta, weather)

    print_summary(df)

    df.to_csv(OUT_PATH, index=False)
    size_mb = os.path.getsize(OUT_PATH) / 1_048_576
    print(f"[DONE] Saved to {OUT_PATH}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main() 
