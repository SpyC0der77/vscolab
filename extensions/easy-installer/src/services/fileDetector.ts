import * as vscode from 'vscode';
import { detectToolStatus } from '../detectors/toolDetector';
import { getTool } from '../models/toolRegistry';
import { addDismissedFileExtension, getConfig } from '../utils/config';
import { InstallService } from './installService';

interface FileMapping {
  extensions: string[];
  toolId: string;
  runtimeName: string;
}

const FILE_MAPPINGS: FileMapping[] = [
  { extensions: ['.py'], toolId: 'python', runtimeName: 'Python' },
  { extensions: ['.js', '.ts'], toolId: 'node', runtimeName: 'Node.js' },
  { extensions: ['.rs'], toolId: 'rust', runtimeName: 'Rust' },
  { extensions: ['.go'], toolId: 'go', runtimeName: 'Go' },
  { extensions: ['.java'], toolId: 'java', runtimeName: 'Java' },
];

export class FileDetector {
  private readonly notifiedExtensions = new Set<string>();

  constructor(private readonly installService: InstallService) {}

  register(context: vscode.ExtensionContext): void {
    context.subscriptions.push(
      vscode.window.onDidChangeActiveTextEditor((editor) => {
        if (editor) {
          void this.handleEditor(editor);
        }
      }),
      vscode.workspace.onDidOpenTextDocument((document) => {
        void this.handleDocument(document);
      }),
    );

    if (vscode.window.activeTextEditor) {
      void this.handleEditor(vscode.window.activeTextEditor);
    }
  }

  private async handleEditor(editor: vscode.TextEditor): Promise<void> {
    await this.handleDocument(editor.document);
  }

  private async handleDocument(document: vscode.TextDocument): Promise<void> {
    const config = getConfig();
    if (!config.enableFileDetection) {
      return;
    }

    const extension = this.getExtension(document.fileName);
    if (!extension) {
      return;
    }

    if (config.dismissedFileExtensions.includes(extension)) {
      return;
    }

    if (this.notifiedExtensions.has(extension)) {
      return;
    }

    const mapping = FILE_MAPPINGS.find((entry) => entry.extensions.includes(extension));
    if (!mapping) {
      return;
    }

    const tool = getTool(mapping.toolId);
    if (!tool) {
      return;
    }

    const status = await detectToolStatus(tool);
    if (status.installed) {
      return;
    }

    this.notifiedExtensions.add(extension);

    const choice = await vscode.window.showWarningMessage(
      `EasyInstaller: ${mapping.runtimeName} file detected but ${mapping.runtimeName} is not installed.`,
      'Install',
      'Dismiss',
      "Don't Ask Again",
    );

    if (choice === 'Install') {
      await this.installService.installTool(mapping.toolId);
    } else if (choice === "Don't Ask Again") {
      await addDismissedFileExtension(extension);
    }
  }

  private getExtension(fileName: string): string | undefined {
    const index = fileName.lastIndexOf('.');
    if (index === -1) {
      return undefined;
    }
    return fileName.slice(index).toLowerCase();
  }
}
