import * as vscode from 'vscode';
import { detectToolStatus } from '../detectors/toolDetector';
import { getTool, getToolDisplayName } from '../models/toolRegistry';
import { addIgnoredWorkspaceSuggestion, getConfig } from '../utils/config';
import { InstallService } from './installService';

interface WorkspaceSuggestion {
  key: string;
  markerFile: string;
  label: string;
  toolIds: string[];
}

const WORKSPACE_SUGGESTIONS: WorkspaceSuggestion[] = [
  {
    key: 'requirements.txt',
    markerFile: 'requirements.txt',
    label: 'Python',
    toolIds: ['python', 'pip'],
  },
  {
    key: 'pyproject.toml',
    markerFile: 'pyproject.toml',
    label: 'Python',
    toolIds: ['python', 'uv'],
  },
  {
    key: 'package.json',
    markerFile: 'package.json',
    label: 'Node.js',
    toolIds: ['node', 'npm'],
  },
  {
    key: 'Cargo.toml',
    markerFile: 'Cargo.toml',
    label: 'Rust',
    toolIds: ['rust', 'cargo'],
  },
  {
    key: 'go.mod',
    markerFile: 'go.mod',
    label: 'Go',
    toolIds: ['go'],
  },
  {
    key: 'pom.xml',
    markerFile: 'pom.xml',
    label: 'Java',
    toolIds: ['java'],
  },
  {
    key: 'bun.lock',
    markerFile: 'bun.lock',
    label: 'Bun',
    toolIds: ['bun'],
  },
  {
    key: 'bun.lockb',
    markerFile: 'bun.lockb',
    label: 'Bun',
    toolIds: ['bun'],
  },
];

export class WorkspaceDetector {
  private readonly prompted = new Set<string>();

  constructor(private readonly installService: InstallService) {}

  register(context: vscode.ExtensionContext): void {
    context.subscriptions.push(
      vscode.workspace.onDidChangeWorkspaceFolders(() => {
        void this.scanAll();
      }),
    );

    void this.scanAll();
  }

  private async scanAll(): Promise<void> {
    const config = getConfig();
    if (!config.enableWorkspaceDetection) {
      return;
    }

    for (const folder of vscode.workspace.workspaceFolders ?? []) {
      await this.scanFolder(folder);
    }
  }

  private async scanFolder(folder: vscode.WorkspaceFolder): Promise<void> {
    const config = getConfig();
    if (!config.enableWorkspaceDetection) {
      return;
    }

    for (const suggestion of WORKSPACE_SUGGESTIONS) {
      if (config.ignoredWorkspaceSuggestions.includes(suggestion.key)) {
        continue;
      }

      const promptKey = `${folder.uri.fsPath}:${suggestion.key}`;
      if (this.prompted.has(promptKey)) {
        continue;
      }

      const markerUri = vscode.Uri.joinPath(folder.uri, suggestion.markerFile);
      let exists = false;
      try {
        await vscode.workspace.fs.stat(markerUri);
        exists = true;
      } catch {
        exists = false;
      }

      if (!exists) {
        continue;
      }

      const missingToolIds: string[] = [];
      for (const toolId of suggestion.toolIds) {
        const tool = getTool(toolId);
        if (!tool) {
          continue;
        }
        const status = await detectToolStatus(tool);
        if (!status.installed) {
          missingToolIds.push(toolId);
        }
      }

      if (missingToolIds.length === 0) {
        continue;
      }

      this.prompted.add(promptKey);
      const missingNames = missingToolIds.map((id) => getToolDisplayName(id)).join(' and ');
      const choice = await vscode.window.showWarningMessage(
        `EasyInstaller: ${suggestion.label} project detected. ${missingNames} ${missingToolIds.length > 1 ? 'are' : 'is'} not installed.`,
        'Install',
        'Ignore',
      );

      if (choice === 'Install') {
        await this.installService.installMany(missingToolIds);
      } else if (choice === 'Ignore') {
        await addIgnoredWorkspaceSuggestion(suggestion.key);
      }
    }
  }
}
