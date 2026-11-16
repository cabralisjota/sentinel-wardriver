import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

print("Reading Android Wi-Fi connection...")

try:
    result = subprocess.run(
        ["termux-wifi-connectioninfo"],
        capture_output=True,
        text=True,
        timeout=15,
        check=True
    )

    info = json.loads(result.stdout)

    if not isinstance(info, dict):
        raise ValueError("Unexpected response")

    path = Path("data/wifi_connection_cache.json")
    path.parent.mkdir(exist_ok=True)

    snapshot = {
        "checked_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "info": info
    }

    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(snapshot, indent=2))
    temp.replace(path)

    print("Wi-Fi connection snapshot saved!")
    print("File:", path)

except Exception as error:
    print("Snapshot failed:", error)
