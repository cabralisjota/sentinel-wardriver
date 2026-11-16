from flask import Flask, jsonify
from pathlib import Path
import sqlite3

app = Flask(__name__)
from wardriver_addons import extras
app.register_blueprint(extras)
DB = Path(__file__).parent / "data/gps_wardriver.db"

@app.route("/api/dashboard")
def dashboard():
    if not DB.exists():
        return jsonify(error="Database not found"), 404

    with sqlite3.connect(DB) as db:
        db.row_factory = sqlite3.Row

        stats = db.execute("""
            SELECT
                COUNT(*) AS total,
                COUNT(DISTINCT bssid) AS networks,
                COUNT(DISTINCT timestamp) AS scans,
                COUNT(DISTINCT
                    ROUND(latitude,5) || ',' ||
                    ROUND(longitude,5)
                ) AS locations
            FROM observations
        """).fetchone()

        records = db.execute("""
            SELECT id, timestamp, ssid, bssid,
                   rssi, frequency, security,
                   latitude, longitude, accuracy
            FROM observations
            ORDER BY id DESC
            LIMIT 2000
        """).fetchall()

        route = db.execute("""
            SELECT timestamp,
                   AVG(latitude) AS lat,
                   AVG(longitude) AS lon,
                   COUNT(*) AS observations
            FROM observations
            WHERE latitude BETWEEN -90 AND 90
              AND longitude BETWEEN -180 AND 180
            GROUP BY timestamp
            ORDER BY timestamp DESC
            LIMIT 1000
        """).fetchall()

    return jsonify(
        stats=dict(stats),
        records=[dict(r) for r in records],
        route=[dict(r) for r in reversed(route)]
    )



@app.route("/api/flipper-status")
def sentinel_flipper_status():
    from flask import jsonify
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parent / "data/flipper_status.json"

    try:
        return jsonify(json.loads(path.read_text()))
    except (OSError, ValueError):
        return jsonify({"error": "Snapshot unavailable"}), 404

@app.route("/")
def home():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport"
      content="width=device-width,initial-scale=1">

<title>Sentinel Wardriver Dashboard</title>

<link rel="stylesheet"
 href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js">
</script>

<style>
* { box-sizing: border-box; }

body {
    margin: 0;
    background: #0b1220;
    color: #e2e8f0;
    font-family: Arial, sans-serif;
}

header {
    padding: 20px 16px;
    border-bottom: 1px solid #334155;
}

h1 {
    color: #38bdf8;
    font-size: 23px;
    margin: 0 0 6px;
}

.subtitle {
    color: #94a3b8;
    font-size: 13px;
}

main {
    padding: 14px;
    max-width: 1400px;
    margin: auto;
}

.stats {
    display: grid;
    grid-template-columns: repeat(2,1fr);
    gap: 10px;
    margin-bottom: 16px;
}

.stat {
    background: #172337;
    padding: 15px;
    border-radius: 12px;
}

.stat strong {
    display: block;
    color: #38bdf8;
    font-size: 27px;
}

.stat small {
    color: #94a3b8;
}

.panel {
    background: #172337;
    border-radius: 12px;
    margin-bottom: 16px;
    overflow: hidden;
}

.panel h3 {
    padding: 14px;
    margin: 0;
    font-size: 16px;
}

#map {
    height: 48vh;
    min-height: 270px;
    background: #23384b;
}

.toolbar {
    padding: 12px;
}

input {
    width: 100%;
    padding: 12px;
    background: #0b1220;
    color: white;
    border: 1px solid #475569;
    border-radius: 8px;
    font-size: 16px;
}

.table-wrap {
    overflow-x: auto;
}

table {
    border-collapse: collapse;
    width: 100%;
    font-size: 12px;
}

th, td {
    padding: 11px;
    text-align: left;
    border-bottom: 1px solid #334155;
    white-space: nowrap;
}

th {
    color: #38bdf8;
    background: #111c2e;
}

td {
    color: #cbd5e1;
}

#status, #record-count {
    color: #94a3b8;
    padding: 12px;
    font-size: 13px;
}

.signal {
    color: #4ade80;
    font-weight: bold;
}

@media (min-width: 700px) {
    .stats {
        grid-template-columns: repeat(4,1fr);
    }
}

.conn-menu summary {
    cursor: pointer;
    padding: 16px;
    color: #e2e8f0;
    font-size: 16px;
    font-weight: bold;
    list-style: none;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
}

.conn-menu summary::-webkit-details-marker {
    display: none;
}

.conn-menu summary::after {
    content: "▼";
    color: #38bdf8;
}

.conn-menu[open] summary::after {
    content: "▲";
}

.conn-body {
    padding: 0 16px 16px;
    overflow-wrap: anywhere;
}

.conn-menu[open] summary {
    border-bottom: 1px solid #334155;
    margin-bottom: 12px;
}

</style>
</head>

<body>

<header>
<h1>SENTINEL WARDRIVER</h1>
<div class="subtitle">
Wi-Fi Intelligence • GPS Tracking • Observation History
</div>
</header>\n
<details id="sentinel-flipper"
 style="margin:16px auto;max-width:1100px;
 background:#14243a;color:#edf5ff;
 border:1px solid #34516e;border-radius:12px;
 padding:16px;">

 <summary style="cursor:pointer;font-weight:bold;">
   📡 Flipper Zero — Device Integration
 </summary>

 <div style="padding:14px 4px;line-height:2;">
   <div>Device: <strong>Flipper Zero</strong></div>
   <div>Wi-Fi board: <strong>ESP32-S2 V1</strong></div>
   <div>USB CLI: <strong id="sf-status">Checking...</strong></div>
   <div>Last verified: <span id="sf-time">—</span></div>
   <div>Response received: <span id="sf-bytes">—</span></div>
   <div>GPS source: <strong>Android / Termux</strong></div>
   <div>Marauder observations: <strong>Not integrated yet</strong></div>
 </div>

 <p style="font-size:12px;color:#a9bfd5;">
   Status reflects the last saved USB test, not a live connection.
 </p>
</details>

<script>
(function () {
  fetch("/api/flipper-status", {cache:"no-store"})
    .then(function(response) {
      if (!response.ok) throw new Error("Snapshot unavailable");
      return response.json();
    })
    .then(function(data) {
      var success = data.usb_verified && data.cli_responded;

      document.getElementById("sf-status").textContent =
        success ? "Last test successful" : "Not verified";

      document.getElementById("sf-bytes").textContent =
        data.bytes_received || "Unknown";

      document.getElementById("sf-time").textContent =
        data.last_verified
          ? new Date(data.last_verified).toLocaleString()
          : "Unknown";
    })
    .catch(function() {
      document.getElementById("sf-status").textContent =
        "No saved connection status";
    });
})();
</script>


<main>

<div class="stats">
<div class="stat">
<strong id="total">0</strong>
<small>Observations</small>
</div>
<div class="stat">
<strong id="networks">0</strong>
<small>Unique BSSIDs</small>
</div>
<div class="stat">
<strong id="scans">0</strong>
<small>Recorded Scans</small>
</div>
<div class="stat">
<strong id="locations">0</strong>
<small>GPS Locations</small>
</div>
</div>

<section class="panel" style="padding:14px">
<details class="conn-menu">
<summary>Wi-Fi Connection Snapshot &amp; Last GPS Fix</summary>
<div class="conn-body">
<div id="device-info">Loading connection details...</div>
<p>
<a href="/export.csv"
   style="color:#38bdf8;font-weight:bold">
Download All Observations (CSV)
</a>
</p>
</div>
</details>
</section>

<section class="panel">
<h3>GPS Observation Map & Route</h3>
<div id="map"></div>
<div id="status">Loading GPS data...</div>
</section>

<section class="panel">
<h3>Complete Observation Details</h3>

<div class="toolbar">
<input id="search"
 placeholder="Search SSID, BSSID or security...">
<input id="min-rssi"
       type="number"
       min="-100"
       max="0"
       placeholder="Minimum signal, e.g. -70 dBm"
       style="margin-top:10px">
</div>

<div id="record-count"></div>

<div class="table-wrap">
<table>
<thead>
<tr>
<th>ID</th>
<th>Timestamp</th>
<th>SSID</th>
<th>BSSID</th>
<th>RSSI</th>
<th>Frequency</th>
<th>Security</th>
<th>Latitude</th>
<th>Longitude</th>
<th>Accuracy</th>
</tr>
</thead>
<tbody id="records"></tbody>
</table>
</div>
</section>

</main>

<script>
let map = null;
let markers = null;
let routeLine = null;
let firstLoad = true;
let allRecords = [];

if (window.L) {
    map = L.map("map").setView([0, 0], 2);

    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            maxZoom: 19,
            attribution: "&copy; OpenStreetMap contributors"
        }
    ).addTo(map);

    markers = L.layerGroup().addTo(map);
} else {
    document.getElementById("map").textContent =
        "Map library unavailable. Check internet connection.";
}

function value(v) {
    return v === null || v === undefined
        ? "—" : String(v);
}

function renderTable() {
    const query = document.getElementById("search")
        .value.toLowerCase();

    const tbody = document.getElementById("records");
    tbody.replaceChildren();

    const threshold =
        document.getElementById("min-rssi").value;

    const filtered = allRecords.filter(r =>
        [r.ssid, r.bssid, r.security]
        .some(v => String(v || "")
        .toLowerCase().includes(query)) &&
        (!threshold ||
         (r.rssi != null &&
          Number(r.rssi) >= Number(threshold)))
    );

    const fields = [
        "id", "timestamp", "ssid", "bssid",
        "rssi", "frequency", "security",
        "latitude", "longitude", "accuracy"
    ];

    for (const record of filtered) {
        const tr = document.createElement("tr");

        for (const field of fields) {
            const td = document.createElement("td");
            td.textContent = value(record[field]);

            if (field === "rssi") {
                td.className = "signal";
            }

            tr.appendChild(td);
        }

        tbody.appendChild(tr);
    }

    document.getElementById("record-count")
        .textContent =
        "Showing " + filtered.length +
        " of " + allRecords.length +
        " recently loaded observations";
}

function renderMap(points) {
    if (!map) return;

    markers.clearLayers();

    if (routeLine) {
        map.removeLayer(routeLine);
        routeLine = null;
    }

    const coords = [];

    for (const p of points) {
        if (p.lat == null || p.lon == null) continue;

        const position = [p.lat, p.lon];
        coords.push(position);

        const marker = L.circleMarker(position, {
            radius: 6,
            color: "#0284c7",
            fillColor: "#38bdf8",
            fillOpacity: 0.8
        });

        const popup = document.createElement("div");
        popup.style.whiteSpace = "pre-line";
        popup.textContent =
            "Scan: " + value(p.timestamp) +
            "\\nObservations: " + p.observations +
            "\\nLatitude: " + p.lat +
            "\\nLongitude: " + p.lon;

        marker.bindPopup(popup);
        marker.addTo(markers);
    }

    if (coords.length > 1) {
        routeLine = L.polyline(coords, {
            color: "#22c55e",
            weight: 3,
            opacity: 0.8
        }).addTo(map);
    }

    if (firstLoad && coords.length) {
        if (coords.length === 1) {
            map.setView(coords[0], 16);
        } else {
            map.fitBounds(coords, {
                padding: [25,25],
                maxZoom: 16
            });
        }
        firstLoad = false;
    }
}

async function refresh() {
    try {
        const response = await fetch(
            "/api/dashboard",
            {cache: "no-store"}
        );

        if (!response.ok) {
            throw new Error("Database API unavailable");
        }

        const data = await response.json();

        for (const field of [
            "total", "networks", "scans", "locations"
        ]) {
            document.getElementById(field)
                .textContent = data.stats[field];
        }

        allRecords = data.records;
        renderTable();
        renderMap(data.route);

        document.getElementById("status")
            .textContent =
            "Last updated: " +
            new Date().toLocaleTimeString() +
            " • Auto-refresh every 30 seconds";

    } catch (error) {
        document.getElementById("status")
            .textContent = "Error: " + error.message;
    }
}

document.getElementById("search")
    .addEventListener("input", renderTable);

function deviceField(label, value) {
    const line = document.createElement("div");
    line.style.padding = "6px 0";
    line.style.overflowWrap = "anywhere";
    line.textContent =
        label + ": " + (value ?? "Unavailable");
    return line;
}

async function loadDevice() {
    const panel = document.getElementById("device-info");

    try {
        const response = await fetch(
            "/api/device",
            {cache: "no-store"}
        );

        if (!response.ok) {
            throw new Error("Device API unavailable");
        }

        const d = await response.json();
        const gps = d.last_gps;

        panel.replaceChildren(
            deviceField(
                "Wi-Fi connection",
                !d.wifi_ssid ||
                d.wifi_ssid === "<unknown ssid>"
                    ? "Not connected to Wi-Fi"
                    : "Connected"
            ),
            deviceField(
                "Connected SSID",
                d.wifi_ssid === "<unknown ssid>"
                    ? null : d.wifi_ssid
            ),
            deviceField(
                "Connected BSSID",
                d.wifi_bssid === "02:00:00:00:00:00"
                    ? null : d.wifi_bssid
            ),
            deviceField(
                "Phone Wi-Fi IP",
                d.wifi_ip === "0.0.0.0"
                    ? null : d.wifi_ip
            ),
            deviceField("Phone outbound IP", d.outbound_ip),\n            deviceField("Wi-Fi details checked", d.wifi_checked_at),
            deviceField(
                "Connected Wi-Fi signal",
                d.rssi == null || d.rssi <= -127 ? null : d.rssi + " dBm"
            ),
            deviceField(
                "Connected frequency",
                d.frequency_mhz == null || d.frequency_mhz <= 0
                    ? null : d.frequency_mhz + " MHz"
            ),
            deviceField(
                "Last observation",
                gps ? gps.timestamp : null
            ),
            deviceField(
                "Last recorded GPS",
                gps ? gps.latitude + ", " +
                      gps.longitude : null
            ),
            deviceField(
                "GPS accuracy",
                gps && gps.accuracy != null
                    ? gps.accuracy + " m" : null
            )
        );

    } catch (error) {
        panel.textContent =
            "Device information unavailable: " +
            error.message;
    }
}

document.getElementById("min-rssi")
    .addEventListener("input", renderTable);

loadDevice();
setInterval(loadDevice, 30000);

refresh();
setInterval(refresh, 30000);
</script>

</body>
</html>
"""

if __name__ == "__main__":
    print("Sentinel Wardriver Dashboard")
    print("http://127.0.0.1:5001")
    app.run(host="127.0.0.1", port=5001, debug=False)
