# EasyInstaller

EasyInstaller is a Visual Studio Code extension for **Linux, macOS, and Windows** that lets you install programming languages, package managers, and developer tools directly from a graphical sidebar.

## Features

- **Activity Bar sidebar** with categorized tools: Languages, Package Managers, Tools, and Installed Tools
- **Installation detection** using PATH lookup and version commands
- **Dependency resolution** with confirmation dialogs (e.g. uv requires Python)
- **Terminal-based installs** — every install runs in a visible VS Code terminal
- **Workspace detection** for `requirements.txt`, `package.json`, `Cargo.toml`, and more
- **File detection** when opening `.py`, `.js`, `.ts`, `.rs`, `.go`, and `.java` files
- **Command palette** commands for each supported tool
- **Configurable behavior** via VS Code settings

## Supported Tools

| Category | Tools |
|----------|-------|
| Languages | Python, Node.js, Go, Rust, Java |
| Package Managers | uv, pip, npm, cargo, bun, NVM |
| Tools | Git |

## Requirements

- Linux (Ubuntu/Debian via apt), macOS (via Homebrew), or Windows (via winget)
- VS Code 1.85+
- Admin access when required (`sudo` on Linux, elevated winget on Windows)
- Network access for script-based installs

## Getting Started

```bash
cd extensions/easy-installer
bun install
bun run compile
```

### Run in Extension Development Host

1. Open the `extensions/easy-installer` folder in VS Code
2. Press `F5` to launch the Extension Development Host
3. Click the **EasyInstaller** icon in the Activity Bar

### Package

```bash
bun add -d @vscode/vsce
bun run package
```

## Commands

| Command | Description |
|---------|-------------|
| `EasyInstaller: Open Dashboard` | Focus the EasyInstaller sidebar |
| `EasyInstaller: Refresh Tools` | Re-detect installed tools and versions |
| `EasyInstaller: Install Python` | Install Python (apt / Homebrew / winget) |
| `EasyInstaller: Install pip` | Install pip |
| `EasyInstaller: Install uv` | Install uv via install script |
| `EasyInstaller: Install Node.js` | Install Node.js LTS (NVM on Linux/macOS, winget on Windows) |
| `EasyInstaller: Install npm` | Install npm (via Node.js) |
| `EasyInstaller: Install NVM` | Install NVM (Linux/macOS) or nvm-windows |
| `EasyInstaller: Install Rust` | Install Rust via rustup |
| `EasyInstaller: Install Cargo` | Install Cargo (via Rust) |
| `EasyInstaller: Install Go` | Install Go (apt / Homebrew / winget) |
| `EasyInstaller: Install Java` | Install Java (apt / Homebrew / winget) |
| `EasyInstaller: Install Bun` | Install Bun via install script |
| `EasyInstaller: Install Git` | Install Git (apt / Homebrew / winget) |

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `easyInstaller.enableWorkspaceDetection` | `true` | Suggest tools based on workspace files |
| `easyInstaller.enableFileDetection` | `true` | Notify when opening files without runtimes |
| `easyInstaller.askBeforeInstall` | `true` | Confirm before launching install commands |
| `easyInstaller.supportedUbuntuOnly` | `false` | When enabled, restrict installs to Ubuntu/Debian Linux only |
| `easyInstaller.dismissedFileExtensions` | `[]` | Extensions suppressed by "Don't Ask Again" |
| `easyInstaller.ignoredWorkspaceSuggestions` | `[]` | Workspace markers ignored via "Ignore" |

## Project Structure

```
src/
  extension.ts          # Activation and command registration
  models/               # InstallableTool interface and registry
  platform/               # OS detection and per-platform install recipes
  detectors/            # Platform, shell, and tool detection
  installers/           # Terminal-based installation
  providers/            # TreeDataProvider for sidebar
  services/             # Install, workspace, and file detection
  views/                # Dashboard helpers
  utils/                # Configuration helpers
```

## Notes

- Node.js is installed through **NVM** on Linux and macOS. On Windows, **winget** is used instead.
- **Cargo** is installed automatically with Rust.
- After terminal installs complete, click **Refresh Tools** or reopen the sidebar to update versions.
- Installs that require `sudo` may prompt for your password in the integrated terminal.

## License

MIT
