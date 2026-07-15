# vscolab

Run [openvscode-server](https://github.com/gitpod-io/openvscode-server) inside [Google Colab](https://colab.research.google.com/) and edit code in a full VS Code UI in a new browser tab. Optional Google Drive sync keeps your workspace across Colab sessions.

## Quick start


|              | Ephemeral                                                                                                          | **Persistent**                                                                                                                              |
| ------------ | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **Lite**     | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab_lite.ipynb)        | —                                                                                                                                           |
| **Standard** | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab_standard.ipynb)    | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab_standard_persistent.ipynb)                  |
| **AI**       | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab_ai.ipynb)          | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab_ai_persistent.ipynb)                      |


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
(Optional) install extensions from ``EXTENSIONS``  ← Standard / AI variants
       │
       ▼
(Optional) start Colab AI bridge  ← AI variants
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

### AI (`vscolab_ai.ipynb` / `ai.py`)

Replaces the former Studio tier. Everything in Standard, plus:

- Pre-installs the **Colab AI** Language Model Chat Provider extension (`vscolab.colab-lm`).
- Starts a localhost bridge (`colab_lm_bridge.py`) that wraps `google.colab.ai` — no API key required.
- VS Code Chat can use Colab Gemini models via the model picker (vendor: **Colab AI**).

Available models and quotas depend on your Colab plan and `google.colab.ai` entitlements.

### AI Persistent (`vscolab_ai_persistent.ipynb` / `ai_persistent.py`)

AI tier with the same Google Drive persistence as Standard Persistent.

## Configuration

Edit the constants at the top of the notebook (or script):


| Variable        | Default                                   | Purpose                                                   |
| --------------- | ----------------------------------------- | --------------------------------------------------------- |
| `VERSION`       | `openvscode-server-v1.109.5`              | Server release to download                                |
| `PORT`          | `3000`                                    | Port for the Colab proxy URL                              |
| `GIT_REPO`      | `""`                                      | Repo to clone as workspace; uses `/content/workspace` when empty |
| `EXTENSIONS`    | `[]`                                      | Extensions to pre-install (Standard / AI only)            |
| `SYNC_INTERVAL` | `5`                                       | Seconds between Drive pushes (persistent only)            |


`EXTENSIONS` entries are marketplace IDs (`"ms-python.python"`) or VSIX dicts (`{"vsix": "name.vsix", "url": "https://..."}`).

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
├── vscolab_ai.ipynb                   # AI tier (Colab Gemini via LM provider)
├── vscolab_ai_persistent.ipynb        # AI tier + Drive sync
├── lite.py                            # Script source for Lite notebook
├── standard.py                        # Script source for Standard notebook
├── standard_persistent.py             # Script source for Standard Persistent
├── ai.py                              # Script source for AI notebook
├── ai_persistent.py                   # Script source for AI Persistent
├── colab_lm_bridge.py                 # Colab AI HTTP bridge for the extension
├── extensions/
│   └── colab-lm/                      # Language Model Chat Provider extension
├── extensions_install.py              # Shared extension install helpers
└── sync_notebooks.py                  # Regenerate .ipynb from .py sources
```

The `.py` files mirror the notebook cells and are useful for local editing or diffing.

## Requirements

- Google Colab runtime (Linux VM)
- Google account with Drive access (persistent notebook)
- Network access to GitHub releases (openvscode-server download)

## Limitations

- Colab VMs are ephemeral; without the persistent notebook, all local changes are lost on disconnect.
- Background sync is push-only after the initial pull — edits made directly on Drive while a session is running may be overwritten on the next push.
- Large folders (e.g. `node_modules`, `.git`) should stay in `.vscolabignore` to avoid slow syncs and Drive quota use.
- Colab AI models are subject to Google Colab plan limits and may change without notice.
- `--without-connection-token` is used for Colab proxy access; do not expose the server outside a trusted Colab session.

## License

MIT

## NOTE

This may be against Google's terms of service. Use at your own risk; I am not liable for any account loss or data deletion caused by use of this project.
