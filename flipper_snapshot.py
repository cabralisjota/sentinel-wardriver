import json
import re
from pathlib import Path
from datetime import datetime, timezone

log = Path("flipper_cli.log")

if not log.exists():
    print("Flipper CLI log not found.")
    raise SystemExit(1)

content = log.read_text(errors="replace")

verified = "Flipper USB device verified." in content
responded = "Welcome to Flipper Zero Command Line Interface!" in content
successful = bool(re.search(r"Exit code:\s*0\b", content))

match = re.search(
    r"--- Received (\d+) bytes ---",
    content
)

if not (verified and responded and successful and match):
    print("No complete successful Flipper session found.")
    raise SystemExit(1)

status = {
    "device": "Flipper Zero",
    "usb_verified": True,
    "cli_responded": True,
    "last_verified": datetime.fromtimestamp(
        log.stat().st_mtime,
        timezone.utc
    ).isoformat(),
    "bytes_received": int(match.group(1)),
    "command": "info device"
}

path = Path("data/flipper_status.json")
path.parent.mkdir(exist_ok=True)

path.write_text(json.dumps(status, indent=2))

print("Flipper Zero status snapshot saved!")
print(json.dumps(status, indent=2))
