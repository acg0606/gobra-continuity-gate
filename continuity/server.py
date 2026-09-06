from __future__ import annotations

import json
import subprocess
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

def make_handler(*, database: Path, web_root: Path, case_id: str):
    from app import run_fresh_command

    class ContinuityHandler(BaseHTTPRequestHandler):
        server_version = "GoBRAContinuity/0.1"

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/api/status":
                payload = run_fresh_command(database, "status")
                self._json(payload)
                return
            if path in {"/", "/index.html"}:
                self._file(web_root / "index.html", "text/html; charset=utf-8")
                return
            self._json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            body = self._request_json()
            try:
                if path == "/api/seed":
                    payload = run_fresh_command(database, "seed")
                elif path == "/api/evaluate":
                    action = str(body.get("action", "")).strip()
                    if not action:
                        self._json({"error": "action_required"}, status=HTTPStatus.BAD_REQUEST)
                        return
                    payload = run_fresh_command(database, "evaluate", action)
                elif path == "/api/evidence":
                    key = str(body.get("key", "")).strip()
                    value = str(body.get("value", "")).strip()
                    if not key or not value:
                        self._json({"error": "key_and_value_required"}, status=HTTPStatus.BAD_REQUEST)
                        return
                    payload = run_fresh_command(database, "remember-evidence", key, value)
                elif path == "/api/deletion-test":
                    payload = run_fresh_command(database, "deletion-test")
                else:
                    self._json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)
                    return
            except (subprocess.SubprocessError, json.JSONDecodeError):
                self._json({"verdict": "MEMORY_REQUIRED", "error": "memory_worker_failed"}, status=HTTPStatus.SERVICE_UNAVAILABLE)
                return
            self._json(payload)

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _request_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if not length:
                return {}
            try:
                return json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return {}

        def _json(self, payload: Any, *, status: HTTPStatus = HTTPStatus.OK) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def _file(self, path: Path, content_type: str) -> None:
            if not path.is_file():
                self._json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)
                return
            data = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return ContinuityHandler


def serve(*, database: Path, web_root: Path, case_id: str, host: str, port: int) -> None:
    handler = make_handler(
        database=database,
        web_root=web_root,
        case_id=case_id,
    )
    server = ThreadingHTTPServer((host, port), handler)
    print(f"GoBRA Continuity Gate: http://{host}:{port}")
    server.serve_forever()
