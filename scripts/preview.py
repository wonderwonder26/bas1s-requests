#!/usr/bin/env python3
"""Serve the site at the GitHub Pages project base path."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from common import SITE_DIR, load_data

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".json": "application/json; charset=utf-8",
    ".xml": "application/xml; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
}


def build_handler(site_dir: Path, base_path: str):
    base = base_path.rstrip("/")

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):
            if not getattr(self.server, "quiet", False):
                super().log_message(fmt, *args)

        def do_GET(self):
            self._respond(write_body=True)

        def do_HEAD(self):
            self._respond(write_body=False)

        def _respond(self, write_body):
            parsed = urlparse(self.path)
            raw_path = unquote(parsed.path)
            if raw_path != base and not raw_path.startswith(base + "/"):
                self._send_file(site_dir / "404.html", 404, write_body)
                return
            relative = raw_path[len(base):] or "/"
            if relative.endswith("/index.html"):
                target = site_dir / relative.lstrip("/")
                if self._is_inside(target) and target.is_file():
                    self._send_file(target, 200, write_body)
                    return
            if not relative.endswith("/"):
                as_dir = site_dir / relative.lstrip("/")
                if self._is_inside(as_dir) and as_dir.is_dir() and (as_dir / "index.html").is_file():
                    location = base + relative + "/"
                    if parsed.query:
                        location += "?" + parsed.query
                    self._redirect(location)
                    return
            candidate = site_dir / relative.lstrip("/")
            if relative.endswith("/"):
                candidate = candidate / "index.html"
            if self._is_inside(candidate) and candidate.is_file():
                self._send_file(candidate, 200, write_body)
                return
            self._send_file(site_dir / "404.html", 404, write_body)

        def _is_inside(self, path: Path):
            try:
                path.resolve().relative_to(site_dir.resolve())
            except ValueError:
                return False
            return True

        def _redirect(self, location):
            body = b""
            self.send_response(302)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _send_file(self, path: Path, status, write_body):
            if not path.is_file():
                message = b"Not found"
                self.send_response(404)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(message)))
                self.end_headers()
                if write_body:
                    self.wfile.write(message)
                return
            data = path.read_bytes()
            content_type = CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if write_body:
                self.wfile.write(data)

    return Handler


def make_server(host="127.0.0.1", port=8765, quiet=False):
    data = load_data()
    handler = build_handler(SITE_DIR, data["site"]["basePath"])
    server = ThreadingHTTPServer((host, port), handler)
    server.quiet = quiet
    return server


def main():
    parser = argparse.ArgumentParser(description="Preview the site at /bas1s-requests/")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = make_server(args.host, args.port, quiet=False)
    base = load_data()["site"]["basePath"]
    print(f"Serving {SITE_DIR} at http://{args.host}:{args.port}{base}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
