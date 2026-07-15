# vscolab

Run [official VS Code](https://code.visualstudio.com/docs/remote/tunnels) inside [Google Colab](https://colab.research.google.com/) via **Remote Tunnels**, then open the workbench on [vscode.dev](https://vscode.dev) (or desktop VS Code). Optional Google Drive sync keeps your workspace across Colab sessions.

> **Why tunnels?** Colab’s `proxyPort` cannot reliably carry WebSocket upgrades for Microsoft’s VS Code web server (browser error **1006**). Remote Tunnels is Microsoft’s supported path.

## Quick start


|              | Ephemeral                                                                                                          | **Persistent**                                                                                                                              |
| ------------ | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **Lite**     | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab_lite.ipynb)        | —                                                                                                                                           |
| **Standard** | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab_standard.ipynb)    | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab_standard_persistent.ipynb)                  |
| **AI**       | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab_ai.ipynb)          | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab_ai_persistent.ipynb)                      |


1. Open a notebook in Colab.
2. Run all cells.
3. When prompted, authorize Google Drive (persistent notebook only).
4. Complete the **GitHub device login** printed in the cell output (`github.com/login/device`).
5. Open the printed **`https://vscode.dev/tunnel/...`** URL (or connect from desktop VS Code → **Remote Tunnels: Connect to Tunnel**).

## How it works

```
Colab notebook cell
       │
       ▼
Download / cache VS Code CLI
       │
       ▼
(Optional) Drive mount + workspace sync  ← Persistent
       │
       ▼
GitHub device login (code tunnel user login)
       │
       ▼
(Optional) start Colab AI bridge  ← AI
       │
       ▼
Start ``code tunnel`` (+ optional --install-extension)
       │
       ▼
Print vscode.dev tunnel URL
```

### Lite (`vscolab_lite.ipynb` / `lite.py`)

Minimal launcher — CLI download, login, tunnel, print URL.

### Standard (`vscolab_standard.ipynb` / `standard.py`)

Same as Lite, plus optional `EXTENSIONS` pre-install when the tunnel starts.

### Standard Persistent (`vscolab_standard_persistent.ipynb` / `standard_persistent.py`)

Adds Drive sync. Tunnel credentials under `MyDrive/vscolab/data/cli` can persist across sessions.


| Phase    | Direction  | When                                |
| -------- | ---------- | ----------------------------------- |
| **Pull** | Drive → VM | Once at startup                     |
| **Push** | VM → Drive | Every 5 seconds (background thread) |


```
MyDrive/vscolab/
├── .vscolabignore      # Sync exclude rules
├── data/               # VS Code CLI data (tunnel auth, etc.)
├── cache/              # Cached CLI tarball
└── …                   # Your synced workspace files
```

### AI (`vscolab_ai.ipynb` / `ai.py`)

Standard + Colab AI:

- Pre-installs **Colab AI** Language Model Chat Provider (`vscolab.colab-lm`).
- Starts `colab_lm_bridge.py` on `127.0.0.1:8787` (reachable from the remote extension host on the Colab VM).
- Official VS Code includes Copilot Chat; pick **Colab AI** models in the Chat model picker.

### AI Persistent (`vscolab_ai_persistent.ipynb` / `ai_persistent.py`)

AI tier with Drive persistence.

## Configuration


| Variable        | Default              | Purpose                                      |
| --------------- | -------------------- | -------------------------------------------- |
| `TUNNEL_NAME`   | `vscolab` / `vscolab-ai` | Tunnel name shown in vscode.dev / Remote Tunnels |
| `GIT_REPO`      | `""`                 | Repo to clone as workspace                   |
| `EXTENSIONS`    | `[]`                 | Marketplace IDs or VSIX dicts to pre-install |
| `SYNC_INTERVAL` | `5`                  | Drive push interval (persistent only)        |


After editing a `.py` file, run `python sync_notebooks.py` to regenerate notebooks.

## Repository layout

```
vscolab/
├── vscode_bootstrap.py                # VS Code CLI + tunnel helpers
├── colab_lm_bridge.py                 # Colab AI HTTP bridge
├── extensions/colab-lm/               # Language Model Chat Provider
├── lite.py / standard.py / ai.py / *_persistent.py
├── sync_notebooks.py
└── vscolab_*.ipynb
```

## Requirements

- Google Colab runtime (Linux VM)
- GitHub account (tunnel device login)
- Network access to Microsoft VS Code download / tunnel endpoints
- Google Drive (persistent notebooks)

## Limitations

- First run requires interactive GitHub device authorization.
- Keep the Colab cell/runtime alive while using the tunnel.
- Colab AI quotas depend on your Colab plan.
- Official VS Code Server [license](https://aka.ms/vscode-server-license) applies; intended for personal use.

## License

MIT (project code). Official VS Code Server is subject to Microsoft's license terms.

## NOTE

This may be against Google's and/or Microsoft's terms of service. Use at your own risk.
