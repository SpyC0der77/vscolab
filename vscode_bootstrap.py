"""Official Microsoft VS Code web server bootstrap for vscolab.

Downloads ``server-linux-x64-web`` (Microsoft Marketplace, Copilot Chat capable)
and starts ``bin/code-server`` on a local port for Colab's proxy.
"""

from __future__ import annotations

import json
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
            # Incomplete extract from a prior run
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

    print(f"Starting VS Code (folder: {folder})...", flush=True)
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
    ]
    # Prefer opening the workspace directly when the flag exists.
    cmd.extend(["--default-folder", folder])

    subprocess.Popen(cmd)
    time.sleep(5)
    print(f"VS Code running on port {port} — {folder}", flush=True)


def vscode_proxy_url(base_proxy_url: str, folder: str | Path) -> str:
    """Append ``?folder=`` so the workbench opens the workspace if needed."""
    folder = str(Path(folder).resolve())
    base = base_proxy_url.rstrip("/")
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}folder={folder}"
