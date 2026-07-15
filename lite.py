from pathlib import Path

from vscode_bootstrap import login_vscode, prepare_vscode, start_vscode_web

PORT = 3000  # unused with tunnels; kept for notebook compatibility
GIT_REPO = ""
COMMIT = ""
CACHE_DIR = Path("/content/vscode-cache")
USER_DATA_DIR = Path("/content/.vscode-server-data")
TUNNEL_NAME = "vscolab"

folder = Path("/content/workspace")
if GIT_REPO:
    import subprocess

    name = GIT_REPO.rstrip("/").removesuffix(".git").split("/")[-1]
    folder = Path(f"/content/{name}")
    if not folder.exists():
        print(f"Cloning {GIT_REPO}...", flush=True)
        subprocess.run(["git", "clone", "--progress", GIT_REPO, str(folder)], check=True)
    else:
        print(f"Using existing clone at {folder}", flush=True)
else:
    folder.mkdir(parents=True, exist_ok=True)

folder = str(folder.resolve())
prepared = prepare_vscode(CACHE_DIR, USER_DATA_DIR, COMMIT)
login_vscode(prepared)
url = start_vscode_web(prepared, folder, tunnel_name=TUNNEL_NAME)
print(f"Open VS Code: {url}", flush=True)
