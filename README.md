# Exawater Capstone Project

Repository for all code for Exawater.

# Setup

## InfluxDB Setup

1. Install Docker
2. Run 

    `docker run -d --name influxdb -p 8086:8086 -v influxdb-data:/var/lib/influxdb2 influxdb:2`

3. Open `http://localhost:8086` and complete the setup steps on screen.
    - Org: exawater
    - Initial Bucket: database

4. It will show a secret token, make sure to copy that down now, otherwise you will have to reset influx and restart step 2-3.

5. Copy that token over to a file named `token` in the uwb-capstone directory. (You need to make this file)

## API Service Setup

1. Pre-requisites:

If you are running without a venv:
```
sudo python3 -m pip install -U pip
sudo python3 -m pip install -U setuptools
```
With a venv:
```
pip3 install -U pip
pip3 install -U setuptools
```

2. Make sure you have the required libraries by running `pip install -r requirements.txt`

3. Run `python3 main.py` to start the service. The service port is `http://localhost:420`

## UI Setup

TODO