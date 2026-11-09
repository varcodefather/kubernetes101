import hmac
import html
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

GREETING = os.environ["GREETING"]
API_TOKEN = os.environ["API_TOKEN"]

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/private":
            authorized = hmac.compare_digest(
                self.headers.get("Authorization", ""), "Bearer " + API_TOKEN
            )
            self.send_response(200 if authorized else 401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": authorized}).encode())
            return
        if self.path != "/":
            self.send_error(404)
            return
        banner = Path("/config/banner.txt").read_text().strip()
        page = """<!doctype html><html lang="en"><meta charset="utf-8">
<title>Kubernetes configuration lab</title>
<style>body{font:24px system-ui;background:#101923;color:#edf4f8;max-width:1100px;margin:24px auto}h1{color:#31ceb2}section{border:1px solid #536879;padding:16px 22px;margin:14px 0}input,button{font:22px system-ui;padding:12px}button{cursor:pointer}output{display:block;margin-top:20px;color:#ffe577}small{font-size:18px;color:#aebeca}</style>
<h1>Same image. Different configuration.</h1>
<section><small>Environment variable — read when this process started</small><p id="greeting">GREETING_VALUE</p></section>
<section><small>Mounted ConfigMap file — read on each page request</small><p id="banner">BANNER_VALUE</p></section>
<section><label for="token">Dummy API key</label><br><input id="token" type="password" autocomplete="off"><button id="check">Test API</button><output id="result">Enter the example key, then test.</output></section>
<script>document.getElementById('check').onclick=async()=>{const response=await fetch('/private',{headers:{Authorization:'Bearer '+document.getElementById('token').value}});document.getElementById('result').textContent=response.status===200?'200 OK — key accepted':'401 Unauthorized — key rejected';};</script>
</html>"""
        page = page.replace("GREETING_VALUE", html.escape(GREETING))
        page = page.replace("BANNER_VALUE", html.escape(banner))
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(page.encode())

HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
