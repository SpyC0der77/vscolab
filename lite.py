from pathlib import Path

from google.colab.output import eval_js
from vscode_bootstrap import prepare_vscode, start_vscode_web, vscode_proxy_url

PORT = 3000
GIT_REPO = ""
# Pin a commit hash to freeze the VS Code build, or leave empty for latest stable.
COMMIT = ""
CACHE_DIR = Path("/content/vscode-cache")
USER_DATA_DIR = Path("/content/.vscode-server-data")

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
start_vscode_web(prepared, folder, PORT)

# CELL 2
proxy = eval_js(f'google.colab.kernel.proxyPort({PORT}, {{"cache": false}})')
url = vscode_proxy_url(proxy, folder)
print(f"Open VS Code: {url}", flush=True)
