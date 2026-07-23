"""Google Drive persistence + official VS Code tunnel for vscolab AI tier.

Syncs the workspace with ``MyDrive/vscolab/`` on Drive.
Pre-installs the Colab AI LM provider and starts the Colab AI bridge.
"""

import subprocess
import threading
import time
from pathlib import Path

from colab_lm_bridge import setup_colab_lm
from google.colab import drive
from vscode_bootstrap import login_vscode, prepare_vscode, start_vscode_web

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

PORT = 3000  # unused with tunnels
GIT_REPO = ""
COMMIT = ""
VSCOLAB_RAW = "https://github.com/SpyC0der77/vscolab/raw/master"
EXTENSIONS = [
    {
        "vsix": "colab-lm-0.2.6.vsix",
        "url": f"{VSCOLAB_RAW}/extensions/colab-lm/colab-lm-0.2.6.vsix",
    },
]
TUNNEL_NAME = "vscolab-ai"


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

prepared = prepare_vscode(p.cache_dir, p.data_dir, COMMIT)
login_vscode(prepared)

p.push()
p.start_push_loop()

folder = str(folder.resolve())
setup_colab_lm()
url = start_vscode_web(
    prepared,
    folder,
    tunnel_name=TUNNEL_NAME,
    extensions=EXTENSIONS,
)
print(f"Drive storage: {p.drive_store}", flush=True)
print(f"Open VS Code: {url}", flush=True)
print("Colab AI bridge is on http://127.0.0.1:8787 (reachable from the remote tunnel).", flush=True)
