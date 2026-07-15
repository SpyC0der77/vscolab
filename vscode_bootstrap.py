"""Official Microsoft VS Code bootstrap via Remote Tunnels (``code tunnel``).

Colab's ``proxyPort`` cannot reliably upgrade WebSockets for Microsoft's web
server (browser error 1006). The supported path is the VS Code CLI tunnel,
which opens ``https://vscode.dev/tunnel/...`` (or desktop Remote Tunnels).
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

CLI_DOWNLOAD = (
    "https://code.visualstudio.com/sha/download?build=stable&os=cli-alpine-x64"
)

# Colab has no desktop keyring; force file-backed credential storage.
os.environ.setdefault("VSCODE_CLI_USE_FILE_KEYCHAIN", "1")


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


def _is_valid_vsix(path: Path) -> bool:
    with path.open("rb") as f:
        return f.read(2) == b"PK"


def _ensure_vsix(vsix_path: Path, url: str, label: str) -> None:
    if vsix_path.exists() and _is_valid_vsix(vsix_path):
        return
    if vsix_path.exists():
        print(f"Removing invalid VSIX at {vsix_path}", flush=True)
        vsix_path.unlink()
    _download(url, vsix_path, label)
    if not _is_valid_vsix(vsix_path):
        raise RuntimeError(
            f"Downloaded file at {vsix_path} is not a valid VSIX (expected zip archive)."
        )


def prepare_vscode(
    cache_dir: Path,
    user_data_dir: Path,
    commit: str = "",
) -> dict:
    """Download the VS Code CLI. ``commit`` is unused (CLI tracks stable)."""
    del commit  # kept for call-site compatibility with older notebooks
    cache_dir = Path(cache_dir).resolve()
    user_data_dir = Path(user_data_dir).resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    user_data_dir.mkdir(parents=True, exist_ok=True)

    cli_data_dir = user_data_dir / "cli"
    cli_data_dir.mkdir(parents=True, exist_ok=True)

    code_bin = cache_dir / "code"
    if not code_bin.exists():
        tarball = cache_dir / "vscode_cli_alpine_x64_cli.tar.gz"
        _download(CLI_DOWNLOAD, tarball, "VS Code CLI")
        print("Extracting VS Code CLI...", flush=True)
        subprocess.run(
            ["tar", "-xzf", str(tarball), "-C", str(cache_dir)],
            check=True,
        )
        if not code_bin.exists():
            found = [p for p in cache_dir.rglob("code") if p.is_file()]
            if not found:
                raise RuntimeError(f"VS Code CLI binary not found under {cache_dir}")
            if found[0] != code_bin:
                found[0].replace(code_bin)
        code_bin.chmod(0o755)

    print(f"VS Code CLI ready at {code_bin}", flush=True)
    return {
        "code_bin": code_bin,
        "cache_dir": cache_dir,
        "user_data_dir": user_data_dir,
        "cli_data_dir": cli_data_dir,
        "server_bin": code_bin,
        "extensions_dir": user_data_dir / "extensions",
    }


def _cli_base(prepared: dict) -> list[str]:
    return [
        str(prepared["code_bin"]),
        "--cli-data-dir",
        str(prepared["cli_data_dir"]),
    ]


def login_vscode(prepared: dict, provider: str = "github", timeout: int = 600) -> None:
    """Run GitHub/Microsoft device login for the tunnel (interactive once)."""
    cmd = [
        *_cli_base(prepared),
        "tunnel",
        "user",
        "login",
        "--provider",
        provider,
    ]
    print(f"Starting VS Code tunnel login ({provider})...", flush=True)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    if proc.stdout is None:
        raise RuntimeError("Failed to capture login process output.")

    url_re = re.compile(
        r"(https://(?:github\.com/login/device|login\.microsoftonline\.com/\S+))"
    )
    code_re = re.compile(r"(?:use code|enter the code)\s+([A-Z0-9-]+)", re.I)
    code_re2 = re.compile(r"\b([A-Z0-9]{4,}-[A-Z0-9]{4,})\b")

    shown_auth = False
    deadline = time.time() + timeout
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            break
        if not line:
            time.sleep(0.05)
            continue
        line = line.rstrip()
        print(line, flush=True)

        url_m = url_re.search(line)
        code_m = code_re.search(line) or code_re2.search(line)
        if url_m and code_m and not shown_auth:
            print(
                f"\n>>> Authorize this Colab session:\n"
                f"    Open {url_m.group(1)}\n"
                f"    Enter code: {code_m.group(1)}\n",
                flush=True,
            )
            shown_auth = True

    if proc.poll() is None:
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            pass

    print("Tunnel login finished.", flush=True)


def _extension_install_args(extensions: list, cache_dir: Path) -> list[str]:
    """Build repeated ``--install-extension`` args (marketplace IDs or VSIX paths)."""
    args: list[str] = []
    for ext in extensions or []:
        if isinstance(ext, str):
            args.extend(["--install-extension", ext])
            continue
        vsix = ext["vsix"]
        vsix_path = Path(vsix)
        if not vsix_path.is_absolute():
            vsix_path = cache_dir / vsix
        if ext.get("url"):
            _ensure_vsix(vsix_path, ext["url"], ext.get("id") or vsix_path.name)
        elif not vsix_path.exists() or not _is_valid_vsix(vsix_path):
            raise FileNotFoundError(f"VSIX not found: {vsix_path}")
        args.extend(["--install-extension", str(vsix_path)])
    return args


def start_vscode_web(
    prepared: dict,
    folder: str | Path,
    port: int = 3000,
    host: str = "0.0.0.0",
    *,
    tunnel_name: str = "vscolab",
    extensions: list | None = None,
    timeout: int = 180,
) -> str:
    """Start ``code tunnel`` and return the ``vscode.dev`` URL.

    ``port`` / ``host`` are ignored (kept for call-site compatibility).
    """
    del port, host
    folder = str(Path(folder).resolve())
    Path(folder).mkdir(parents=True, exist_ok=True)

    cmd = [
        *_cli_base(prepared),
        "tunnel",
        "--accept-server-license-terms",
        "--name",
        tunnel_name,
        *_extension_install_args(extensions or [], prepared["cache_dir"]),
    ]

    print(f"Starting VS Code tunnel '{tunnel_name}' (cwd={folder})...", flush=True)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=folder,
    )
    if proc.stdout is None:
        raise RuntimeError("Failed to capture tunnel process output.")

    url_re = re.compile(r"(https://vscode\.dev/tunnel/[^\s]+)")
    deadline = time.time() + timeout
    tunnel_url: str | None = None

    while time.time() < deadline:
        if proc.poll() is not None and tunnel_url is None:
            rest = proc.stdout.read() or ""
            if rest:
                print(rest, end="", flush=True)
            raise RuntimeError(
                f"VS Code tunnel exited early (code {proc.returncode}) before URL appeared."
            )
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.05)
            continue
        print(line.rstrip(), flush=True)
        match = url_re.search(line)
        if match:
            tunnel_url = match.group(1).rstrip(").,]")
            break

    if not tunnel_url:
        raise RuntimeError(
            f"Timed out waiting for vscode.dev tunnel URL ({timeout}s)."
        )

    folder_name = Path(folder).name
    if folder_name and not tunnel_url.rstrip("/").endswith(folder_name):
        tunnel_url = tunnel_url.rstrip("/") + "/" + folder_name

    print(f"VS Code tunnel ready: {tunnel_url}", flush=True)
    prepared["tunnel_proc"] = proc
    return tunnel_url


def vscode_proxy_url(base_proxy_url: str, folder: str | Path) -> str:
    """Compatibility shim — tunnel URLs are already complete."""
    del folder
    return base_proxy_url
