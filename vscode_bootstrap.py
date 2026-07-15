"""Official Microsoft VS Code web server bootstrap for vscolab.

Downloads ``server-linux-x64-web`` (Microsoft Marketplace, Copilot Chat capable)
and starts ``bin/code-server`` on a local port for Colab's proxy.
"""

from __future__ import annotations

import json
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

LATEST_API = (
    "https://update.code.visualstudio.com/api/latest/server-linux-x64-web/stable"
)
SERVER_URL_TMPL = (
    "https://update.code.visualstudio.com/commit:{commit}/server-linux-x64-web/stable"
)


def resolve_commit(commit: str = "") -> tuple[str, str]:
    """Return ``(commit, version_name)``. Empty commit resolves latest stable."""
    if commit:
        return commit, commit[:12]
    with urllib.request.urlopen(LATEST_API, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    return str(data["version"]), str(data.get("name") or data["version"][:12])


def _download(url: str, dest: Path, label: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"Using cached {label} at {dest}", flush=True)
        return
    print(f"Downloading {label}...", flush=True)
    subprocess.run(
        ["wget", "--show-progress", "-O", str(dest), url],
        check=True,
    )


def prepare_vscode(
    cache_dir: Path,
    user_data_dir: Path,
    commit: str = "",
) -> dict:
    """Download and extract the official VS Code web server. Returns paths."""
    cache_dir = Path(cache_dir).resolve()
    user_data_dir = Path(user_data_dir).resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    user_data_dir.mkdir(parents=True, exist_ok=True)

    resolved, version_name = resolve_commit(commit)
    print(f"VS Code {version_name} (commit {resolved[:12]})", flush=True)

    server_root = cache_dir / f"vscode-web-{resolved}"
    server_bin = server_root / "bin" / "code-server"
    tarball = cache_dir / f"vscode-server-linux-x64-web-{resolved}.tar.gz"

    if not server_bin.exists():
        _download(
            SERVER_URL_TMPL.format(commit=resolved),
            tarball,
            "VS Code web server",
        )
        if server_root.exists():
            subprocess.run(["rm", "-rf", str(server_root)], check=False)
        server_root.mkdir(parents=True, exist_ok=True)
        print("Extracting VS Code web server...", flush=True)
        subprocess.run(
            [
                "tar",
                "-xzf",
                str(tarball),
                "-C",
                str(server_root),
                "--strip-components",
                "1",
            ],
            check=True,
        )

    if not server_bin.exists():
        raise RuntimeError(f"code-server not found at {server_bin}")

    extensions_dir = user_data_dir / "extensions"
    extensions_dir.mkdir(parents=True, exist_ok=True)

    return {
        "commit": resolved,
        "version": version_name,
        "server_bin": server_bin,
        "server_root": server_root,
        "user_data_dir": user_data_dir,
        "extensions_dir": extensions_dir,
    }


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def start_vscode_web(
    prepared: dict,
    folder: str | Path,
    port: int = 3000,
    host: str = "0.0.0.0",
) -> None:
    """Start official ``code-server`` (web) in the background."""
    folder = str(Path(folder).resolve())
    server_bin = prepared["server_bin"]
    user_data_dir = prepared["user_data_dir"]
    extensions_dir = prepared["extensions_dir"]
    log_path = Path(user_data_dir) / "vscode-server.log"

    # Do not pass openvscode-only flags like --default-folder; they make the
    # official binary exit immediately (browser then sees WebSocket 1006).
    cmd = [
        str(server_bin),
        "--host",
        host,
        "--port",
        str(port),
        "--without-connection-token",
        "--accept-server-license-terms",
        "--user-data-dir",
        str(user_data_dir),
        "--extensions-dir",
        str(extensions_dir),
        folder,
    ]

    print(f"Starting VS Code (folder: {folder})...", flush=True)
    print(f"Server log: {log_path}", flush=True)
    log_file = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )

    deadline = time.time() + 30
    while time.time() < deadline:
        if proc.poll() is not None:
            log_file.flush()
            tail = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
            raise RuntimeError(
                f"VS Code exited early (code {proc.returncode}). Log tail:\n{tail}"
            )
        if _port_open("127.0.0.1", port):
            break
        time.sleep(0.5)
    else:
        log_file.flush()
        tail = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
        raise RuntimeError(
            f"VS Code did not open port {port} within 30s. Log tail:\n{tail}"
        )

    print(f"VS Code running on port {port} — {folder}", flush=True)


def vscode_proxy_url(base_proxy_url: str, folder: str | Path) -> str:
    """Append ``?folder=`` so the workbench opens the workspace."""
    folder = str(Path(folder).resolve())
    base = base_proxy_url.rstrip("/")
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}folder={folder}"
