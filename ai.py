from pathlib import Path

from colab_lm_bridge import setup_colab_lm
from vscode_bootstrap import login_vscode, prepare_vscode, start_vscode_web

PORT = 3000  # unused with tunnels; kept for notebook compatibility
GIT_REPO = ""
COMMIT = ""
VSCOLAB_RAW = "https://github.com/SpyC0der77/vscolab/raw/master"
EXTENSIONS = [
    # Copilot Chat ships with official VS Code — do not marketplace-install it.
    {
        "vsix": "colab-lm-0.1.0.vsix",
        "url": f"{VSCOLAB_RAW}/extensions/colab-lm/colab-lm-0.1.0.vsix",
    },
]
CACHE_DIR = Path("/content/vscode-cache")
USER_DATA_DIR = Path("/content/.vscode-server-data")
TUNNEL_NAME = "vscolab-ai"

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
setup_colab_lm()
url = start_vscode_web(
    prepared,
    folder,
    tunnel_name=TUNNEL_NAME,
    extensions=EXTENSIONS,
)
print(f"Open VS Code: {url}", flush=True)
print("Colab AI bridge is on http://127.0.0.1:8787 (reachable from the remote tunnel).", flush=True)
