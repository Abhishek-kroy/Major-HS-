import time
import csv
import requests
import json
import random

# CONFIGURATION
API_URL = "http://127.0.0.1:3001/api/predict-proxy"
DATA_PATH = "data/processed/industrial_energy.csv"

def run_emulator():
    print("SENSOR EMULATOR STARTING (Live Dataset Mode - Port 8888)...")
    print(f"Reading from: {DATA_PATH}")
    
    try:
        with open(DATA_PATH, 'r') as f:
            reader = csv.DictReader(f)
            # Filter rows with actual load and limit for demo speed
            rows = [row for row in reader if float(row['kwh']) > 0]
            
        print(f"Filtered {len(rows)} active load rows. Starting live feed...")
        
        # We need a 24-reading sliding window for the LSTM Autoencoder
        for i in range(len(rows) - 24):
            window = rows[i:i+24]
            machine_id = int(window[0]['machine_id'])
            readings = [float(r['kwh']) for r in window]
            
            payload = {
                "machine_id": machine_id,
                "readings": readings,
                "predicted_kwh": readings[-1] * 1.05 # Spark forecast simulation
            }
            
            # Connection Retry Logic for Stability during Presentation
            success = False
            for attempt in range(3):
                try:
                    response = requests.post(API_URL, json=payload, timeout=5)
                    if response.status_code == 200:
                        res_data = response.json()
                        status = "ANOMALY" if res_data['is_anomaly'] else "NORMAL"
                        print(f"[{time.strftime('%H:%M:%S')}] Machine {machine_id} | Power: {readings[-1]:.2f}W | {status} (Recon Error: {res_data['recon_error']:.4f})")
                        success = True
                        break
                except Exception:
                    time.sleep(1)
            
            if not success:
                print(f"Connection Failed. Check if FastAPI is running on port 8888.")
                
            # Simulate real industrial sensor frequency
            time.sleep(0.5)
            
    except FileNotFoundError:
        print(f"Error: {DATA_PATH} not found. Please run data preparation first!")

if __name__ == "__main__":
    run_emulator()
