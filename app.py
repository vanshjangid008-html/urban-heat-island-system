import json
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify
import paho.mqtt.client as mqtt
from pymongo import MongoClient

app = Flask(__name__)

try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
    client.server_info()
    db = client["urban_heat_island"]
    readings_col = db["sensor_readings"]
    reports_col = db["citizen_reports"]
    USE_MONGO = True
except Exception:
    USE_MONGO = False
    memory_readings = []
    memory_reports = []

node_status = {}

def is_valid_payload(data):
    try:
        temp = float(data["temperature"])
        hum = float(data["humidity"])
        aqi = float(data["aqi"])
        if not (-10.0 <= temp <= 65.0): return False
        if not (0.0 <= hum <= 100.0): return False
        if not (0.0 <= aqi <= 1000.0): return False
        return True
    except (KeyError, ValueError, TypeError):
        return False

MQTT_BROKER = "://hivemq.com"
MQTT_TOPIC = "metro/uhi/sensors/#"

def on_connect(client, userdata, flags, rc):
    client.subscribe(MQTT_TOPIC, qos=1)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        if not is_valid_payload(payload):
            return

        record = {
            "node_id": payload["node_id"],
            "zone": payload.get("zone", "Downtown"),
            "temperature": round(float(payload["temperature"]), 2),
            "humidity": round(float(payload["humidity"]), 2),
            "aqi": round(float(payload["aqi"]), 1),
            "timestamp": datetime.utcnow().isoformat()
        }

        node_status[record["node_id"]] = {
            "last_seen": time.time(),
            "zone": record["zone"],
            "temp": record["temperature"],
            "aqi": record["aqi"]
        }

        if USE_MONGO:
            readings_col.insert_one(record.copy())
        else:
            memory_readings.append(record)
            if len(memory_readings) > 200:
                memory_readings.pop(0)
    except Exception as e:
        print(f"[ERROR] {e}")

def start_mqtt():
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_BROKER, 1883, 60)
    mqtt_client.loop_forever()

threading.Thread(target=start_mqtt, daemon=True).start()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/telemetry")
def get_telemetry():
    now = time.time()
    nodes = []
    for nid, info in node_status.items():
        status = "ONLINE" if (now - info["last_seen"]) < 15 else "OFFLINE (FAILOVER)"
        nodes.append({
            "node_id": nid,
            "zone": info["zone"],
            "temperature": info["temp"],
            "aqi": info["aqi"],
            "status": status
        })
    reports = list(reports_col.find({}, {"_id": 0}).sort("timestamp", -1).limit(5)) if USE_MONGO else memory_reports[-5:]
    return jsonify({"nodes": nodes, "reports": reports})

@app.route("/api/report_hotspot", methods=["POST"])
def report_hotspot():
    data = request.json
    report = {
        "zone": data.get("zone", "Unknown"),
        "issue": data.get("issue", "High Asphalt Heat"),
        "action": data.get("action", "Deploy Mobile Mist / Tree Cover"),
        "timestamp": datetime.utcnow().strftime("%H:%M:%S UTC")
    }
    if USE_MONGO:
        reports_col.insert_one(report.copy())
    else:
        memory_reports.append(report)
    return jsonify({"status": "success", "report": report})

if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)
