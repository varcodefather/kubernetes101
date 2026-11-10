"""Small frontend/backend for an isolated Kubernetes networking lesson."""
import html
import json
import os
import socket
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROLE = os.environ.get('ROLE', 'backend')
POD = os.environ.get('HOSTNAME', 'unknown')
BACKEND_URL = os.environ.get('BACKEND_URL', 'http://backend')
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class Handler(BaseHTTPRequestHandler):
    def send(self, status, body, content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-Type', content_type + '; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        if self.path == '/healthz':
            self.send(200, json.dumps({'ready': True, 'role': ROLE}))
            return
        if self.path not in ('/', '/api'):
            self.send(404, json.dumps({'error': 'not found'}))
            return
        if ROLE == 'backend':
            self.send(200, json.dumps({'pod': POD, 'message': 'Hello through the backend Service'}))
            return
        result = {'frontend': POD, 'target': BACKEND_URL}
        try:
            with HTTP.open(BACKEND_URL, timeout=2) as response:
                result['backend'] = json.load(response)
            result['ok'] = True
            status = 200
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            reason = getattr(error, 'reason', error)
            detail = ('Name lookup failed: ' + str(reason)) if isinstance(reason, socket.gaierror) else str(error)
            result.update(ok=False, error=detail, error_type=type(reason).__name__)
            status = 502
        if self.path == '/api':
            self.send(status, json.dumps(result))
            return
        title = 'Backend reached' if result['ok'] else 'Backend request failed'
        color = '#31ceb2' if result['ok'] else '#ffbd69'
        details = ('Backend Pod: ' + result['backend']['pod'] + '\n' + result['backend']['message']) if result['ok'] else result['error']
        body = """<!doctype html><html lang="en"><meta charset="utf-8">
<title>Kubernetes networking lab</title>
<style>body{font:25px system-ui;max-width:1100px;margin:48px auto;background:#101923;color:#edf4f8}h1{color:COLOR}section{border:1px solid #536879;padding:24px;margin:25px 0}pre{white-space:pre-wrap;font:22px monospace}small{font-size:19px;color:#aebeca}a{color:#31ceb2}</style>
<h1>TITLE</h1><p>Browser → frontend → backend Service → backend Pod</p>
<section><small>Frontend responding from</small><pre>FRONTEND</pre></section>
<section><small>Frontend requested</small><pre>TARGET</pre></section>
<section><small>Backend result</small><pre>DETAILS</pre></section>
<p><a href="/">Reload request</a></p></html>"""
        for key, value in [('COLOR', color), ('TITLE', title), ('FRONTEND', POD), ('TARGET', BACKEND_URL), ('DETAILS', details)]:
            body = body.replace(key, html.escape(value))
        self.send(status, body, 'text/html')


print(json.dumps({'role': ROLE, 'pod': POD, 'listen': 8000}), flush=True)
ThreadingHTTPServer(('0.0.0.0', 8000), Handler).serve_forever()
