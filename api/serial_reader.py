import serial
import json
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime, timezone
import os

# --- adjust port to match your system ---
# Windows:  'COM3', 'COM4', etc.
# Mac:      '/dev/cu.usbserial-xxxx'
# Linux:    '/dev/ttyUSB0' or '/dev/ttyACM0'
SERIAL_PORT = 'COM3'
BAUD_RATE   = 57600

client    = InfluxDBClient(url=os.environ["INFLUX_URL"], token=os.environ["INFLUX_TOKEN"])
write_api = client.write_api(write_options=SYNCHRONOUS)

VALID_SENSORS = {"coil_temp", "ambient_temp", "humidity", "water_produced"}
SENSOR_UNITS  = {
    "coil_temp":      "°C",
    "ambient_temp":   "°C",
    "humidity":       "%",
    "water_produced": "g",
}

def process_data(raw_line):
    try:
        data = json.loads(raw_line)
    except json.JSONDecodeError:
        print(f"Skipping non-JSON line: {raw_line}")
        return

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
            .time(datetime.now(timezone.utc), WritePrecision.NS)
        )
        points.append(point)

    if points:
        write_api.write(
            bucket=os.environ["INFLUX_BUCKET"],
            org=os.environ["INFLUX_ORG"],
            record=points
        )
        print(f"Written {len(points)} points to InfluxDB")
    
def main():
    print(f"Listening on {SERIAL_PORT} at {BAUD_RATE} baud...")
    with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
        while True:
            line = ser.readline().decode('utf-8').strip()
            if line:
                print(f"Received: {line}")
                process_data(line)

if __name__ == "__main__":
    main()