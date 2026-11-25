import random
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# In-memory storage & simulated decentralized sensor nodes
node_status = {}
memory_reports = []

NODES = [
    {"id": "NODE-01", "zone": "Industrial District", "base_temp": 38.5, "base_aqi": 165},
    {"id": "NODE-02", "zone": "Downtown Core", "base_temp": 37.2, "base_aqi": 140},
    {"id": "NODE-03", "zone": "Central Park", "base_temp": 29.4, "base_aqi": 55},
    {"id": "NODE-04", "zone": "Highway Junction", "base_temp": 39.1, "base_aqi": 185},
    {"id": "NODE-05", "zone": "Residential North", "base_temp": 32.0, "base_aqi": 80},
    {"id": "NODE-06", "zone": "Tech Hub", "base_temp": 34.8, "base_aqi": 110},
]

# Fault-tolerant validation filter
def is_valid_payload(temp, hum, aqi):
    return (-10.0 <= temp <= 65.0) and (0.0 <= hum <= 100.0) and (0.0 <= aqi <= 1000.0)

# Background thread simulating MQTT edge nodes + fault injection
def sensor_network_worker():
    cycle = 0
    while True:
        cycle += 1
        for node in NODES:
            # Simulate power outage on NODE-04 every 5th cycle
            if node["id"] == "NODE-04" and cycle % 5 == 0:
                print(f"[FAULT-SIM] {node['id']} power drop simulated.")
                continue

            temp = round(node["base_temp"] + random.uniform(-0.8, 1.2), 2)
            hum = round(random.uniform(35.0, 65.0), 2)
            aqi = round(node["base_aqi"] + random.uniform(-10, 15), 1)

            if is_valid_payload(temp, hum, aqi):
                node_status[node["id"]] = {
                    "last_seen": time.time(),
                    "zone": node["zone"],
                    "temp": temp,
                    "aqi": aqi
                }

        # Simulate corrupted sensor packet every 3rd cycle
        if cycle % 3 == 0:
            if not is_valid_payload(999.9, -5, 50):
                print("[FAULT-TOLERANCE] Blocked corrupted sensor packet (999.9°C).")

        time.sleep(3)

threading.Thread(target=sensor_network_worker, daemon=True).start()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/telemetry")
def get_telemetry():
    now = time.time()
    nodes = []
    for nid, info in node_status.items():
        status = "ONLINE" if (now - info["last_seen"]) < 10 else "OFFLINE (FAILOVER)"
        nodes.append({
            "node_id": nid,
            "zone": info["zone"],
            "temperature": info["temp"],
            "aqi": info["aqi"],
            "status": status
        })
    return jsonify({"nodes": nodes, "reports": memory_reports[-5:]})

@app.route("/api/report_hotspot", methods=["POST"])
def report_hotspot():
    data = request.json
    report = {
        "zone": data.get("zone", "Unknown"),
        "issue": data.get("issue", "High Asphalt Heat"),
        "action": data.get("action", "Deploy Mobile Mist"),
        "timestamp": datetime.utcnow().strftime("%H:%M:%S UTC")
    }
    memory_reports.append(report)
    return jsonify({"status": "success", "report": report})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
