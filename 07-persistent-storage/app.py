"""Small file-backed counter for a local Kubernetes storage lesson."""
import html
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

directory = Path(os.environ.get("DATA_DIR", "/data"))
directory.mkdir(parents=True, exist_ok=True)
state = directory / "counter.json"
lock = threading.Lock()
pod = os.environ.get("POD_NAME", os.environ.get("HOSTNAME", "local"))

def read_count():
    return json.loads(state.read_text())["count"] if state.exists() else 0

def save_count(value):
    temporary = directory / "counter.tmp"
    with temporary.open("w") as output:
        json.dump({"count": value}, output)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, state)

class Handler(BaseHTTPRequestHandler):
    def send(self, status, content, content_type="application/json"):
        body = content.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/healthz":
            return self.send(200, "ok", "text/plain")
        if self.path not in ("/", "/api", "/export"):
            return self.send(404, "not found", "text/plain")
        with lock:
            count = read_count()
        if self.path == "/export":
            return self.send(200, json.dumps({"count": count}))
        if self.path == "/api":
            return self.send(200, json.dumps({"count": count, "pod": pod}))
        page = f"""<!doctype html><meta charset=utf-8><title>Kubernetes storage</title>
<style>body{{background:#101923;color:#e7eef4;font:24px system-ui;max-width:1000px;margin:55px auto}}
h1{{color:#31ceb2}}.count{{font-size:100px;font-weight:700;margin:25px 0}}
button,a{{font:24px system-ui;color:#101923;background:#31ceb2;border:0;padding:12px 24px;border-radius:5px}}
code{{font-size:21px}}small{{display:block;color:#a7b6c2;margin:35px 0}}</style>
<h1>Counter with saved data</h1><div class=count>{count}</div>
<form method=post action=/increment><button>Add one</button></form>
<small>Served by <code>{html.escape(pod)}</code></small>
<p>Saved in <code>/data/counter.json</code></p><p><a href=/>Reload</a></p>"""
        self.send(200, page, "text/html; charset=utf-8")

    def do_POST(self):
        if self.path == "/increment":
            with lock:
                save_count(read_count() + 1)
            self.send_response(303)
            self.send_header("Location", "/")
            self.send_header("Content-Length", "0")
            return self.end_headers()
        if self.path != "/restore":
            return self.send(404, "not found", "text/plain")
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 1024:
                raise ValueError("backup must be a small JSON object")
            value = json.loads(self.rfile.read(length))["count"]
            if type(value) is not int or not 0 <= value <= 1_000_000:
                raise ValueError("invalid count")
        except (ValueError, KeyError, TypeError) as error:
            return self.send(400, json.dumps({"error": str(error)}))
        with lock:
            save_count(value)
        self.send(200, json.dumps({"restored_count": value, "pod": pod}))

ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
