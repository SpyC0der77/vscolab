import json
import shutil
import subprocess
import zipfile
from pathlib import Path


def _is_valid_vsix(path: Path) -> bool:
    with path.open("rb") as f:
        return f.read(2) == b"PK"


def _extension_id_from_vsix(vsix_path: Path) -> str:
    with zipfile.ZipFile(vsix_path) as zf:
        data = json.loads(zf.read("extension/package.json"))
    return f"{data['publisher']}.{data['name']}-{data['version']}"


def _ensure_vsix(vsix_path: Path, url: str, label: str) -> None:
    if vsix_path.exists() and _is_valid_vsix(vsix_path):
        return
    if vsix_path.exists():
        print(f"Removing invalid VSIX at {vsix_path}", flush=True)
        vsix_path.unlink()
    print(f"Downloading {label}...", flush=True)
    subprocess.run(["wget", "--show-progress", "-O", str(vsix_path), url], check=True)
    if not _is_valid_vsix(vsix_path):
        raise RuntimeError(
            f"Downloaded file at {vsix_path} is not a valid VSIX (expected zip archive)."
        )


def _ensure_server_settings(server_data_dir: Path) -> None:
    settings_dir = server_data_dir / "User"
    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_path = settings_dir / "settings.json"
    settings = {}
    if settings_path.exists():
        settings = json.loads(settings_path.read_text())
    settings["extensions.verifySignature"] = False
    settings["security.workspace.trust.enabled"] = False
    settings["security.workspace.trust.startupPrompt"] = "never"
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")


def _install_vsix_manually(vsix_path: Path, server_data_dir: Path, ext_id: str) -> None:
    target = server_data_dir / "extensions" / ext_id
    if target.exists():
        return
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(vsix_path) as zf:
        for member in zf.namelist():
            if not member.startswith("extension/") or member.endswith("/"):
                continue
            rel = member[len("extension/") :]
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(zf.read(member))
    print(f"Extension extracted to {target}", flush=True)


def _install_marketplace(server_bin: Path, ext_id: str, server_data_dir: Path) -> None:
    ext_dir = server_data_dir / "extensions"
    if any(ext_dir.glob(f"{ext_id}*")):
        print(f"{ext_id} already installed", flush=True)
        return

    print(f"Installing {ext_id}...", flush=True)
    result = subprocess.run(
        [
            str(server_bin),
            "--install-extension",
            ext_id,
            "--force",
            "--accept-server-license-terms",
            "--server-data-dir",
            str(server_data_dir),
        ],
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print(result.stdout, end="", flush=True)
    if result.stderr:
        print(result.stderr, end="", flush=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to install extension {ext_id}.")


def _install_vsix(
    server_bin: Path,
    vsix_path: Path,
    server_data_dir: Path,
    ext_id: str,
) -> None:
    ext_dir = server_data_dir / "extensions" / ext_id
    if ext_dir.exists():
        print(f"{ext_id} already installed at {ext_dir}", flush=True)
        return

    # Drop older builds of the same extension so updates take effect.
    with zipfile.ZipFile(vsix_path) as zf:
        meta = json.loads(zf.read("extension/package.json"))
    base = f"{meta['publisher']}.{meta['name']}"
    ext_root = server_data_dir / "extensions"
    if ext_root.exists():
        for old in ext_root.glob(f"{base}-*"):
            if old.name == ext_id:
                continue
            print(f"Removing older extension {old.name}", flush=True)
            shutil.rmtree(old, ignore_errors=True)

    print(f"Installing {ext_id}...", flush=True)
    result = subprocess.run(
        [
            str(server_bin),
            "--install-extension",
            str(vsix_path),
            "--force",
            "--accept-server-license-terms",
            "--server-data-dir",
            str(server_data_dir),
        ],
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print(result.stdout, end="", flush=True)
    if result.stderr:
        print(result.stderr, end="", flush=True)

    if result.returncode == 0:
        return

    print("CLI install failed, extracting VSIX manually...", flush=True)
    _install_vsix_manually(vsix_path, server_data_dir, ext_id)
    if not ext_dir.exists():
        raise RuntimeError(f"Failed to install extension {ext_id}.")


def install_extensions(
    server_bin: Path,
    extensions: list,
    server_data_dir: Path,
    cache_dir: Path,
) -> None:
    server_data_dir.mkdir(parents=True, exist_ok=True)
    _ensure_server_settings(server_data_dir)

    if not extensions:
        return

    for ext in extensions:
        if isinstance(ext, str):
            _install_marketplace(server_bin, ext, server_data_dir)
            continue

        vsix = ext["vsix"]
        vsix_path = Path(vsix)
        if not vsix_path.is_absolute():
            vsix_path = cache_dir / vsix

        label = ext.get("id") or vsix_path.name
        if ext.get("url"):
            if vsix_path.exists() and _is_valid_vsix(vsix_path):
                print(f"Using cached {label} at {vsix_path}", flush=True)
            else:
                _ensure_vsix(vsix_path, ext["url"], label)
        elif not vsix_path.exists():
            raise FileNotFoundError(f"VSIX not found: {vsix_path}")

        ext_id = ext.get("id") or _extension_id_from_vsix(vsix_path)
        _install_vsix(server_bin, vsix_path, server_data_dir, ext_id)
