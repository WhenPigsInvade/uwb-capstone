from flask import Flask, jsonify
from influxdb import InfluxDBClient
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd
import datetime


# @TODO Move to own config file
# ----------------------------
# Configuration
# ----------------------------
INFLUX_URL = "http://localhost:69"
INFLUX_ORG = "exawater"
INFLUX_BUCKET = "sensor-data"

SERVICE_PORT = 420

CSV_FILE = "data/data.csv"
MEASUREMENT = "environment"

app = Flask(__name__)
client = InfluxDBClient(
    url=INFLUX_URL,
    org=INFLUX_ORG
)

write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()

@app.route("/data", methods=['GET'])
def get_data():
    message = {"time": datetime.datetime.now(),
               "temperature": "TODO",
               "humidity": "TODO"
               }
    return jsonify(message)

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