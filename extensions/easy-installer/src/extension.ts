import * as vscode from 'vscode';
import { ToolTreeProvider, ToolTreeItem } from './providers/toolTreeProvider';
import { InstallService } from './services/installService';
import { WorkspaceDetector } from './services/workspaceDetector';
import { FileDetector } from './services/fileDetector';
import { openDashboard, refreshTools } from './views/dashboard';

const INSTALL_COMMANDS: Record<string, string> = {
  'easyInstaller.installPython': 'python',
  'easyInstaller.installPip': 'pip',
  'easyInstaller.installUv': 'uv',
  'easyInstaller.installNode': 'node',
  'easyInstaller.installNpm': 'npm',
  'easyInstaller.installNvm': 'nvm',
  'easyInstaller.installRust': 'rust',
  'easyInstaller.installCargo': 'cargo',
  'easyInstaller.installGo': 'go',
  'easyInstaller.installJava': 'java',
  'easyInstaller.installBun': 'bun',
  'easyInstaller.installGit': 'git',
};

export function activate(context: vscode.ExtensionContext): void {
  const treeProvider = new ToolTreeProvider();
  const installService = new InstallService(() => {
    treeProvider.refresh();
  });

  const treeView = vscode.window.createTreeView('easyInstaller.toolsView', {
    treeDataProvider: treeProvider,
    showCollapseAll: true,
  });

  context.subscriptions.push(treeView);

  context.subscriptions.push(
    treeView.onDidChangeVisibility((event) => {
      if (event.visible) {
        void refreshTools(treeProvider);
      }
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('easyInstaller.openDashboard', () => openDashboard()),
    vscode.commands.registerCommand('easyInstaller.refreshTools', () => refreshTools(treeProvider)),
    vscode.commands.registerCommand('easyInstaller.install', async (item?: ToolTreeItem) => {
      const toolId = resolveToolId(item);
      if (toolId) {
        await installService.installTool(toolId);
        treeProvider.refresh();
      }
    }),
    vscode.commands.registerCommand('easyInstaller.reinstall', async (item?: ToolTreeItem) => {
      const toolId = resolveToolId(item);
      if (toolId) {
        await installService.installTool(toolId);
        treeProvider.refresh();
      }
    }),
  );

  for (const [command, toolId] of Object.entries(INSTALL_COMMANDS)) {
    context.subscriptions.push(
      vscode.commands.registerCommand(command, async () => {
        await installService.installTool(toolId);
        treeProvider.refresh();
      }),
    );
  }

  const workspaceDetector = new WorkspaceDetector(installService);
  workspaceDetector.register(context);

  const fileDetector = new FileDetector(installService);
  fileDetector.register(context);

  void refreshTools(treeProvider);
}

export function deactivate(): void {}

function resolveToolId(item?: ToolTreeItem): string | undefined {
  return item?.toolId;
}
