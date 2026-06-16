import subprocess, time
from pathlib import Path

VERSION = "openvscode-server-v1.109.5"
PORT = 3000
GIT_REPO = "https://github.com/microsoft/vscode.git"
EASYINSTALLER_VSIX = "easy-installer-1.0.0.vsix"
EASYINSTALLER_URL = (
    "https://github.com/SpyC0der77/vscolab/raw/master"
    f"/extensions/easy-installer/{EASYINSTALLER_VSIX}"
)
SERVER_DATA_DIR = Path("/content/.openvscode-server-data")

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
if not vsix_path.exists():
    print("Downloading EasyInstaller...", flush=True)
    subprocess.run(["wget", "--show-progress", "-O", str(vsix_path), EASYINSTALLER_URL], check=True)

print("Installing EasyInstaller extension...", flush=True)
subprocess.run([
    str(server_bin),
    "--install-extension", str(vsix_path),
    "--accept-server-license-terms",
    "--server-data-dir", str(SERVER_DATA_DIR),
], check=True)

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
