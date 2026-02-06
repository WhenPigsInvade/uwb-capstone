from flask import Flask, jsonify, request
from influxdb import InfluxDBClient
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd
import datetime


# @TODO Move to own config file
# ----------------------------
# Configuration
# ----------------------------
INFLUX_URL = "http://localhost:8086"
INFLUX_ORG = "exawater"
INFLUX_BUCKET = "database"
INFLUX_TOKEN = "RqVG5ECxqv3ztW4RyYATvaL07v2DYZmOMxgsTrRtjItImnDX7TNA_d75uGWPlWUCjeG5qVozn0y55PQO1kPD-A=="

SERVICE_PORT = 420

CSV_FILE = "data/data.csv"
MEASUREMENT = "environment"

app = Flask(__name__)
client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)

write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()

@app.route("/data", methods=['GET'])
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

    # Apply optional filters
    if device_id:
        query += f'|> filter(fn: (r) => r["device_id"] == "{device_id}")\n'

    if sensor_type:
        query += f'|> filter(fn: (r) => r["sensor_type"] == "{sensor_type}")\n'

    # If no filters AND no all=true → return latest 5
    if not request.args or (all_data != "true" and len(request.args) == 0):
        query += '''
          |> sort(columns: ["_time"], desc: true)
          |> limit(n: 5)
        '''

    # If all=true → no limit applied (full dataset returned)

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

@app.route("/prediction", methods=['GET'])
def get_prediction():
    message = {"prediction": "TODO"}
    return jsonify(message)

# @TODO
def read_sensors():
    return

# @TODO
def read_database():
    return

# @TODO remove loading from csv and integrate fully with influxdb
# ----------------------------
# Load CSV
# ----------------------------
def load_csv():
    print("Loading sensor CSV into InfluxDB...")

    df = pd.read_csv(CSV_FILE)
    df["time"] = pd.to_datetime(df["time"])

    points = []

    for _, row in df.iterrows():
        point = (
            Point("sensor_data")
            .tag("device_id", row["device_id"])
            .tag("sensor_type", row["sensor_type"])
            .field("value", float(row["value"]))
            .time(row["time"], WritePrecision.NS)
        )
        points.append(point)

    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)

    print("Sensor data loaded.")

# ----------------------------
# Startup
# ----------------------------
with app.app_context():
    load_csv()

if __name__ == "__main__":
    app.run(port=SERVICE_PORT)