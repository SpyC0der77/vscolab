import subprocess, time
from pathlib import Path

from persistencelib import Persistence

VERSION = "openvscode-server-v1.109.5"
PORT = 3000
GIT_REPO = "https://github.com/microsoft/vscode.git"

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

p.push()
p.start_push_loop()

folder = str(folder.resolve())

print(f"Starting openvscode-server (default folder: {folder})...", flush=True)
subprocess.Popen([
    str(local_server / "bin/openvscode-server"),
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
from google.colab import output

output.serve_kernel_port_as_iframe(PORT, height=800)
