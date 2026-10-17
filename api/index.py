import json
import os
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        assets_url = os.environ.get("ASSETS_URL", "")
        assets_2_url = os.environ.get("ASSETS_2_URL", "")
        response_data = {
            "status": "ok",
            "service": "app",
            "bound_services": {
                "assets": assets_url,
                "assets_2": assets_2_url,
            },
        }
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode("utf-8"))
