"""Export this demo app's current count; not a database backup utility."""
import sys
from urllib.request import urlopen
with urlopen("http://127.0.0.1:8000/export", timeout=5) as response:
    sys.stdout.buffer.write(response.read() + b"\n")
