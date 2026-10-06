#!/usr/bin/env python3
"""Lightweight HTTP server for Retail ETL Pipeline Executive Dashboard."""

import http.server
import json
import socketserver
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
PORT = 8000


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler serving the HTML dashboard, JSON APIs, and Word document downloads."""

    def _handle_request(self, send_body=True):
        if self.path == "/" or self.path == "/index.html":
            html_file = BASE_DIR / "dashboard" / "index.html"
            content = html_file.read_bytes()
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Content-length", str(len(content)))
            self.end_headers()
            if send_body:
                self.wfile.write(content)
            return

        elif self.path in ("/download/docx", "/Retail_ETL_Pipeline_Technical_Assessment.docx"):
            docx_path = BASE_DIR / "Retail_ETL_Pipeline_Technical_Assessment.docx"
            if not docx_path.exists():
                docx_path = BASE_DIR.parent / "Retail_ETL_Pipeline_Technical_Assessment.docx"

            if docx_path.exists():
                content = docx_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-type", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                self.send_header("Content-Disposition", 'attachment; filename="Retail_ETL_Pipeline_Technical_Assessment.docx"')
                self.send_header("Content-length", str(len(content)))
                self.end_headers()
                if send_body:
                    self.wfile.write(content)
                return
            else:
                self.send_error(404, "Word document not found")
                return

        elif self.path.startswith("/api/reconciliation"):
            recon_csv = BASE_DIR / "output" / "reconciliation_errors.csv"
            if recon_csv.exists():
                df = pd.read_csv(recon_csv)
                data = df.to_dict(orient="records")
            else:
                data = []

            payload = json.dumps(data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-length", str(len(payload)))
            self.end_headers()
            if send_body:
                self.wfile.write(payload)
            return

        elif self.path.startswith("/api/duplicates"):
            dup_csv = BASE_DIR / "output" / "duplicate_records.csv"
            if dup_csv.exists():
                df = pd.read_csv(dup_csv)
                data = df.to_dict(orient="records")
            else:
                data = []

            payload = json.dumps(data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-length", str(len(payload)))
            self.end_headers()
            if send_body:
                self.wfile.write(payload)
            return

        # Fallback to standard static file serving
        if send_body:
            return super().do_GET()
        else:
            return super().do_HEAD()

    def do_GET(self):
        return self._handle_request(send_body=True)

    def do_HEAD(self):
        return self._handle_request(send_body=False)


def main():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"Retail ETL Dashboard running at: http://localhost:{PORT}/")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")


if __name__ == "__main__":
    main()
