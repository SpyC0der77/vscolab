import { ToolCategory } from '../models/installableTool';
import { EasyPlatform } from './platform';

export interface PlatformSpec {
  whichCommands: string[];
  extraPaths?: string[];
  versionCommand: string;
  installCommand: string;
}

export interface ToolRecipe {
  id: string;
  name: string;
  category: ToolCategory;
  dependencies: string[];
  linux: PlatformSpec;
  darwin: PlatformSpec;
  win32: PlatformSpec;
}

const NVM_SOURCE =
  'export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && \\. "$NVM_DIR/nvm.sh"';

const WINGET =
  'winget install --accept-package-agreements --accept-source-agreements -e --id';

export const TOOL_RECIPES: ToolRecipe[] = [
  {
    id: 'python',
    name: 'Python',
    category: 'language',
    dependencies: [],
    linux: {
      whichCommands: ['python3'],
      versionCommand: 'python3 --version 2>&1',
      installCommand: 'sudo apt update && sudo apt install -y python3',
    },
    darwin: {
      whichCommands: ['python3', 'python'],
      versionCommand: 'python3 --version 2>&1',
      installCommand: 'brew install python',
    },
    win32: {
      whichCommands: ['python', 'py'],
      versionCommand: 'python --version 2>&1',
      installCommand: `${WINGET} Python.Python.3.12`,
    },
  },
  {
    id: 'node',
    name: 'Node.js',
    category: 'language',
    dependencies: ['nvm'],
    linux: {
      whichCommands: ['node'],
      versionCommand: 'node --version 2>&1',
      installCommand: `${NVM_SOURCE} && nvm install --lts`,
    },
    darwin: {
      whichCommands: ['node'],
      versionCommand: 'node --version 2>&1',
      installCommand: `${NVM_SOURCE} && nvm install --lts`,
    },
    win32: {
      whichCommands: ['node'],
      versionCommand: 'node --version 2>&1',
      installCommand: `${WINGET} OpenJS.NodeJS.LTS`,
    },
  },
  {
    id: 'go',
    name: 'Go',
    category: 'language',
    dependencies: [],
    linux: {
      whichCommands: ['go'],
      versionCommand: 'go version 2>&1',
      installCommand: 'sudo apt update && sudo apt install -y golang-go',
    },
    darwin: {
      whichCommands: ['go'],
      versionCommand: 'go version 2>&1',
      installCommand: 'brew install go',
    },
    win32: {
      whichCommands: ['go'],
      versionCommand: 'go version 2>&1',
      installCommand: `${WINGET} GoLang.Go`,
    },
  },
  {
    id: 'rust',
    name: 'Rust',
    category: 'language',
    dependencies: [],
    linux: {
      whichCommands: ['rustc'],
      versionCommand: 'rustc --version 2>&1',
      installCommand: "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y",
    },
    darwin: {
      whichCommands: ['rustc'],
      versionCommand: 'rustc --version 2>&1',
      installCommand: "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y",
    },
    win32: {
      whichCommands: ['rustc'],
      versionCommand: 'rustc --version 2>&1',
      installCommand:
        'Invoke-WebRequest -Uri https://win.rustup.rs/x86_64 -OutFile $env:TEMP\\rustup-init.exe; & $env:TEMP\\rustup-init.exe -y',
    },
  },
  {
    id: 'java',
    name: 'Java',
    category: 'language',
    dependencies: [],
    linux: {
      whichCommands: ['java'],
      versionCommand: 'java -version 2>&1',
      installCommand: 'sudo apt update && sudo apt install -y default-jdk',
    },
    darwin: {
      whichCommands: ['java'],
      versionCommand: 'java -version 2>&1',
      installCommand: 'brew install openjdk',
    },
    win32: {
      whichCommands: ['java'],
      versionCommand: 'java -version 2>&1',
      installCommand: `${WINGET} Microsoft.OpenJDK.21`,
    },
  },
  {
    id: 'uv',
    name: 'uv',
    category: 'packageManager',
    dependencies: ['python'],
    linux: {
      whichCommands: ['uv'],
      extraPaths: ['$HOME/.local/bin/uv', '$HOME/.cargo/bin/uv'],
      versionCommand: 'uv --version 2>&1',
      installCommand: 'curl -LsSf https://astral.sh/uv/install.sh | sh',
    },
    darwin: {
      whichCommands: ['uv'],
      extraPaths: ['$HOME/.local/bin/uv', '$HOME/.cargo/bin/uv'],
      versionCommand: 'uv --version 2>&1',
      installCommand: 'curl -LsSf https://astral.sh/uv/install.sh | sh',
    },
    win32: {
      whichCommands: ['uv'],
      extraPaths: ['$HOME/.local/bin/uv.exe', '$HOME/.cargo/bin/uv.exe'],
      versionCommand: 'uv --version 2>&1',
      installCommand: 'irm https://astral.sh/uv/install.ps1 | iex',
    },
  },
  {
    id: 'pip',
    name: 'pip',
    category: 'packageManager',
    dependencies: ['python'],
    linux: {
      whichCommands: ['pip3', 'pip'],
      versionCommand: 'pip3 --version 2>&1 || pip --version 2>&1',
      installCommand: 'sudo apt update && sudo apt install -y python3-pip',
    },
    darwin: {
      whichCommands: ['pip3', 'pip'],
      versionCommand: 'pip3 --version 2>&1 || pip --version 2>&1',
      installCommand: 'python3 -m ensurepip --upgrade',
    },
    win32: {
      whichCommands: ['pip', 'pip3'],
      versionCommand: 'pip --version 2>&1',
      installCommand: 'python -m ensurepip --upgrade',
    },
  },
  {
    id: 'npm',
    name: 'npm',
    category: 'packageManager',
    dependencies: ['node'],
    linux: {
      whichCommands: ['npm'],
      versionCommand: 'npm --version 2>&1',
      installCommand: `${NVM_SOURCE} && nvm install --lts`,
    },
    darwin: {
      whichCommands: ['npm'],
      versionCommand: 'npm --version 2>&1',
      installCommand: `${NVM_SOURCE} && nvm install --lts`,
    },
    win32: {
      whichCommands: ['npm'],
      versionCommand: 'npm --version 2>&1',
      installCommand: `${WINGET} OpenJS.NodeJS.LTS`,
    },
  },
  {
    id: 'cargo',
    name: 'Cargo',
    category: 'packageManager',
    dependencies: ['rust'],
    linux: {
      whichCommands: ['cargo'],
      versionCommand: 'cargo --version 2>&1',
      installCommand: "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y",
    },
    darwin: {
      whichCommands: ['cargo'],
      versionCommand: 'cargo --version 2>&1',
      installCommand: "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y",
    },
    win32: {
      whichCommands: ['cargo'],
      versionCommand: 'cargo --version 2>&1',
      installCommand:
        'Invoke-WebRequest -Uri https://win.rustup.rs/x86_64 -OutFile $env:TEMP\\rustup-init.exe; & $env:TEMP\\rustup-init.exe -y',
    },
  },
  {
    id: 'bun',
    name: 'Bun',
    category: 'packageManager',
    dependencies: [],
    linux: {
      whichCommands: ['bun'],
      extraPaths: ['$HOME/.bun/bin/bun'],
      versionCommand: 'bun --version 2>&1',
      installCommand: 'curl -fsSL https://bun.sh/install | bash',
    },
    darwin: {
      whichCommands: ['bun'],
      extraPaths: ['$HOME/.bun/bin/bun'],
      versionCommand: 'bun --version 2>&1',
      installCommand: 'curl -fsSL https://bun.sh/install | bash',
    },
    win32: {
      whichCommands: ['bun'],
      extraPaths: ['$HOME/.bun/bin/bun.exe'],
      versionCommand: 'bun --version 2>&1',
      installCommand: 'irm bun.sh/install.ps1 | iex',
    },
  },
  {
    id: 'nvm',
    name: 'NVM',
    category: 'packageManager',
    dependencies: [],
    linux: {
      whichCommands: ['nvm'],
      extraPaths: ['$HOME/.nvm/nvm.sh'],
      versionCommand: `${NVM_SOURCE} && nvm --version 2>&1`,
      installCommand: 'curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/master/install.sh | bash',
    },
    darwin: {
      whichCommands: ['nvm'],
      extraPaths: ['$HOME/.nvm/nvm.sh'],
      versionCommand: `${NVM_SOURCE} && nvm --version 2>&1`,
      installCommand: 'curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/master/install.sh | bash',
    },
    win32: {
      whichCommands: ['nvm'],
      extraPaths: ['$APPDATA/nvm/nvm.exe'],
      versionCommand: 'nvm version 2>&1',
      installCommand: `${WINGET} CoreyButler.NVMforWindows`,
    },
  },
  {
    id: 'git',
    name: 'Git',
    category: 'tool',
    dependencies: [],
    linux: {
      whichCommands: ['git'],
      versionCommand: 'git --version 2>&1',
      installCommand: 'sudo apt update && sudo apt install -y git',
    },
    darwin: {
      whichCommands: ['git'],
      versionCommand: 'git --version 2>&1',
      installCommand: 'brew install git',
    },
    win32: {
      whichCommands: ['git'],
      versionCommand: 'git --version 2>&1',
      installCommand: `${WINGET} Git.Git`,
    },
  },
];

export function getPlatformSpec(recipe: ToolRecipe, platform: EasyPlatform): PlatformSpec {
  return recipe[platform];
}

export function getToolDependencies(recipe: ToolRecipe, platform: EasyPlatform): string[] {
  if (recipe.id === 'node' && platform === 'win32') {
    return [];
  }
  return recipe.dependencies;
}
