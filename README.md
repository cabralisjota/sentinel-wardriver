# Sentinel Wardriver

Android-based Wi-Fi wardriving and wireless
network visualization platform.

Built with Python, Flask, SQLite, Termux,
and experimental Flipper Zero integration.

## Features

- Wi-Fi access point discovery
- SSID and BSSID collection
- Signal strength monitoring
- GPS location tracking
- SQLite observation storage
- Interactive Leaflet map
- Wi-Fi observation history
- CSV data export
- Flipper Zero USB communication
- Mobile-friendly dashboard

## Technology

- Python
- Flask
- SQLite
- Android Termux
- Termux:API
- Leaflet.js
- Flipper Zero / ESP32 Marauder

## Installation

Install Termux and Termux:API.

In Termux:

    pkg install python termux-api
    pip install flask

Grant the required Android location
and Wi-Fi permissions.

## Running Sentinel

Start the dashboard:

    python wardriver_map.py

Open:

    http://127.0.0.1:5001

In another Termux session, start scanning:

    python continuous_scan.py

## Flipper Zero Integration

USB communication with the Flipper Zero
CLI has been demonstrated.

Marauder scan-log importing is experimental
and not yet fully integrated.

## Privacy and Security

Only scan networks you are authorized
to assess.

GPS databases, collected Wi-Fi observations,
logs, and local configuration data should
not be committed to public repositories.

## Status

Version: 0.1.0-beta

Development is ongoing.
