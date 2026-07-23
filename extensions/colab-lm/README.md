# Colab AI

VS Code Language Model Chat Provider that talks to `google.colab.ai` through the vscolab bridge (`lib/colab_lm_bridge.py` on `127.0.0.1:8787`).

You get this for free when you run an [AI-tier vscolab notebook](https://github.com/SpyC0der77/vscolab). The notebook starts the bridge and installs this VSIX into the tunnel session. In Chat, pick a **Colab AI** model.

## Requirements

- Official VS Code (Remote Tunnels / vscode.dev), not openvscode-server
- Bridge running: `http://127.0.0.1:8787` (started by `scripts/ai.py` / `scripts/ai_persistent.py`)
- A Colab runtime with AI access

## Settings

| Setting | Default | What it does |
| ------- | ------- | ------------ |
| `colabLm.bridgeUrl` | `http://127.0.0.1:8787` | Bridge base URL |

Command palette: **Colab AI: Show Bridge Status**

Status bar (bottom left): **Colab AI** — green check when the bridge is up, warning when not. Click for details.

## Develop

```bash
cd extensions/colab-lm
bun install
bun run compile
bun run package
```

That writes `colab-lm-0.2.6.vsix`. The AI notebooks pull the committed copy from this repo.
