# vscolab

Run [openvscode-server](https://github.com/gitpod-io/openvscode-server) inside [Google Colab](https://colab.research.google.com/) and edit code in a full VS Code UI in a new browser tab. Optional Google Drive sync keeps your workspace across Colab sessions.

## Quick start


|              | Ephemeral                                                                                                          | **Persistent**                                                                                                                              |
| ------------ | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **Lite**     | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab_lite.ipynb)        | —                                                                                                                                           |
| **Standard** | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab_standard.ipynb)    | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab_standard_persistent.ipynb)                  |
| **Studio**   | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab_studio.ipynb)      | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab_studio_persistent.ipynb)                    |


1. Open a notebook in Colab.
2. Run all cells.
3. When prompted, authorize Google Drive (persistent notebook only).
4. Click the **Open VS Code** URL printed in the cell output.

## How it works

All notebooks bootstrap **openvscode-server** on port `3000` and expose it with Colab's `google.colab.kernel.proxyPort()`.

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
(Optional) install extensions from ``EXTENSIONS``  ← Standard, Studio variants
       │
       ▼
Start openvscode-server (--default-folder; optional --server-data-dir)
       │
       ▼
Print Colab proxy URL to open VS Code in a new tab
```

### Lite (`vscolab_lite.ipynb` / `lite.py`)

Minimal launcher — download, extract, start openvscode-server, print proxy URL. No extension pre-install, no `server-data-dir`, no Drive sync.

### Standard (`vscolab_standard.ipynb` / `standard.py`)

- Downloads and extracts openvscode-server into `/content`.
- Optionally clones a git repo into `/content/<repo-name>`; otherwise uses `/content/workspace`.
- Pre-installs any entries in `EXTENSIONS` (empty by default).
- No persistence — workspace is lost when the Colab VM is recycled.

### Studio (`vscolab_studio.ipynb` / `studio.py`)

Same as Standard, with EasyInstaller also pre-populated in `EXTENSIONS`. Server state lives under `/content/.openvscode-server-data` for the session.

### Standard Persistent (`vscolab_standard_persistent.ipynb` / `standard_persistent.py`)

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

### Studio Persistent (`vscolab_studio_persistent.ipynb` / `studio_persistent.py`)

Same as Standard Persistent, with EasyInstaller pre-populated in `EXTENSIONS`. VSIX files cache under `cache/`; installed extensions persist in `data/` on Drive.

## Configuration

Edit the constants at the top of the notebook (or script):


| Variable        | Default                                   | Purpose                                                   |
| --------------- | ----------------------------------------- | --------------------------------------------------------- |
| `VERSION`       | `openvscode-server-v1.109.5`              | Server release to download                                |
| `PORT`          | `3000`                                    | Port for the Colab proxy URL                              |
| `GIT_REPO`      | `""`                                      | Repo to clone as workspace; uses `/content/workspace` when empty |
| `EXTENSIONS`    | `[]` (EasyInstaller on Studio)            | Extensions to pre-install (Standard/Studio only)        |
| `SYNC_INTERVAL` | `5`                                       | Seconds between Drive pushes (persistent only)            |


`EXTENSIONS` entries are marketplace IDs (`"ms-python.python"`) or VSIX dicts (`{"vsix": "name.vsix", "url": "https://..."}`). Studio notebooks also ship EasyInstaller.

After editing a `.py` file, run `python sync_notebooks.py` to regenerate the matching notebook (extension install logic is inlined for Colab where needed).

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

Edit `.vscolabignore` in your workspace (via VS Code in Colab or at `/content/workspace/.vscolabignore`).

## Repository layout

```
vscolab/
├── vscolab_lite.ipynb                 # Lite Colab notebook (launch only)
├── vscolab_standard.ipynb             # Standard Colab notebook
├── vscolab_standard_persistent.ipynb  # Standard + Drive sync
├── vscolab_studio.ipynb               # Studio (EasyInstaller preloaded)
├── vscolab_studio_persistent.ipynb    # Studio + Drive sync
├── lite.py                            # Script source for Lite notebook
├── standard.py                        # Script source for Standard notebook
├── standard_persistent.py             # Script source for Standard Persistent
├── studio.py                          # Script source for Studio notebook
├── studio_persistent.py               # Script source for Studio Persistent
├── extensions_install.py              # Shared extension install helpers
├── sync_notebooks.py                  # Regenerate .ipynb from .py sources
└── extensions/
    └── easy-installer/                # VS Code extension for installing dev tools
```

The `.py` files mirror the notebook cells and are useful for local editing or diffing.

## EasyInstaller extension

The repo includes [EasyInstaller](extensions/easy-installer/), a VS Code sidebar extension for installing languages and tools (Python, Node.js, Rust, Go, Java, Git, and more) from the integrated terminal.

Use [vscolab_studio.ipynb](vscolab_studio.ipynb) or [vscolab_studio_persistent.ipynb](vscolab_studio_persistent.ipynb) to have it installed automatically, or install it manually after the first session. Build from source:

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
- `--without-connection-token` is used for Colab proxy access; do not expose the server outside a trusted Colab session.

## License

MIT

## NOTE

This may be against Google's terms of service. Use at your own risk; I am not liable for any account loss or data deletion caused by use of this project.
