# vscolab

Run a full VS Code UI inside [Google Colab](https://colab.research.google.com/). Optional Google Drive sync keeps your workspace across Colab sessions.

| Tier | Backend | Auth |
| ---- | ------- | ---- |
| **Lite / Standard** | [openvscode-server](https://github.com/gitpod-io/openvscode-server) + Colab `proxyPort` | None — click the printed URL |
| **AI** | Official VS Code via [Remote Tunnels](https://code.visualstudio.com/docs/remote/tunnels) → [vscode.dev](https://vscode.dev) | GitHub device login (needed for Copilot Chat + Colab LM) |

## Quick start


|              | Ephemeral                                                                                                          | **Persistent**                                                                                                                              |
| ------------ | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **Lite**     | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab_lite.ipynb)        | —                                                                                                                                           |
| **Standard** | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab_standard.ipynb)    | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab_standard_persistent.ipynb)                  |
| **AI**       | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab_ai.ipynb)          | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/vscolab_ai_persistent.ipynb)                      |


### Lite / Standard

1. Open a notebook in Colab and run all cells.
2. Authorize Google Drive if using a persistent notebook.
3. Click the **Open VS Code** Colab proxy URL.

### AI

1. Open an AI notebook and run all cells.
2. Complete the **GitHub device login** (`github.com/login/device`).
3. Open the printed **`https://vscode.dev/tunnel/...`** URL (or connect from desktop VS Code → **Remote Tunnels: Connect to Tunnel**).

## How it works

### Lite / Standard (openvscode-server)

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
(Optional) install extensions from ``EXTENSIONS``  ← Standard
       │
       ▼
Start openvscode-server (--default-folder; optional --server-data-dir)
       │
       ▼
Print Colab proxy URL
```

### AI (official VS Code tunnel)

```
Colab notebook cell
       │
       ▼
Download / cache VS Code CLI
       │
       ▼
GitHub device login
       │
       ▼
Start Colab AI bridge (google.colab.ai)
       │
       ▼
Start ``code tunnel`` (+ colab-lm VSIX)
       │
       ▼
Print vscode.dev tunnel URL
```

Official VS Code is required for the AI tier because Copilot Chat + Language Model providers need the Microsoft build. Colab’s `proxyPort` cannot carry that server’s WebSockets (error 1006), so AI uses Remote Tunnels instead.

### Lite (`vscolab_lite.ipynb` / `lite.py`)

Minimal openvscode-server launcher. No extension pre-install, no Drive sync.

### Standard (`vscolab_standard.ipynb` / `standard.py`)

openvscode-server + optional `EXTENSIONS` pre-install. No persistence.

### Standard Persistent (`vscolab_standard_persistent.ipynb` / `standard_persistent.py`)

Standard + Google Drive sync:


| Phase    | Direction  | When                                |
| -------- | ---------- | ----------------------------------- |
| **Pull** | Drive → VM | Once at startup                     |
| **Push** | VM → Drive | Every 5 seconds (background thread) |


```
MyDrive/vscolab/
├── .vscolabignore      # Sync exclude rules
├── data/               # VS Code server state (extensions, settings)
├── cache/              # Cached openvscode-server tarball
└── …                   # Your synced workspace files
```

### AI (`vscolab_ai.ipynb` / `ai.py`)

- Official VS Code via Remote Tunnels (GitHub login).
- Pre-installs **Colab AI** Language Model Chat Provider (`vscolab.colab-lm`).
- Starts `colab_lm_bridge.py` on `127.0.0.1:8787`.
- In Chat, pick **Colab AI** models (uses your Colab AI entitlement).

### AI Persistent (`vscolab_ai_persistent.ipynb` / `ai_persistent.py`)

AI tier with Drive persistence (CLI/tunnel credentials under `data/cli`).

## Configuration


| Variable        | Default                        | Purpose                                      |
| --------------- | ------------------------------ | -------------------------------------------- |
| `VERSION`       | `openvscode-server-v1.109.5`   | openvscode-server release (Lite / Standard)  |
| `TUNNEL_NAME`   | `vscolab-ai`                   | Tunnel name (AI only)                        |
| `PORT`          | `3000`                         | Colab proxy port (Lite / Standard)           |
| `GIT_REPO`      | `""`                           | Repo to clone as workspace                   |
| `EXTENSIONS`    | `[]`                           | Marketplace IDs or VSIX dicts                |
| `SYNC_INTERVAL` | `5`                            | Drive push interval (persistent only)        |


After editing a `.py` file, run `python sync_notebooks.py` to regenerate notebooks.

## Repository layout

```
vscolab/
├── lite.py / standard.py / standard_persistent.py   # openvscode-server
├── ai.py / ai_persistent.py                         # official VS Code tunnel
├── vscode_bootstrap.py                              # tunnel helpers (AI)
├── colab_lm_bridge.py                               # Colab AI HTTP bridge
├── extensions/colab-lm/                             # LM Chat Provider
├── extensions_install.py                            # openvscode extension install
└── sync_notebooks.py
```

## Requirements

- Google Colab runtime (Linux VM)
- Google Drive (persistent notebooks)
- GitHub account (**AI tier only**, for tunnel login)
- Network access to GitHub releases (openvscode) and/or Microsoft VS Code endpoints (AI)

## Limitations

- Colab VMs are ephemeral without the persistent notebooks.
- AI tier needs interactive GitHub device auth and a live Colab runtime while the tunnel is open.
- Colab AI quotas depend on your Colab plan.
- `--without-connection-token` / tunnels are for personal Colab use; do not expose them publicly.

## License

MIT (project code). Official VS Code Server (AI tier) is subject to Microsoft's license terms.

## NOTE

This may be against Google's and/or Microsoft's terms of service. Use at your own risk.
