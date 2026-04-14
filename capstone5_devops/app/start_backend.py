import uvicorn
import os
import sys

# Ensure we are in the correct directory to load models
APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_DIR)

if __name__ == "__main__":
    print("STARTING INDUSTRIAL AI BACKEND...")
    print(f"Current Directory: {os.getcwd()}")
    
    # Run the app on 8888 using the IP explicitly to avoid 'localhost' resolution errors
    try:
        uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
    except Exception as e:
        print("\nTIP: If you see 'Access Forbidden', try a different port like 9999 or 7777.")
