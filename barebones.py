import subprocess, time
from pathlib import Path

VERSION = "openvscode-server-v1.109.5"
PORT = 3000
GIT_REPO = "https://github.com/microsoft/vscode.git"

url = f"https://github.com/gitpod-io/openvscode-server/releases/download/{VERSION}/{VERSION}-linux-x64.tar.gz"
tarball = f"{VERSION}-linux-x64.tar.gz"

print("Downloading openvscode-server...", flush=True)
subprocess.run(["wget", "--show-progress", "-O", tarball, url], check=True)

print("Extracting...", flush=True)
subprocess.run(["tar", "-xzf", tarball], check=True)

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
    f"./{VERSION}-linux-x64/bin/openvscode-server",
    "--host", "0.0.0.0",
    "--port", str(PORT),
    "--without-connection-token",
    "--default-folder", folder,
])
time.sleep(5)
print(f"openvscode-server running on port {PORT} — {folder}", flush=True)

# CELL 2
from google.colab import output

output.serve_kernel_port_as_iframe(PORT, height=800)
