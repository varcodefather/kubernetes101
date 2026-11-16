import html
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

reserve_mib = int(os.environ.get("RESERVE_MIB", "128"))
assert 0 <= reserve_mib <= 128, "Lab memory allocation capped at 128 MiB"
print(f"Reserving {reserve_mib} MiB for the local demo", flush=True)
reserved = bytearray(reserve_mib * 1024 * 1024)
for offset in range(0, len(reserved), 4096):
    reserved[offset] = 1
print("Allocation complete; starting web server", flush=True)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthz":
            body, content_type = "ok", "text/plain"
        elif self.path == "/":
            pod = html.escape(os.environ.get("HOSTNAME", "local"))
            body = f"""<!doctype html><meta charset=utf-8><title>Resource limits 101</title>
<style>body{{background:#101923;color:#edf4f8;font:29px system-ui;max-width:1050px;margin:70px auto}}h1{{color:#31ceb2}}</style>
<h1>App running with its allocated memory</h1><p>Held allocation: {reserve_mib} MiB</p><p>Pod: {pod}</p>"""
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
