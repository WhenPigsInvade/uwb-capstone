from flask import Flask, jsonify, request
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd
import os

# ----------------------------
# Configuration
# ----------------------------
INFLUX_URL = "http://influxdb:8086"   # service name in docker-compose
INFLUX_ORG = "exawater"
INFLUX_BUCKET = "database"
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")

if not INFLUX_TOKEN:
    raise RuntimeError("INFLUX_TOKEN not found in environment variables")

SERVICE_PORT = 5000
CSV_FILE = "/data/data.csv"

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
# Routes
# ----------------------------
@app.route("/data", methods=["GET"])
def get_data():
    device_id = request.args.get("device_id")
    sensor_type = request.args.get("sensor_type")
    start = request.args.get("start", "-30d")
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

    # Only limit if all != true
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
    if not os.path.exists(CSV_FILE):
        print("No CSV found. Skipping seed.")
        return

    print("Loading sensor CSV into InfluxDB...")

    df = pd.read_csv(CSV_FILE)
    df["time"] = pd.to_datetime(df["time"])

    points = []

    for _, row in df.iterrows():
        point = (
            Point("sensor_data")
            .tag("device_id", str(row["device_id"]))
            .tag("sensor_type", str(row["sensor_type"]))
            .field("value", float(row["value"]))
            .time(row["time"], WritePrecision.NS)
        )
        points.append(point)

    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)

    print("Sensor data loaded.")


# ----------------------------
# Startup
# ----------------------------
if __name__ == "__main__":
    load_csv()
    app.run(host="0.0.0.0", port=SERVICE_PORT)