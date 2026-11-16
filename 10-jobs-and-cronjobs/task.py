import datetime
import json
import os

raw = os.environ.get("INPUT_VALUES", "12,18,30")
print("Starting local batch:", raw, flush=True)
values = [int(part.strip()) for part in raw.split(",")]
print(json.dumps({"completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  "pod": os.environ.get("HOSTNAME", "local"),
                  "items": len(values), "sum": sum(values)}), flush=True)
