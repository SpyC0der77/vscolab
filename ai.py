import subprocess
from pathlib import Path

from colab_lm_bridge import setup_colab_lm
from extensions_install import install_extensions
from google.colab.output import eval_js
from vscode_bootstrap import prepare_vscode, start_vscode_web, vscode_proxy_url

PORT = 3000
GIT_REPO = ""
# Pin a commit hash to freeze the VS Code build, or leave empty for latest stable.
COMMIT = ""
VSCOLAB_RAW = "https://github.com/SpyC0der77/vscolab/raw/master"
EXTENSIONS = [
    # Official Chat agent (Microsoft Marketplace) — required for the model picker.
    "GitHub.copilot-chat",
    {
        "vsix": "colab-lm-0.1.0.vsix",
        "url": f"{VSCOLAB_RAW}/extensions/colab-lm/colab-lm-0.1.0.vsix",
    },
]
CACHE_DIR = Path("/content/vscode-cache")
USER_DATA_DIR = Path("/content/.vscode-server-data")

folder = Path("/content/workspace")
if GIT_REPO:
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
install_extensions(prepared["server_bin"], EXTENSIONS, USER_DATA_DIR, CACHE_DIR)
setup_colab_lm()
start_vscode_web(prepared, folder, PORT)

# CELL 2
proxy = eval_js(f'google.colab.kernel.proxyPort({PORT}, {{"cache": false}})')
url = vscode_proxy_url(proxy, folder)
print(f"Open VS Code: {url}", flush=True)
