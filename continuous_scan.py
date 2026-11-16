import subprocess
import sys
import time
import sqlite3

print("SENTINEL WARDRIVER")
print("Continuous GPS + Wi-Fi scanning")
print("Press Ctrl+C to stop")

try:
    while True:
        print("\nStarting scan...")

        subprocess.run(
            [sys.executable, "gps_scan.py"],
            timeout=90
        )

        with sqlite3.connect(
            "data/gps_wardriver.db"
        ) as db:
            total = db.execute(
                "SELECT COUNT(*) FROM observations"
            ).fetchone()[0]

            unique = db.execute(
                "SELECT COUNT(DISTINCT bssid) FROM observations"
            ).fetchone()[0]

        print(f"Total observations: {total}")
        print(f"Unique BSSIDs: {unique}")
        print("Next scan in 30 seconds...")

        time.sleep(30)

except KeyboardInterrupt:
    print("\nWardriver stopped safely.")

except Exception as error:
    print("Error:", error)
