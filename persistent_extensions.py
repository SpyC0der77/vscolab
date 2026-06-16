"""Google Drive persistence + openvscode-server bootstrap for vscolab.

Syncs the VS Code ``--default-folder`` path with ``MyDrive/vscolab/`` on Drive.
Load: pull once (Drive -> workspace). Runtime: push-only background sync.
Includes EasyInstaller pre-installed from the bundled VSIX.
"""

import json
import subprocess
import threading
import time
import zipfile
from pathlib import Path

from google.colab import drive, output

SYNC_INTERVAL = 5
DRIVE_STORE = Path("/content/drive/MyDrive/vscolab")
IGNORE_FILE = ".vscolabignore"
DEFAULT_IGNORE = """\
# Patterns here stay on the Colab VM only — never synced to Drive.
__pycache__/
*.py[cod]
node_modules/
.venv/
venv/
*.egg-info/
.git/
"""

VERSION = "openvscode-server-v1.109.5"
PORT = 3000
GIT_REPO = "https://github.com/microsoft/vscode.git"
EASYINSTALLER_VSIX = "easy-installer-1.0.0.vsix"
EASYINSTALLER_URL = (
    "https://github.com/SpyC0der77/vscolab/raw/master"
    f"/extensions/easy-installer/{EASYINSTALLER_VSIX}"
)
EASYINSTALLER_EXTENSION = "vscolab.easy-installer-1.0.0"


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


class Persistence:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()

    @property
    def drive_store(self) -> Path:
        return DRIVE_STORE

    @property
    def data_dir(self) -> Path:
        return DRIVE_STORE / "data"

    @property
    def cache_dir(self) -> Path:
        return DRIVE_STORE / "cache"

    def mount(self) -> None:
        print("Mounting Google Drive...", flush=True)
        drive.mount("/content/drive")
        for d in (self.drive_store, self.data_dir, self.cache_dir):
            d.mkdir(parents=True, exist_ok=True)
        print(f"vscolab folder: {self.drive_store}", flush=True)

    def _ignore_file(self) -> Path:
        path = self.drive_store / IGNORE_FILE
        if not path.exists():
            path.write_text(DEFAULT_IGNORE)
        return path

    def _sync_ignore_for_pull(self) -> None:
        self.workspace.mkdir(parents=True, exist_ok=True)
        (self.workspace / IGNORE_FILE).write_text(self._ignore_file().read_text())

    def _sync_ignore_for_push(self) -> None:
        ws_ignore = self.workspace / IGNORE_FILE
        drive_ignore = self._ignore_file()
        if ws_ignore.exists():
            drive_ignore.write_text(ws_ignore.read_text())
        else:
            ws_ignore.write_text(drive_ignore.read_text())

    def _ensure_writable(self) -> None:
        subprocess.run(["chmod", "-R", "u+w", str(self.workspace)], check=False)

    def pull(self) -> None:
        print(f"Pulling from Drive into {self.workspace}...", flush=True)
        self._sync_ignore_for_pull()
        subprocess.run(
            [
                "rsync", "-rl",
                "--no-perms", "--no-owner", "--no-group",
                "--filter=:- .vscolabignore",
                "--exclude=data/", "--exclude=cache/",
                f"{self.drive_store}/", f"{self.workspace}/",
            ],
            check=False,
        )
        self._ensure_writable()

    def push(self) -> None:
        self._sync_ignore_for_push()
        subprocess.run(
            [
                "ionice", "-c3", "nice", "-n", "19",
                "rsync", "-rl",
                "--size-only",
                "--no-perms", "--no-owner", "--no-group",
                "--filter=:- .vscolabignore",
                "--delete", "--delete-excluded",
                "--exclude=data/", "--exclude=cache/",
                f"{self.workspace}/", f"{self.drive_store}/",
            ],
            check=False,
        )

    def start_push_loop(self) -> None:
        def loop():
            while True:
                time.sleep(SYNC_INTERVAL)
                self.push()

        threading.Thread(target=loop, daemon=True).start()
        print(
            f"Background push every {SYNC_INTERVAL}s -> Drive (see {IGNORE_FILE})",
            flush=True,
        )


folder = Path("/content")
if GIT_REPO:
    name = GIT_REPO.rstrip("/").removesuffix(".git").split("/")[-1]
    folder = Path(f"/content/{name}")

p = Persistence(workspace=folder)
p.mount()
p.pull()

if GIT_REPO and not folder.exists():
    print(f"Cloning {GIT_REPO}...", flush=True)
    subprocess.run(["git", "clone", "--progress", GIT_REPO, str(folder)], check=True)
    p.push()

url = f"https://github.com/gitpod-io/openvscode-server/releases/download/{VERSION}/{VERSION}-linux-x64.tar.gz"
tarball = f"{VERSION}-linux-x64.tar.gz"
tarball_path = p.cache_dir / tarball
local_server = Path(f"/content/{VERSION}-linux-x64")
server_bin = local_server / "bin/openvscode-server"

if not tarball_path.exists():
    print("Downloading openvscode-server...", flush=True)
    subprocess.run(["wget", "--show-progress", "-O", str(tarball_path), url], check=True)
else:
    print(f"Using cached tarball at {tarball_path}", flush=True)

if not local_server.exists():
    print("Extracting...", flush=True)
    subprocess.run(["tar", "-xzf", str(tarball_path), "-C", "/content"], check=True)
else:
    print(f"Using extracted server at {local_server}", flush=True)

vsix_path = p.cache_dir / EASYINSTALLER_VSIX
if vsix_path.exists() and _is_valid_vsix(vsix_path):
    print(f"Using cached EasyInstaller at {vsix_path}", flush=True)
else:
    _ensure_easyinstaller_vsix(vsix_path, EASYINSTALLER_URL)
install_easyinstaller(server_bin, vsix_path, p.data_dir)

p.push()
p.start_push_loop()

folder = str(folder.resolve())

print(f"Starting openvscode-server (default folder: {folder})...", flush=True)
subprocess.Popen([
    str(server_bin),
    "--host", "0.0.0.0",
    "--port", str(PORT),
    "--without-connection-token",
    "--accept-server-license-terms",
    "--server-data-dir", str(p.data_dir),
    "--default-folder", folder,
])
time.sleep(5)
print(f"openvscode-server running on port {PORT} — {folder}", flush=True)
print(f"Drive storage: {p.drive_store}", flush=True)

# CELL 2
output.serve_kernel_port_as_iframe(PORT, height=800)
