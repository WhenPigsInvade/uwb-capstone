from flask import Flask, jsonify, request
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd
import requests
import time
import os
import math
from predict import predict

# ----------------------------
# Configuration
# ----------------------------
INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")

if not INFLUX_TOKEN:
    raise RuntimeError("INFLUX_TOKEN not found in environment variables")

SERVICE_PORT = 5001
CSV_FILE = os.getenv("CSV_FILE", "/data/data2.csv")

SHELLY_DEVICES = {
    "apower_1": "http://192.168.137.100/rpc/shelly.GetStatus",
    "apower_2": "http://192.168.137.101/rpc/shelly.GetStatus"
}

# --- UPDATED: Aligned with the new ESP32 payload ---
VALID_SENSORS = {
    "ambient_temp", "humidity", 
    "ambient_temp_outside", "humidity_outside", 
    "coil_temp_top", "coil_temp_mid", "coil_temp_bot", 
    "dew_point_inside", "dew_point_outside",     
    "current_weight", "water_rate_ml_hr",        
    "fan_speed", "chiller_temp", 
    "apower_1", "apower_2"
}

SENSOR_UNITS  = {
    "ambient_temp":         "°C",
    "humidity":             "%",
    "ambient_temp_outside": "°C",
    "humidity_outside":     "%",
    "coil_temp_top":        "°C",
    "coil_temp_mid":        "°C",
    "coil_temp_bot":        "°C",
    "dew_point_inside":     "°C",
    "dew_point_outside":    "°C",
    "current_weight":       "g",
    "water_rate_ml_hr":     "ml/hr",
    "fan_speed":            "lvl",
    "chiller_temp":         "°C",
    "apower_1":             "kWh",
    "apower_2":             "kWh",
}

app = Flask(__name__)

# ----------------------------
# InfluxDB Client
# ----------------------------
client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)

write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()

# ----------------------------
# Shared ingestion logic
# ----------------------------
def process_data(data):
    points = []

    for reading in data.get("readings", []):
        sensor_type = reading.get("sensor_type")
        value       = reading.get("value")

        # 1. Check if sensor is valid and value exists
        if sensor_type not in VALID_SENSORS or value is None:
            print(f"Invalid or missing reading: {reading}")
            continue

        # 2. Check for InfluxDB-breaking NaN values sent by the ESP32
        try:
            float_val = float(value)
            if math.isnan(float_val):
                print(f"Skipping NaN reading for {sensor_type}")
                continue
        except ValueError:
            print(f"Could not convert {value} to float for {sensor_type}")
            continue

        # 3. Create the InfluxDB Point
        point = (
            Point("sensor_data")
            .tag("device_id",   str(data["device_id"]))
            .tag("sensor_type", sensor_type)
            .tag("unit",        SENSOR_UNITS[sensor_type])
            .field("value",     float_val)
            .time(time.time_ns(), WritePrecision.NS)
        )
        points.append(point)

    if points:
        write_api.write(
            bucket=INFLUX_BUCKET,
            org=INFLUX_ORG,
            record=points
        )
        print(f"Written {len(points)} points to InfluxDB")


# ----------------------------
# Routes
# ----------------------------
@app.route("/data", methods=["GET", "POST"])
def data_handler():
    if request.method == "POST":
        try:
            data = request.get_json()
            print(f"Received: {data}")

            if not data or "device_id" not in data:
                return jsonify({"error": "Invalid payload"}), 400

            if "readings" not in data:
                data["readings"] = []

            for sensor_name, shelly_url in SHELLY_DEVICES.items():
                try:
                    shelly_resp = requests.get(shelly_url, timeout=5)
                    
                    if shelly_resp.status_code == 200:
                        shelly_data = shelly_resp.json()
                        apower = shelly_data.get("switch:0", {}).get("apower")
                        
                        if apower is not None:
                            # --- UPDATED: Convert Watts to kWh for a 20-minute interval ---
                            apower_kwh = (float(apower) * (20.0 / 60.0)) / 1000.0
                            
                            data["readings"].append({
                                "sensor_type": sensor_name,
                                "value": apower_kwh
                            })
                except Exception as e:
                    print(f"Warning: Failed to fetch Shelly data for {sensor_name} at {shelly_url}: {e}")

            process_data(data)
            return jsonify({"status": "ok"}), 200

        except Exception as e:
            print(f"Error: {e}")
            return jsonify({"status": "error"}), 400


    print("Data endpoint hit")

    device_id = request.args.get("device_id")
    sensor_type = request.args.get("sensor_type")
    start = request.args.get("start", "-100y")
    all_data = request.args.get("all")

    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {start})
      |> filter(fn: (r) => r["_measurement"] == "sensor_data")
    '''

    if device_id:
        query += f'|> filter(fn: (r) => r["device_id"] == "{device_id}")\n'

    if sensor_type:
        query += f'|> filter(fn: (r) => r["sensor_type"] == "{sensor_type}")\n'

    if all_data != "true":
        query += '''
          |> sort(columns: ["_time"], desc: true)
          |> limit(n: 10)
        '''

    tables = query_api.query(query)

    results = []
    for table in tables:
        for record in table.records:
            results.append({
                "time": record.get_time().isoformat(),
                "device_id": record.values.get("device_id"),
                "sensor_type": record.values.get("sensor_type"),
                "value": record.get_value()
            })

    return jsonify(results), 200


@app.route("/prediction", methods=["GET"])
def get_prediction():
    # --- UPDATED: Changed range from -1h to -100y to guarantee the absolute latest data point ---
    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -100y)
      |> filter(fn: (r) => r["_measurement"] == "sensor_data")
      |> filter(fn: (r) => 
            r["sensor_type"] == "fan_speed" or 
            r["sensor_type"] == "chiller_temp" or 
            r["sensor_type"] == "ambient_temp" or 
            r["sensor_type"] == "humidity" or 
            r["sensor_type"] == "coil_temp_top" or
            r["sensor_type"] == "dew_point_inside"
      )
      |> last()
    '''
    
    try:
        tables = query_api.query(query)
        current_state = {}
        
        for table in tables:
            for record in table.records:
                current_state[record.values.get("sensor_type")] = record.get_value()
                
        required_sensors = ["fan_speed", "chiller_temp", "ambient_temp", "humidity", "coil_temp_top", "dew_point_inside"]
        missing = [s for s in required_sensors if s not in current_state]
        if missing:
            return jsonify({"error": f"Missing data for sensors: {missing}. Ensure the device has broadcasted at least once."}), 400
        
        prediction_results = predict(
            curr_fan_sp=current_state["fan_speed"],
            curr_chiller_tp=current_state["chiller_temp"],
            curr_amb_dew_pt=current_state["dew_point_inside"],
            curr_amb_rh=current_state["humidity"],
            curr_coil_in_temp=current_state["coil_temp_top"]
        )
        
        response_data = {
            "optimal_chiller_temp": float(prediction_results[0]),
            "optimal_fan_speed": float(prediction_results[1]),
            "predicted_current_yield_ml_hr": float(prediction_results[2][0]),
            "predicted_current_energy_kwh": float(prediction_results[3][0])
        }
        
        return jsonify(response_data), 200

    except Exception as e:
        print(f"Error generating prediction: {e}")
        return jsonify({"error": "Failed to generate prediction", "details": str(e)}), 500

# ----------------------------
# Load CSV into Influx (one-time seed)
# ----------------------------
def load_csv():
    print(f"Looking for CSV at: {CSV_FILE}")
    print(f"File exists: {os.path.exists(CSV_FILE)}")
    if not os.path.exists(CSV_FILE):
        print("No CSV found. Skipping seed.")
        return

    print("Loading sensor CSV into InfluxDB...")

    df = pd.read_csv(CSV_FILE, comment="#")

    if df.empty:
        print("CSV is empty after filtering metadata.")
        return

    df = df.rename(columns={
        "_time": "time",
        "_value": "value"
    })

    df["time"] = pd.to_datetime(df["time"], format="ISO8601")

    points = []

    for _, row in df.iterrows():
        if pd.isna(row["value"]) or pd.isna(row["sensor_type"]):
            continue

        point = (
            Point("sensor_data")
            .tag("device_id", str(row["device_id"]))
            .tag("sensor_type", str(row["sensor_type"]))
            .tag("unit", str(row.get("unit", ""))) 
            .field("value", float(row["value"]))
            .time(row["time"], WritePrecision.NS)
        )
        points.append(point)

    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)

    print(f"Loaded {len(points)} points into InfluxDB.")


def wait_for_influx():
    url = "http://influxdb:8086/health"

    for i in range(20):
        try:
            r = requests.get(url)
            if r.status_code == 200:
                print("InfluxDB is ready!")
                return
        except:
            pass

        print("Waiting for InfluxDB...")
        time.sleep(3)

    raise RuntimeError("InfluxDB failed to start")


def is_bucket_empty():
    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -100y)
      |> limit(n: 1)
    '''

    tables = query_api.query(query)

    for table in tables:
        for _ in table.records:
            return False 

    return True 


# ----------------------------
# Startup
# ----------------------------
if __name__ == "__main__":
    wait_for_influx()

    if is_bucket_empty():
        print("Bucket is empty. Seeding from CSV...")
        load_csv()
    else:
        print("Bucket already contains data. Skipping seed.")
    app.run(host="0.0.0.0", port=SERVICE_PORT, debug=True)