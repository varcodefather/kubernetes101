import html
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthz":
            body, content_type = "ok", "text/plain"
        elif self.path == "/":
            message = html.escape(os.environ.get("MESSAGE", "Hello from Helm"))
            pod = html.escape(os.environ.get("HOSTNAME", "local"))
            body = f"""<!doctype html><meta charset=utf-8><title>Helm 101</title>
<style>body{{background:#101923;color:#edf4f8;font:29px system-ui;max-width:1050px;margin:70px auto}}h1{{color:#31ceb2}}small{{color:#aebfc9}}</style>
<h1>{message}</h1><p>Chart values → Deployment → running app</p><small>Pod: {pod}</small>"""
            content_type = "text/html; charset=utf-8"
        else:
            self.send_error(404)
            return
        data = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
