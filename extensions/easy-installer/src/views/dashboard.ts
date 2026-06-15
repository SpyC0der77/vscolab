import * as vscode from 'vscode';
import { ToolTreeProvider } from '../providers/toolTreeProvider';
import { detectAllToolStatuses } from '../detectors/toolDetector';
import { isInstallEnvironmentReady } from '../detectors/platformSupport';
import { getPlatformLabel } from '../platform/platform';
import { refreshAllTerminals } from '../utils/shellRefresh';

export async function refreshTools(treeProvider: ToolTreeProvider): Promise<void> {
  const supported = await isInstallEnvironmentReady();

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: 'EasyInstaller: Detecting installed tools...',
      cancellable: false,
    },
    async () => {
      if (!supported) {
        vscode.window.showWarningMessage(
          `EasyInstaller: This system (${getPlatformLabel()}) may not match the configured platform restrictions. Detection may be inaccurate.`,
        );
      }
      await detectAllToolStatuses();
    },
  );

  refreshAllTerminals();
  treeProvider.refresh();
  vscode.window.showInformationMessage('EasyInstaller: Tool detection complete.');
}

export async function openDashboard(): Promise<void> {
  await vscode.commands.executeCommand('workbench.view.extension.easyInstaller');
}
