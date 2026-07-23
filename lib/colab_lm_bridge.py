"""Colab AI bridge for the vscolab Language Model Chat Provider extension.

Starts a localhost HTTP server that wraps ``google.colab.ai`` so the VS Code
extension (running in openvscode-server) can call Gemini without an API key.
"""

from __future__ import annotations

import json
import os
import socket
import threading
import time
import traceback
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 8787
# Outside the VS Code workspace (/content/workspace) so it stays Colab-VM-only.
LOG_PATH = Path("/content/.vscolab/colab_lm_bridge.log")
_LOG_LOCK = threading.Lock()

# Notebook cells re-exec `_server = None` on every run. Keep the live server on a
# stable key so re-runs can shut it down without killing the Colab kernel.
_SERVER_KEY = "_vscolab_lm_http_server"
_AVAILABLE_KEY = "_vscolab_lm_available_models"


def _get_server() -> ThreadingHTTPServer | None:
    return globals().get(_SERVER_KEY)


def _set_server(server: ThreadingHTTPServer | None) -> None:
    globals()[_SERVER_KEY] = server


def _get_available() -> dict[str, str]:
    """canonical id -> Colab API model name (may include ``google/`` prefix)."""
    return globals().get(_AVAILABLE_KEY) or {}


def _set_available(mapping: dict[str, str]) -> None:
    globals()[_AVAILABLE_KEY] = mapping


def _canonical_id(raw: str) -> str:
    return raw.split("/", 1)[-1].strip()


class _ReuseHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def _bridge_healthy(host: str, port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/health", timeout=1) as resp:
            return resp.status == 200
    except Exception:
        return False


def _request_shutdown(host: str, port: int) -> None:
    """Ask a live bridge (possibly from a prior cell run) to stop itself."""
    try:
        req = urllib.request.Request(
            f"http://{host}:{port}/shutdown",
            method="POST",
            data=b"{}",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=2):
            pass
    except Exception:
        pass


def _stop_server(server: ThreadingHTTPServer | None) -> None:
    if server is None:
        return
    try:
        server.shutdown()
    except Exception:
        pass
    try:
        server.server_close()
    except Exception:
        pass


def _wait_port_free(host: str, port: int, timeout: float = 3.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex((host, port)) != 0:
                return True
        time.sleep(0.1)
    return False


def _list_models() -> list[str]:
    try:
        from google.colab import ai

        discovered = [str(m) for m in ai.list_models()]
    except Exception as exc:
        print(f"colab_lm_bridge: list_models failed ({exc})", flush=True)
        _set_available({})
        return []

    available: dict[str, str] = {}
    models: list[str] = []
    for raw in discovered:
        cid = _canonical_id(raw)
        if not cid or cid in available:
            continue
        available[cid] = raw
        models.append(cid)
    _set_available(available)
    return models


def _resolve_model_name(model: str | None) -> str | None:
    if not model:
        return None
    cid = _canonical_id(model)
    available = _get_available()
    if cid in available:
        return available[cid]
    if model in available.values():
        return model
    # Colab docs often use the google/ prefix.
    if "/" not in model:
        return f"google/{cid}"
    return model


def _call_generate(prompt: str, model_name: str | None, stream: bool) -> str | Iterator[str]:
    from google.colab import ai

    kwargs: dict[str, Any] = {"stream": stream}
    if model_name:
        try:
            return ai.generate_text(prompt, model_name=model_name, **kwargs)
        except TypeError as exc:
            if "model_name" not in str(exc) and "unexpected keyword" not in str(exc):
                raise
            return ai.generate_text(prompt, model=model_name, **kwargs)
    return ai.generate_text(prompt, **kwargs)


def _generate(prompt: str, model: str | None, stream: bool) -> str | Iterator[str]:
    # Refresh availability if we haven't yet (e.g. reused bridge process).
    if not _get_available():
        _list_models()

    resolved = _resolve_model_name(model)
    candidates: list[str | None] = []
    for name in (resolved, model, f"google/{_canonical_id(model)}" if model else None):
        if name and name not in candidates:
            candidates.append(name)
    if not candidates:
        candidates = [None]

    last_exc: Exception | None = None
    for name in candidates:
        try:
            return _call_generate(prompt, name, stream)
        except Exception as exc:
            msg = str(exc).lower()
            last_exc = exc
            if "unavailable" in msg or "not found" in msg or "404" in msg:
                continue
            raise
    assert last_exc is not None
    raise RuntimeError(
        f"Model {model!r} is unavailable on this Colab runtime. "
        f"Pick another model from the picker (served as {_list_models()})."
    ) from last_exc


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


def _chunk_text(chunk: Any) -> str | None:
    """OpenAI-style streams often yield ``None`` for role-only deltas."""
    if chunk is None:
        return None
    if isinstance(chunk, str):
        return chunk
    return str(chunk)


def _log_exchange(request: dict[str, Any], response: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "request": request,
        "response": response,
    }
    line = json.dumps(entry, ensure_ascii=False) + "\n"
    with _LOG_LOCK:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line)


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
            self._json(200, {"status": "ok", "pid": os.getpid()})
            return
        if path == "/models":
            self._json(200, {"models": _list_models()})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/shutdown":
            self._json(200, {"status": "shutting_down"})
            server = self.server

            def _stop() -> None:
                time.sleep(0.05)
                try:
                    server.shutdown()
                except Exception:
                    pass
                try:
                    server.server_close()
                except Exception:
                    pass

            threading.Thread(target=_stop, daemon=True).start()
            return

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
        request_log = {
            "path": "/generate",
            "model": model,
            "stream": stream,
            "prompt": prompt,
            "messages": messages,
            "payload": payload,
        }

        try:
            result = _generate(prompt, model, stream)
        except Exception as exc:
            print(f"colab_lm_bridge: generate failed: {exc}", flush=True)
            traceback.print_exc()
            response = {"error": str(exc)}
            _log_exchange(request_log, response)
            self._json(500, response)
            return

        if not stream:
            text = _chunk_text(result) or ""
            response = {"text": text}
            _log_exchange(request_log, response)
            self._json(200, response)
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        chunks: list[str] = []
        try:
            for raw in result:
                text = _chunk_text(raw)
                if text is None:
                    continue
                chunks.append(text)
                line = json.dumps({"text": text}) + "\n"
                data = line.encode()
                self.wfile.write(f"{len(data):x}\r\n".encode())
                self.wfile.write(data)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")
            _log_exchange(
                request_log,
                {"stream": True, "text": "".join(chunks), "chunks": chunks},
            )
        except Exception as exc:
            print(f"colab_lm_bridge: stream failed: {exc}", flush=True)
            _log_exchange(
                request_log,
                {
                    "stream": True,
                    "error": str(exc),
                    "text": "".join(chunks),
                    "chunks": chunks,
                },
            )


def setup_colab_lm(host: str = BRIDGE_HOST, port: int = BRIDGE_PORT) -> str:
    """Start the Colab AI bridge and return its base URL.

    Restarts the in-process server on notebook re-runs. Never kills the Colab
    kernel (the bridge shares this process).
    """
    url = f"http://{host}:{port}"

    try:
        from google.colab import ai  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "google.colab.ai is only available inside Google Colab."
        ) from exc

    existing = _get_server()
    if existing is not None:
        print("Stopping previous Colab AI bridge...", flush=True)
        _stop_server(existing)
        _set_server(None)
        _wait_port_free(host, port)
    elif _bridge_healthy(host, port):
        # Prior cell left a live bridge but lost the Python reference.
        print("Stopping previous Colab AI bridge via /shutdown...", flush=True)
        _request_shutdown(host, port)
        _wait_port_free(host, port)

    if _bridge_healthy(host, port):
        # Still serving (shutdown raced or foreign process). Reuse — do NOT
        # fuser/kill: that would terminate this Colab kernel.
        models = _list_models()
        print(f"Colab AI bridge already listening at {url} (reusing)", flush=True)
        print(f"Available models: {', '.join(models)}", flush=True)
        print(f"Request/response log: {LOG_PATH}", flush=True)
        return url

    try:
        server = _ReuseHTTPServer((host, port), _BridgeHandler)
    except OSError as exc:
        if getattr(exc, "errno", None) != 98:  # EADDRINUSE
            raise
        if _bridge_healthy(host, port):
            models = _list_models()
            print(f"Colab AI bridge already listening at {url} (reusing)", flush=True)
            print(f"Available models: {', '.join(models)}", flush=True)
            print(f"Request/response log: {LOG_PATH}", flush=True)
            return url
        raise RuntimeError(
            f"Port {port} is busy and the existing Colab AI bridge did not respond. "
            "Restart the Colab runtime, then re-run this cell."
        ) from exc

    models = _list_models()
    _set_server(server)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    print(f"Colab AI bridge listening at {url}", flush=True)
    print(f"Available models: {', '.join(models)}", flush=True)
    print(f"Request/response log: {LOG_PATH}", flush=True)
    return url
