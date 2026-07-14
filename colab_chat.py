"""Colab Gemini chat bridge for openvscode-server (no GitHub / Copilot auth).

Starts a local OpenAI-compatible proxy over ``google.colab.ai`` and seeds
Continue with a config that points at it. openvscode-server has no GitHub
Copilot Chat; Continue provides the sidebar chat UI instead.
"""

from __future__ import annotations

import json
import threading
import time
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

GEMINI_PROXY_PORT = 8787
# Platform-specific VSIX — marketplace ID install often fails on openvscode-server.
CONTINUE_VSIX_VERSION = "1.3.40"
CONTINUE_EXTENSION = {
    "vsix": f"Continue.continue-{CONTINUE_VSIX_VERSION}@linux-x64.vsix",
    "url": (
        "https://open-vsx.org/api/Continue/continue/linux-x64/"
        f"{CONTINUE_VSIX_VERSION}/file/"
        f"Continue.continue-{CONTINUE_VSIX_VERSION}@linux-x64.vsix"
    ),
}
DEFAULT_MODEL = "google/gemini-3.5-flash"


def _messages_to_prompt(messages: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for msg in messages:
        role = msg.get("role") or "user"
        content = msg.get("content")
        if isinstance(content, list):
            texts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    texts.append(str(block.get("text") or ""))
                elif isinstance(block, str):
                    texts.append(block)
            content = "\n".join(texts)
        elif content is None:
            content = ""
        else:
            content = str(content)
        if role == "system":
            parts.append(f"System: {content}")
        elif role == "assistant":
            parts.append(f"Assistant: {content}")
        else:
            parts.append(f"User: {content}")
    parts.append("Assistant:")
    return "\n\n".join(parts)


def _list_models() -> list[str]:
    try:
        from google.colab import ai

        models = list(ai.list_models())
        if models:
            return [str(m) for m in models]
    except Exception as exc:
        print(f"colab_chat: list_models failed ({exc}); using default", flush=True)
    return [DEFAULT_MODEL]


def _generate(prompt: str, model: str, stream: bool) -> str | Iterator[str]:
    from google.colab import ai

    kwargs: dict[str, Any] = {"stream": stream}
    if model:
        kwargs["model_name"] = model
    return ai.generate_text(prompt, **kwargs)


def _sse_chunk(model: str, content: str | None, *, finish: str | None = None) -> bytes:
    delta: dict[str, Any] = {}
    if content is not None:
        delta["content"] = content
    choice: dict[str, Any] = {"index": 0, "delta": delta}
    if finish is not None:
        choice["finish_reason"] = finish
    payload = {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [choice],
    }
    return f"data: {json.dumps(payload)}\n\n".encode()


class _GeminiHandler(BaseHTTPRequestHandler):
    server_version = "vscolab-colab-gemini/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"colab_chat proxy: {fmt % args}", flush=True)

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
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path in ("/v1/models", "/models"):
            models = _list_models()
            data = [
                {
                    "id": mid,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "google-colab",
                }
                for mid in models
            ]
            self._json(200, {"object": "list", "data": data})
            return
        if path in ("/health", "/"):
            self._json(200, {"ok": True, "service": "colab-gemini"})
            return
        self._json(404, {"error": {"message": f"Not found: {path}", "type": "invalid_request_error"}})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path not in ("/v1/chat/completions", "/chat/completions"):
            self._json(404, {"error": {"message": f"Not found: {path}", "type": "invalid_request_error"}})
            return

        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode() or "{}")
        except json.JSONDecodeError:
            self._json(400, {"error": {"message": "Invalid JSON", "type": "invalid_request_error"}})
            return

        messages = body.get("messages") or []
        model = body.get("model") or DEFAULT_MODEL
        stream = bool(body.get("stream"))
        prompt = _messages_to_prompt(messages)

        try:
            if stream:
                self._stream(model, prompt)
            else:
                text = _generate(prompt, model, stream=False)
                self._json(
                    200,
                    {
                        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "message": {"role": "assistant", "content": str(text)},
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    },
                )
        except Exception as exc:
            traceback.print_exc()
            self._json(
                500,
                {
                    "error": {
                        "message": str(exc),
                        "type": "server_error",
                    }
                },
            )

    def _stream(self, model: str, prompt: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        chunks = _generate(prompt, model, stream=True)
        for piece in chunks:
            if piece is None:
                continue
            self.wfile.write(_sse_chunk(model, str(piece)))
            self.wfile.flush()
        self.wfile.write(_sse_chunk(model, None, finish="stop"))
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


_proxy_lock = threading.Lock()
_proxy_started = False


def start_gemini_proxy(port: int = GEMINI_PROXY_PORT) -> None:
    """Start the OpenAI-compatible Colab Gemini proxy in a daemon thread."""
    global _proxy_started
    with _proxy_lock:
        if _proxy_started:
            print(f"Colab Gemini proxy already running on :{port}", flush=True)
            return

        server = ThreadingHTTPServer(("127.0.0.1", port), _GeminiHandler)

        def _run() -> None:
            print(f"Colab Gemini proxy listening on http://127.0.0.1:{port}/v1", flush=True)
            server.serve_forever()

        thread = threading.Thread(target=_run, name="colab-gemini-proxy", daemon=True)
        thread.start()
        _proxy_started = True


def write_continue_config(port: int = GEMINI_PROXY_PORT, model: str | None = None) -> Path:
    """Write ~/.continue/config.yaml pointing at the local Gemini proxy."""
    models = _list_models()
    chosen = model or (models[0] if models else DEFAULT_MODEL)
    config = f"""name: vscolab Colab Gemini
version: 0.0.1
schema: v1

models:
  - name: Colab Gemini
    provider: openai
    model: {chosen}
    apiBase: http://127.0.0.1:{port}/v1
    apiKey: colab
    roles:
      - chat
      - edit
      - apply
"""
    # Extra models (same proxy) so the picker can switch when Colab exposes several.
    for mid in models:
        if mid == chosen:
            continue
        safe = mid.replace('"', "")
        config += f"""  - name: {safe}
    provider: openai
    model: {safe}
    apiBase: http://127.0.0.1:{port}/v1
    apiKey: colab
    roles:
      - chat
      - edit
"""

    continue_dir = Path.home() / ".continue"
    continue_dir.mkdir(parents=True, exist_ok=True)
    path = continue_dir / "config.yaml"
    path.write_text(config, encoding="utf-8")
    print(f"Wrote Continue config → {path} (model={chosen})", flush=True)
    return path


def setup_colab_chat(port: int = GEMINI_PROXY_PORT) -> None:
    """Start proxy + seed Continue. Call after extensions are installed."""
    try:
        start_gemini_proxy(port)
        write_continue_config(port)
        print(
            "Chat ready: open the Continue sidebar in VS Code "
            "(no GitHub sign-in; uses Colab Gemini).",
            flush=True,
        )
    except Exception as exc:
        traceback.print_exc()
        print(f"colab_chat setup failed: {exc}", flush=True)
