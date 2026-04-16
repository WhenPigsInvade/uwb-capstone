from flask import Flask, jsonify, request
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd
import time
import os

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

VALID_SENSORS = {"coil_temp", "ambient_temp", "humidity", "water_produced"}
SENSOR_UNITS  = {
    "coil_temp":      "°C",
    "ambient_temp":   "°C",
    "humidity":       "%",
    "water_produced": "g",
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

        if sensor_type not in VALID_SENSORS or value is None:
            print(f"Invalid reading: {reading}")
            continue

        point = (
            Point("sensor_data")
            .tag("device_id",   str(data["device_id"]))
            .tag("sensor_type", sensor_type)
            .tag("unit",        SENSOR_UNITS[sensor_type])
            .field("value",     float(value))
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
    # ------------------------
    # POST → ESP32 ingestion
    # ------------------------
    if request.method == "POST":
        try:
            data = request.get_json()
            print(f"Received: {data}")

            if not data or "device_id" not in data:
                return jsonify({"error": "Invalid payload"}), 400

            process_data(data)
            return jsonify({"status": "ok"}), 200

        except Exception as e:
            print(f"Error: {e}")
            return jsonify({"status": "error"}), 400

    # ------------------------
    # GET → existing query API
    # ------------------------
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
          |> limit(n: 5)
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
    return jsonify({"prediction": "TODO"}), 200


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

    # Skip Influx metadata lines starting with '#'
    df = pd.read_csv(CSV_FILE, comment="#")

    if df.empty:
        print("CSV is empty after filtering metadata.")
        return

    # Rename columns to match your schema
    df = df.rename(columns={
        "_time": "time",
        "_value": "value"
    })

    # Convert time
    df["time"] = pd.to_datetime(df["time"], format="ISO8601")

    points = []

    for _, row in df.iterrows():
        # Skip invalid rows just in case
        if pd.isna(row["value"]) or pd.isna(row["sensor_type"]):
            continue

        point = (
            Point("sensor_data")
            .tag("device_id", str(row["device_id"]))
            .tag("sensor_type", str(row["sensor_type"]))
            .tag("unit", str(row.get("unit", "")))  # optional
            .field("value", float(row["value"]))
            .time(row["time"], WritePrecision.NS)
        )
        points.append(point)

    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)

    print(f"Loaded {len(points)} points into InfluxDB.")


def wait_for_influx():
    import requests
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
            return False  # Found at least one record

    return True  # No data found

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