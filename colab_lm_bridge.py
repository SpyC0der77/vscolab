"""Colab AI bridge for the vscolab Language Model Chat Provider extension.

Starts a localhost HTTP server that wraps ``google.colab.ai`` so the VS Code
extension (running in openvscode-server) can call Gemini without an API key.
"""

from __future__ import annotations

import json
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Iterator
from urllib.parse import urlparse

BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 8787
DEFAULT_MODEL = "gemini-2.5-flash"

_server: ThreadingHTTPServer | None = None


def _list_models() -> list[str]:
    try:
        from google.colab import ai

        models = list(ai.list_models())
        if models:
            return [str(m) for m in models]
    except Exception as exc:
        print(f"colab_lm_bridge: list_models failed ({exc}); using default", flush=True)
    return [DEFAULT_MODEL]


def _generate(prompt: str, model: str | None, stream: bool) -> str | Iterator[str]:
    from google.colab import ai

    kwargs: dict[str, Any] = {"stream": stream}
    if model:
        kwargs["model"] = model
    return ai.generate_text(prompt, **kwargs)


def _messages_to_prompt(messages: list[dict[str, str]]) -> str:
    parts: list[str] = []
    for msg in messages:
        role = msg.get("role") or "user"
        content = msg.get("content") or ""
        if role == "assistant":
            parts.append(f"Assistant: {content}")
        else:
            parts.append(f"User: {content}")
    parts.append("Assistant:")
    return "\n\n".join(parts)


class _BridgeHandler(BaseHTTPRequestHandler):
    server_version = "vscolab-colab-lm/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"colab_lm_bridge: {fmt % args}", flush=True)

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj: Any) -> None:
        self._send(code, json.dumps(obj).encode(), "application/json")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/health":
            self._json(200, {"status": "ok"})
            return
        if path == "/models":
            self._json(200, {"models": _list_models()})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path != "/generate":
            self._json(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(body.decode() or "{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid json"})
            return

        prompt = payload.get("prompt")
        messages = payload.get("messages")
        if not prompt and messages:
            prompt = _messages_to_prompt(messages)
        if not prompt:
            self._json(400, {"error": "prompt or messages required"})
            return

        model = payload.get("model")
        stream = bool(payload.get("stream"))

        try:
            result = _generate(prompt, model, stream)
        except Exception as exc:
            print(f"colab_lm_bridge: generate failed: {exc}", flush=True)
            traceback.print_exc()
            self._json(500, {"error": str(exc)})
            return

        if not stream:
            self._json(200, {"text": str(result)})
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        try:
            for chunk in result:
                line = json.dumps({"text": str(chunk)}) + "\n"
                data = line.encode()
                self.wfile.write(f"{len(data):x}\r\n".encode())
                self.wfile.write(data)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")
        except Exception as exc:
            print(f"colab_lm_bridge: stream failed: {exc}", flush=True)


def setup_colab_lm(host: str = BRIDGE_HOST, port: int = BRIDGE_PORT) -> str:
    """Start the Colab AI bridge and return its base URL."""
    global _server

    if _server is not None:
        return f"http://{host}:{port}"

    try:
        from google.colab import ai  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "google.colab.ai is only available inside Google Colab."
        ) from exc

    _server = ThreadingHTTPServer((host, port), _BridgeHandler)
    thread = threading.Thread(target=_server.serve_forever, daemon=True)
    thread.start()

    url = f"http://{host}:{port}"
    print(f"Colab AI bridge listening at {url}", flush=True)
    return url
