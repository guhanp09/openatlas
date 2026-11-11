"""Local-only browser prototype; queries are not logged or persisted."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .search import encode, response

STATIC = Path(__file__).parent / "static"


def handler_for(index, weight, examples=None):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, status, content, kind="application/json; charset=utf-8"):
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy", "default-src 'self'; object-src 'none'; frame-ancestors 'none'"
            )
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self):
            parts = urlsplit(self.path)
            if parts.path == "/api/search":
                params = parse_qs(parts.query, keep_blank_values=True)
                try:
                    language = params.get("language", ["english"])[0]
                    query = params.get("q", [""])[0]
                    mode = params.get("mode", ["compact"])[0]
                    ranked = index.rank(query, language, weight)
                    self.send(200, encode(response(ranked, language, mode)))
                except ValueError as error:
                    self.send(400, encode({"error": str(error)}))
                return
            if parts.path == "/api/examples":
                self.send(200, encode(examples or {}))
                return
            allowed = {
                "/": ("index.html", "text/html; charset=utf-8"),
                "/app.css": ("app.css", "text/css; charset=utf-8"),
                "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            }
            if parts.path not in allowed:
                self.send(404, encode({"error": "Not found"}))
                return
            name, kind = allowed[parts.path]
            self.send(200, (STATIC / name).read_bytes(), kind)

    return Handler


def serve(root, port=8765):
    import joblib

    root = Path(root)
    artifact = root / "models" / "search.joblib"
    if not artifact.exists():
        raise ValueError("Run python -m openatlas evaluate first to build your local search index.")
    # Only load an artifact generated locally from the trusted evaluation command.
    model = joblib.load(artifact)
    examples = json.loads((root / "models" / "examples.json").read_text())
    server = ThreadingHTTPServer(("127.0.0.1", port), handler_for(model["index"], model["weight"], examples))
    print(f"OpenAtlas: http://127.0.0.1:{port} — Ctrl-C to stop", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
