"""Restore local demo through its locked application API."""
import sys
from urllib.request import Request, urlopen
payload = sys.stdin.buffer.read(1025)
request = Request("http://127.0.0.1:8000/restore", data=payload,
                  headers={"Content-Type": "application/json"}, method="POST")
with urlopen(request, timeout=5) as response:
    sys.stdout.buffer.write(response.read() + b"\n")
