import requests
import os

API_URL = "http://localhost:5000/api/sensors"

api_token = os.environ.get("API_TOKEN")
if not api_token:
    raise ValueError("Missing API_TOKEN environment variable")

def fetch_sensor_data(row_count=24):
    try:
        response = requests.get(API_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        status = data.get("status", "UNKNOWN")
        device = data.get("device", "UNDEFINED")
        sensors = [(s.get("name", ""), s.get("status", "")) for s in data.get("sensors", [])]
        return device, status, sensors[:row_count]
    except Exception as e:
        print(f"[ERROR] Failed to fetch API data: {e}")
        return "EPD-01", "ERROR", [(f"Sensor {i+1}", "ERR") for i in range(row_count)]
