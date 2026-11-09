"""Disposable local probe lab. Failure controls belong in this demo only."""
import html
import json
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

STARTED = time.monotonic()
STARTUP_SECONDS = float(os.environ.get("STARTUP_SECONDS", "20"))
POD = os.environ.get("HOSTNAME", "unknown")
UNREADY = Path("/tmp/unready")
UNHEALTHY = Path("/tmp/unhealthy")


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body, content_type="text/plain; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        started = time.monotonic() - STARTED >= STARTUP_SECONDS
        if self.path in ("/startup", "/live", "/ready"):
            healthy = started
            if self.path in ("/live", "/ready"):
                healthy = healthy and not UNHEALTHY.exists()
            if self.path == "/ready":
                healthy = healthy and not UNREADY.exists()
            self.respond(200 if healthy else 503, "ok\n" if healthy else "not ready\n")
            return
        if self.path == "/identity":
            self.respond(200, json.dumps({"pod": POD}), "application/json")
            return
        if self.path != "/":
            self.respond(404, "not found\n")
            return
        self.respond(200, """<!doctype html><html lang="en"><meta charset="utf-8">
<title>Kubernetes health lab</title>
<style>body{font:24px system-ui;background:#101923;color:#edf4f8;max-width:1080px;margin:36px auto}h1{color:#31ceb2}section{border:1px solid #536879;padding:20px;margin:24px 0}button{font:22px system-ui;padding:14px;margin:10px 10px 10px 0;cursor:pointer}output{display:block;margin-top:20px;color:#ffe577}small{font-size:18px;color:#aebeca}</style>
<h1>Healthy enough to serve traffic?</h1>
<section><small>This response came through the app Service from</small><p id="pod">POD_NAME</p></section>
<section><p>Disposable lab controls — affect whichever Pod handles the request</p>
<button id="unready">Simulate dependency failure</button>
<button id="unhealthy">Simulate liveness failure</button>
<output id="result">Both replicas should be Ready before starting a test.</output></section>
<script>for(const mode of ['unready','unhealthy']){document.getElementById(mode).onclick=async()=>{const r=await fetch('/simulate/'+mode,{method:'POST'});const d=await r.json();document.getElementById('result').textContent=d.pod+' — '+d.state;};}</script></html>""".replace("POD_NAME", html.escape(POD)), "text/html; charset=utf-8")

    def do_POST(self):
        paths = {"/simulate/unready": (UNREADY, "readiness failure requested"),
                 "/simulate/unhealthy": (UNHEALTHY, "liveness failure requested")}
        if self.path not in paths:
            self.respond(404, "not found\n")
            return
        marker, state = paths[self.path]
        marker.touch()
        print(json.dumps({"pod": POD, "event": state}), flush=True)
        self.respond(200, json.dumps({"pod": POD, "state": state}), "application/json")

    def log_message(self, fmt, *args):
        if self.path == "/" or self.command == "POST":
            super().log_message(fmt, *args)


print(json.dumps({"pod": POD, "event": "process started", "startup_seconds": STARTUP_SECONDS}), flush=True)
HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
