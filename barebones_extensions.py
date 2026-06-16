import json
import subprocess
import time
import zipfile
from pathlib import Path

VERSION = "openvscode-server-v1.109.5"
PORT = 3000
GIT_REPO = "https://github.com/microsoft/vscode.git"
EASYINSTALLER_VSIX = "easy-installer-1.0.0.vsix"
EASYINSTALLER_URL = (
    "https://github.com/SpyC0der77/vscolab/raw/master"
    f"/extensions/easy-installer/{EASYINSTALLER_VSIX}"
)
EASYINSTALLER_EXTENSION = "vscolab.easy-installer-1.0.0"
SERVER_DATA_DIR = Path("/content/.openvscode-server-data")


def _is_valid_vsix(path: Path) -> bool:
    with path.open("rb") as f:
        return f.read(2) == b"PK"


def _ensure_easyinstaller_vsix(vsix_path: Path, url: str) -> None:
    if vsix_path.exists() and _is_valid_vsix(vsix_path):
        return
    if vsix_path.exists():
        print(f"Removing invalid VSIX at {vsix_path}", flush=True)
        vsix_path.unlink()
    print("Downloading EasyInstaller...", flush=True)
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
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")


def _install_vsix_manually(vsix_path: Path, server_data_dir: Path) -> None:
    target = server_data_dir / "extensions" / EASYINSTALLER_EXTENSION
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
    print(f"EasyInstaller extracted to {target}", flush=True)


def install_easyinstaller(
    server_bin: Path,
    vsix_path: Path,
    server_data_dir: Path,
) -> None:
    server_data_dir.mkdir(parents=True, exist_ok=True)
    _ensure_server_settings(server_data_dir)

    ext_dir = server_data_dir / "extensions" / EASYINSTALLER_EXTENSION
    if ext_dir.exists():
        print(f"EasyInstaller already installed at {ext_dir}", flush=True)
        return

    print("Installing EasyInstaller extension...", flush=True)
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
    _install_vsix_manually(vsix_path, server_data_dir)
    if not ext_dir.exists():
        raise RuntimeError("Failed to install EasyInstaller extension.")

url = f"https://github.com/gitpod-io/openvscode-server/releases/download/{VERSION}/{VERSION}-linux-x64.tar.gz"
tarball = f"{VERSION}-linux-x64.tar.gz"

print("Downloading openvscode-server...", flush=True)
subprocess.run(["wget", "--show-progress", "-O", tarball, url], check=True)

print("Extracting...", flush=True)
subprocess.run(["tar", "-xzf", tarball], check=True)

local_server = Path(f"/content/{VERSION}-linux-x64")
server_bin = local_server / "bin/openvscode-server"
SERVER_DATA_DIR.mkdir(parents=True, exist_ok=True)

vsix_path = Path(f"/content/{EASYINSTALLER_VSIX}")
_ensure_easyinstaller_vsix(vsix_path, EASYINSTALLER_URL)
install_easyinstaller(server_bin, vsix_path, SERVER_DATA_DIR)

folder = Path("/content")
if GIT_REPO:
    name = GIT_REPO.rstrip("/").removesuffix(".git").split("/")[-1]
    folder = Path(f"/content/{name}")
    if not folder.exists():
        print(f"Cloning {GIT_REPO}...", flush=True)
        subprocess.run(["git", "clone", "--progress", GIT_REPO, str(folder)], check=True)
    else:
        print(f"Using existing clone at {folder}", flush=True)

folder = str(folder.resolve())

print(f"Starting openvscode-server (default folder: {folder})...", flush=True)
subprocess.Popen([
    str(server_bin),
    "--host", "0.0.0.0",
    "--port", str(PORT),
    "--without-connection-token",
    "--accept-server-license-terms",
    "--server-data-dir", str(SERVER_DATA_DIR),
    "--default-folder", folder,
])
time.sleep(5)
print(f"openvscode-server running on port {PORT} — {folder}", flush=True)

# CELL 2
from google.colab import output

output.serve_kernel_port_as_iframe(PORT, height=800)
