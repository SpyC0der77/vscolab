"""Google Drive persistence for vscolab.

Syncs the VS Code ``--default-folder`` path with ``MyDrive/vscolab/`` on Drive.
Load: pull once (Drive -> workspace). Runtime: push-only background sync.

Manual test (Colab):
1. Run barebones cell 1 — approve Drive mount; confirm MyDrive/vscolab/ exists.
2. Confirm .vscolabignore appears on Drive.
3. Edit a file in VS Code; wait ~5s — file appears on Drive; ignored paths do not.
4. Restart runtime — pull restores files into the same --default-folder path.
5. Extensions/settings persist via data/ across restarts.
"""

import subprocess
import threading
import time
from pathlib import Path

from google.colab import drive

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

    def _sync_ignore_to_workspace(self) -> None:
        self.workspace.mkdir(parents=True, exist_ok=True)
        (self.workspace / IGNORE_FILE).write_text(self._ignore_file().read_text())

    def _ensure_writable(self) -> None:
        subprocess.run(["chmod", "-R", "u+w", str(self.workspace)], check=False)

    def pull(self) -> None:
        print(f"Pulling from Drive into {self.workspace}...", flush=True)
        self._sync_ignore_to_workspace()
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
        self._sync_ignore_to_workspace()
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
