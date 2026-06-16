# vscolab

Run [openvscode-server](https://github.com/gitpod-io/openvscode-server) inside [Google Colab](https://colab.research.google.com/) and edit code in a full VS Code UI embedded in the notebook. Optional Google Drive sync keeps your workspace across Colab sessions.

## Quick start


|                   | Ephemeral                                                                                                         | **Persistent**                                                                                                               |
| ----------------- | ----------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **EasyInstaller** | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab.ipynb)            | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab_persistent.ipynb)            |
| **Barebones**     | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab_extensions.ipynb) | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab_persistent_extensions.ipynb) |


1. Open a notebook in Colab.
2. Run all cells.
3. When prompted, authorize Google Drive (persistent notebook only).
4. VS Code appears in an iframe below the cell output.

## How it works

Both notebooks bootstrap **openvscode-server** on port `3000` and expose it with Colab's `output.serve_kernel_port_as_iframe()`.

```
Colab notebook cell
       │
       ▼
Download / cache openvscode-server tarball
       │
       ▼
(Optional) git clone → workspace folder
       │
       ▼
Start openvscode-server (--default-folder, --server-data-dir)
       │
       ▼
Iframe embed in notebook output
```

### Barebones (`vscolab.ipynb` / `barebones.py`)

- Downloads and extracts openvscode-server into `/content`.
- Optionally clones a git repo into `/content/<repo-name>`.
- No persistence — workspace is lost when the Colab VM is recycled.

### Barebones + EasyInstaller (`vscolab_extensions.ipynb` / `barebones_extensions.py`)

Same as barebones, plus downloads and installs the bundled EasyInstaller VSIX before starting the server. Server state (including the extension) lives under `/content/.openvscode-server-data` for the session.

### Persistent (`vscolab_persistent.ipynb` / `persistent.py`)

Adds a `Persistence` class that syncs the workspace with Google Drive:


| Phase    | Direction  | When                                |
| -------- | ---------- | ----------------------------------- |
| **Pull** | Drive → VM | Once at startup                     |
| **Push** | VM → Drive | Every 5 seconds (background thread) |


Drive layout:

```
MyDrive/vscolab/
├── .vscolabignore      # Sync exclude rules
├── data/               # VS Code server state (extensions, settings)
├── cache/              # Cached openvscode-server tarball
└── …                   # Your synced workspace files
```

The openvscode-server tarball and VS Code user data are cached under `cache/` and `data/` on Drive so subsequent sessions skip re-downloading and preserve extensions.

### Persistent + EasyInstaller (`vscolab_persistent_extensions.ipynb` / `persistent_extensions.py`)

Same as persistent, plus caches the EasyInstaller VSIX under `cache/` and installs it into `data/` on startup. EasyInstaller and other extensions persist across Colab sessions.

## Configuration

Edit the constants at the top of the notebook (or script):


| Variable        | Default                                   | Purpose                                                   |
| --------------- | ----------------------------------------- | --------------------------------------------------------- |
| `VERSION`       | `openvscode-server-v1.109.5`              | Server release to download                                |
| `PORT`          | `3000`                                    | Port for the embedded iframe                              |
| `GIT_REPO`      | `https://github.com/microsoft/vscode.git` | Repo to clone as workspace; set to `""` to use `/content` |
| `SYNC_INTERVAL` | `5`                                       | Seconds between Drive pushes (persistent only)            |


## `.vscolabignore`

Patterns listed in `.vscolabignore` stay on the Colab VM and are never pushed to Drive. A default file is created on first run:

```
__pycache__/
*.py[cod]
node_modules/
.venv/
venv/
*.egg-info/
.git/
```

Edit `.vscolabignore` in your workspace (via VS Code in Colab or at `/content/<repo>/.vscolabignore`).

## Repository layout

```
vscolab/
├── vscolab.ipynb                      # Barebones Colab notebook
├── vscolab_persistent.ipynb           # Persistent Colab notebook
├── vscolab_extensions.ipynb           # Barebones + EasyInstaller
├── vscolab_persistent_extensions.ipynb  # Persistent + EasyInstaller
├── barebones.py                       # Script source for barebones notebook
├── persistent.py                      # Script source for persistent notebook
├── barebones_extensions.py            # Script source for barebones + EasyInstaller
├── persistent_extensions.py           # Script source for persistent + EasyInstaller
└── extensions/
    └── easy-installer/                # VS Code extension for installing dev tools
```

The `.py` files mirror the notebook cells and are useful for local editing or diffing.

## EasyInstaller extension

The repo includes [EasyInstaller](extensions/easy-installer/), a VS Code sidebar extension for installing languages and tools (Python, Node.js, Rust, Go, Java, Git, and more) from the integrated terminal.

Use [vscolab_extensions.ipynb](vscolab_extensions.ipynb) or [vscolab_persistent_extensions.ipynb](vscolab_persistent_extensions.ipynb) to have it installed automatically, or install it manually after the first session. Build from source:

```bash
cd extensions/easy-installer
bun install
bun run compile
```

See [extensions/easy-installer/README.md](extensions/easy-installer/README.md) for commands, settings, and packaging.

## Requirements

- Google Colab runtime (Linux VM)
- Google account with Drive access (persistent notebook)
- Network access to GitHub releases (openvscode-server download)

## Limitations

- Colab VMs are ephemeral; without the persistent notebook, all local changes are lost on disconnect.
- Background sync is push-only after the initial pull — edits made directly on Drive while a session is running may be overwritten on the next push.
- Large folders (e.g. `node_modules`, `.git`) should stay in `.vscolabignore` to avoid slow syncs and Drive quota use.
- `--without-connection-token` is used for Colab iframe embedding; do not expose the server outside a trusted Colab session.

## License

MIT