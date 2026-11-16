import json
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

def get_json(command, timeout):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True
    )
    return json.loads(result.stdout)

print("Getting GPS location...")

try:
    gps = get_json(
        ["termux-location", "-p", "gps", "-r", "once"],
        40
    )

    if not isinstance(gps, dict) or not all(
        gps.get(k) is not None
        for k in ("latitude", "longitude")
    ):
        raise ValueError("No valid GPS fix")

    print("Scanning nearby Wi-Fi networks...")

    networks = get_json(
        ["termux-wifi-scaninfo"],
        25
    )

    if not isinstance(networks, list):
        raise ValueError("Unexpected Wi-Fi response")

    Path("data").mkdir(exist_ok=True)

    with sqlite3.connect("data/gps_wardriver.db") as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                ssid TEXT,
                bssid TEXT,
                rssi INTEGER,
                frequency INTEGER,
                security TEXT,
                latitude REAL,
                longitude REAL,
                accuracy REAL
            )
        """)

        timestamp = datetime.now(timezone.utc).isoformat()
        saved = 0

        for network in networks:
            if not isinstance(network, dict):
                continue

            db.execute("""
                INSERT INTO observations
                (timestamp, ssid, bssid, rssi,
                 frequency, security, latitude,
                 longitude, accuracy)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                network.get("ssid"),
                network.get("bssid"),
                network.get("rssi"),
                network.get("frequency_mhz"),
                network.get("capabilities"),
                gps["latitude"],
                gps["longitude"],
                gps.get("accuracy")
            ))
            saved += 1

    print(f"Saved {saved} GPS-tagged Wi-Fi observations.")
    print("Database: data/gps_wardriver.db")

except Exception as error:
    print(f"Scan failed: {error}")
