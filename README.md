# vscolab

Run [official VS Code](https://code.visualstudio.com/) (`server-linux-x64-web`) inside [Google Colab](https://colab.research.google.com/) and edit code in a full VS Code UI in a new browser tab. Optional Google Drive sync keeps your workspace across Colab sessions.

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

All notebooks bootstrap the official **VS Code web server** (`server-linux-x64-web` / `code-server`) on port `3000` and expose it with Colab's `google.colab.kernel.proxyPort()`.

```
Colab notebook cell
       │
       ▼
Download / cache official VS Code web server
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
Start ``code-server`` (user-data-dir; folder via --default-folder / ?folder=)
       │
       ▼
Print Colab proxy URL to open VS Code in a new tab
```

### Lite (`vscolab_lite.ipynb` / `lite.py`)

Minimal launcher — download web server, start it, print proxy URL. No extension pre-install, no Drive sync.

### Standard (`vscolab_standard.ipynb` / `standard.py`)

- Downloads and caches the official VS Code web server (Microsoft build).
- Optionally clones a git repo into `/content/<repo-name>`; otherwise uses `/content/workspace`.
- Pre-installs any entries in `EXTENSIONS` (empty by default) from the Microsoft Marketplace / VSIX.
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
├── data/               # VS Code user data (extensions, settings)
├── cache/              # Cached VS Code web server tarballs
└── …                   # Your synced workspace files
```

### AI (`vscolab_ai.ipynb` / `ai.py`)

Everything in Standard, plus:

- Official VS Code web already includes **GitHub Copilot Chat** (built-in) — no separate install.
- Pre-installs the **Colab AI** Language Model Chat Provider (`vscolab.colab-lm`).
- Starts a localhost bridge (`colab_lm_bridge.py`) that wraps `google.colab.ai` — no API key required.
- In Chat, pick a **Colab AI** model from the model picker (you may still see a Copilot sign-in prompt for other features; Colab models use your Colab entitlement).

Available models and quotas depend on your Colab plan and `google.colab.ai` entitlements.

### AI Persistent (`vscolab_ai_persistent.ipynb` / `ai_persistent.py`)

AI tier with the same Google Drive persistence as Standard Persistent.

## Configuration

Edit the constants at the top of the notebook (or script):


| Variable        | Default                                   | Purpose                                                   |
| --------------- | ----------------------------------------- | --------------------------------------------------------- |
| `COMMIT`        | `""` (latest stable)                      | Pin a VS Code commit hash, or leave empty for latest      |
| `PORT`          | `3000`                                    | Port for the Colab proxy URL                              |
| `GIT_REPO`      | `""`                                      | Repo to clone as workspace; uses `/content/workspace` when empty |
| `EXTENSIONS`    | `[]`                                      | Extensions to pre-install (Standard / AI only)            |
| `SYNC_INTERVAL` | `5`                                       | Seconds between Drive pushes (persistent only)            |


`EXTENSIONS` entries are marketplace IDs (`"ms-python.python"`) or VSIX dicts (`{"vsix": "name.vsix", "url": "https://..."}`).

After editing a `.py` file, run `python sync_notebooks.py` to regenerate the matching notebook (shared helpers are inlined for Colab where needed).

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
├── vscode_bootstrap.py                # Official VS Code web server helpers
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
- Network access to Microsoft VS Code download / update endpoints

## Limitations

- Colab VMs are ephemeral; without the persistent notebook, all local changes are lost on disconnect.
- Background sync is push-only after the initial pull — edits made directly on Drive while a session is running may be overwritten on the next push.
- Large folders (e.g. `node_modules`, `.git`) should stay in `.vscolabignore` to avoid slow syncs and Drive quota use.
- Colab AI models are subject to Google Colab plan limits and may change without notice.
- `--without-connection-token` is used for Colab proxy access; do not expose the server outside a trusted Colab session.
- Official VS Code Server [license](https://aka.ms/vscode-server-license) does not allow hosting it as a multi-user service; this project is intended for personal Colab use.

## License

MIT (project code). Official VS Code Server is subject to Microsoft's license terms.

## NOTE

This may be against Google's and/or Microsoft's terms of service. Use at your own risk; I am not liable for any account loss or data deletion caused by use of this project.
