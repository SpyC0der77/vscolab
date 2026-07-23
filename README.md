# vscolab

VS Code in [Google Colab](https://colab.research.google.com/). Persistent notebooks sync the workspace to Google Drive.


| Tier     | What you get                                      |
| -------- | ------------------------------------------------- |
| Standard | VS Code in the browser via Colab                  |
| AI       | Full VS Code + Copilot Chat with Colab AI         |

## Quick start


|          | Ephemeral                                                                                                                 | Persistent (Google Drive)                                                                                                            |
| -------- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Standard | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/notebooks/vscolab_standard.ipynb) | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/notebooks/vscolab_standard_persistent.ipynb) |
| AI       | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/notebooks/vscolab_ai.ipynb)       | [Open In Colab](https://colab.research.google.com/github/SpyC0der77/vscolab/blob/master/notebooks/vscolab_ai_persistent.ipynb)       |


Standard: run all cells, authorize Drive if asked, click the **Open VS Code** proxy URL.

AI: run all cells, finish GitHub device login (`github.com/login/device`), open the printed `https://vscode.dev/tunnel/...` link (or **Remote Tunnels: Connect to Tunnel** from desktop VS Code).

## Notebooks


| Notebook / script                                        | Notes                                                                                     |
| -------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `vscolab_standard` / `scripts/standard.py`               | openvscode-server. Optional `EXTENSIONS` pre-install (leave `[]` for none).               |
| `vscolab_standard_persistent` / `scripts/standard_persistent.py` | Standard + Drive sync (pull once at start, push every `SYNC_INTERVAL` seconds).   |
| `vscolab_ai` / `scripts/ai.py`                           | Tunnel + Colab AI bridge (`127.0.0.1:8787`) + `colab-lm` VSIX. Pick **Colab AI** in Chat. |
| `vscolab_ai_persistent` / `scripts/ai_persistent.py`     | AI + Drive sync (CLI/tunnel creds under `data/cli`).                                      |


Drive layout for persistent notebooks:

```
MyDrive/vscolab/
├── .vscolabignore   # exclude rules (VM-only paths)
├── data/            # server state (extensions, settings; AI: data/cli)
├── cache/           # cached server/CLI download
└── …                # workspace files
```

Edit a script under `scripts/`, then `python tools/sync_notebooks.py` to refresh the notebooks.

## Config

Set these at the top of the `.py` (or matching notebook cell):


| Variable        | Default                      | Used by                                                |
| --------------- | ---------------------------- | ------------------------------------------------------ |
| `VERSION`       | `openvscode-server-v1.109.5` | Standard                                               |
| `PORT`          | `3000`                       | Standard (proxy)                                       |
| `GIT_REPO`      | `""`                         | All (clone into workspace)                             |
| `EXTENSIONS`    | `[]`                         | Standard / AI (marketplace IDs or `{vsix, url}` dicts) |
| `TUNNEL_NAME`   | `vscolab-ai`                 | AI                                                     |
| `SYNC_INTERVAL` | `5`                          | Persistent                                             |


## Layout

```
vscolab/
├── notebooks/               # Colab notebooks (generated from scripts/)
├── scripts/                 # standard.py, ai.py, *_persistent.py
├── lib/                     # vscode_bootstrap, colab_lm_bridge, extensions_install
├── extensions/colab-lm/     # LM Chat Provider
└── tools/sync_notebooks.py
```

## Caveats

- Without a persistent notebook, the Colab VM is throwaway.
- AI needs a live Colab runtime for the tunnel, plus a GitHub login.
- Colab AI quotas follow your Colab plan.
- `--without-connection-token` and tunnels are for personal use. Don't publish the URL.
- This may conflict with Google's and/or Microsoft's terms. Use at your own risk.

## License

MIT for this repo. Official VS Code Server (AI tier) is under Microsoft's terms.
