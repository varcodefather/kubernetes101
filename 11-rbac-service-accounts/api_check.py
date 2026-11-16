import html
import json
import os
from pathlib import Path
import ssl
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

directory = Path("/var/run/secrets/kubernetes.io/serviceaccount")
namespace = os.environ["POD_NAMESPACE"]
host = os.environ["KUBERNETES_SERVICE_HOST"]
port = os.environ.get("KUBERNETES_SERVICE_PORT_HTTPS", "443")
authority = f"[{host}]" if ":" in host else host
base = f"https://{authority}:{port}"
context = ssl.create_default_context(cafile=str(directory / "ca.crt"))

def inspect_access():
    targets = [
        ("Named ConfigMap", f"/api/v1/namespaces/{namespace}/configmaps/lesson-config"),
        ("Other ConfigMap", f"/api/v1/namespaces/{namespace}/configmaps/unrelated-config"),
        ("List ConfigMaps", f"/api/v1/namespaces/{namespace}/configmaps"),
        ("Dummy Secret", f"/api/v1/namespaces/{namespace}/secrets/demo-secret"),
        ("Other namespace", "/api/v1/namespaces/rbac-other/configmaps/lesson-config")]
    results = []
    for name, path in targets:
        # Read projected token for each request so rotation is not cached.
        request = urllib.request.Request(base + path, headers={"Authorization": "Bearer " + (directory / "token").read_text().strip()})
        try:
            with urllib.request.urlopen(request, context=context, timeout=3) as response:
                data = json.load(response)
                message = data.get("data", {}).get("message", "") if name == "Named ConfigMap" else ""
                results.append(dict(target=name, status=response.status, message=message))
        except urllib.error.HTTPError as error:
            # No token, secret contents or raw response data in diagnostic UI/logs.
            results.append(dict(target=name, status=error.code, message="Forbidden" if error.code == 403 else "API request failed"))
        except OSError as error:
            results.append(dict(target=name, status=0, message=type(error).__name__))
    return results

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthz":
            body, kind = b"ok", "text/plain"
        elif self.path in ["/", "/api"]:
            results = inspect_access()
            if self.path == "/api":
                body, kind = json.dumps(results).encode(), "application/json"
            else:
                rows = "".join(f"<tr><td>{html.escape(r['target'])}</td><td>{r['status']}</td><td>{html.escape(r['message'])}</td></tr>" for r in results)
                body = f"""<!doctype html><meta charset=utf-8><title>RBAC 101</title>
<style>body{{background:#101923;color:#edf4f8;font:26px system-ui;max-width:1120px;margin:60px auto}}h1{{color:#31ceb2}}td,th{{padding:16px;text-align:left;border-bottom:1px solid #314352}}</style>
<h1>Requests made by our app's ServiceAccount</h1><p>Namespace: {html.escape(namespace)} · Account: config-reader</p>
<table><tr><th>Request</th><th>API status</th><th>Result</th></tr>{rows}</table>
<p>Reload to check current permissions. Tokens remain inside the Pod.</p>""".encode()
                kind = "text/html; charset=utf-8"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
