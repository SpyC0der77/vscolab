# Colab AI

Language Model Chat Provider for VS Code that routes chat requests to `google.colab.ai` via the vscolab Colab AI bridge.

## Development

```bash
cd extensions/colab-lm
bun install
bun run compile
bun run package
```

The packaged VSIX is committed at `colab-lm-0.1.0.vsix` for pre-install in the AI tier notebooks.
