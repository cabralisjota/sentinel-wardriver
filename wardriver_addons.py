import csv
import io
import json
import socket
import sqlite3
import struct
import subprocess

from pathlib import Path
from flask import Blueprint, jsonify, Response, stream_with_context

extras = Blueprint("extras", __name__)
DB = Path(__file__).parent / "data/gps_wardriver.db"


def get_wifi_info():
    try:
        path = (
            Path(__file__).parent
            / "data/wifi_connection_cache.json"
        )
        snapshot = json.loads(path.read_text())
        info = snapshot.get("info", {})

        if not isinstance(info, dict):
            return {}

        return {
            **info,
            "_checked_at": snapshot.get("checked_at")
        }

    except (OSError, ValueError):
        return {}


def get_outbound_ip():
    destinations = [
        (socket.AF_INET, ("1.1.1.1", 80)),
        (socket.AF_INET6,
         ("2606:4700:4700::1111", 80, 0, 0))
    ]

    for family, address in destinations:
        try:
            with socket.socket(
                family, socket.SOCK_DGRAM
            ) as sock:
                sock.connect(address)
                return sock.getsockname()[0]
        except OSError:
            continue

    return None


def get_wifi_ip(info):
    value = info.get("ip_address") or info.get("ip")

    if isinstance(value, int) and value:
        return socket.inet_ntoa(
            struct.pack("<I", value & 0xffffffff)
        )

    if isinstance(value, str) and "." in value:
        return value

    return None


@extras.route("/api/device")
def device_info():
    wifi = get_wifi_info()

    last_gps = None

    if DB.exists():
        with sqlite3.connect(DB) as db:
            row = db.execute("""
                SELECT timestamp, latitude,
                       longitude, accuracy
                FROM observations
                ORDER BY id DESC
                LIMIT 1
            """).fetchone()

            if row:
                last_gps = {
                    "timestamp": row[0],
                    "latitude": row[1],
                    "longitude": row[2],
                    "accuracy": row[3]
                }

    return jsonify({
        "wifi_checked_at": wifi.get("_checked_at"),
        "wifi_ssid": wifi.get("ssid"),
        "wifi_bssid": wifi.get("bssid"),
        "wifi_ip": get_wifi_ip(wifi),
        "outbound_ip": get_outbound_ip(),
        "rssi": wifi.get("rssi"),
        "frequency_mhz": wifi.get("frequency_mhz"),
        "last_gps": last_gps
    })


@extras.route("/export.csv")
def export_csv():
    if not DB.exists():
        return jsonify(error="Database not found"), 404

    columns = [
        "id", "timestamp", "ssid", "bssid",
        "rssi", "frequency", "security",
        "latitude", "longitude", "accuracy"
    ]

    def safe_cell(value):
        if isinstance(value, str) and value.lstrip().startswith(
            ("=", "+", "-", "@", "\t", "\r")
        ):
            return "'" + value
        return value

    def generate():
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        writer.writerow(columns)
        yield buffer.getvalue()

        with sqlite3.connect(DB) as db:
            rows = db.execute("""
                SELECT id, timestamp, ssid, bssid,
                       rssi, frequency, security,
                       latitude, longitude, accuracy
                FROM observations
                ORDER BY id
            """)

            for row in rows:
                buffer.seek(0)
                buffer.truncate(0)

                writer.writerow([
                    safe_cell(value) for value in row
                ])

                yield buffer.getvalue()

    return Response(
        stream_with_context(generate()),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                "attachment; filename=sentinel_observations.csv",
            "Cache-Control": "no-store"
        }
    )
