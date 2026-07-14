"""Google Drive persistence + openvscode-server bootstrap for vscolab.

Syncs the VS Code ``--default-folder`` path with ``MyDrive/vscolab/`` on Drive.
Load: pull once (Drive -> workspace). Runtime: push-only background sync.
Pre-installs extensions from ``EXTENSIONS`` (marketplace IDs and/or VSIX).
"""

import subprocess
import threading
import time
from pathlib import Path

from colab_chat import CONTINUE_EXTENSION, setup_colab_chat
from extensions_install import install_extensions
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
GIT_REPO = ""
VSCOLAB_RAW = "https://github.com/SpyC0der77/vscolab/raw/master"
EXTENSIONS = [
    CONTINUE_EXTENSION,
    {
        "vsix": "easy-installer-1.0.0.vsix",
        "url": f"{VSCOLAB_RAW}/extensions/easy-installer/easy-installer-1.0.0.vsix",
    },
    # Marketplace IDs:
    # "ms-python.python",
]


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


folder = Path("/content/workspace")
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

install_extensions(server_bin, EXTENSIONS, p.data_dir, p.cache_dir)
setup_colab_chat()

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
url = output.eval_js(f'google.colab.kernel.proxyPort({PORT}, {{"cache": false}})')
print(f"Open VS Code: {url}", flush=True)
