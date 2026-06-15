import * as vscode from 'vscode';
import { InstallableTool } from '../models/installableTool';
import { getTool, getToolDisplayName } from '../models/toolRegistry';
import { assertInstallEnvironment, getUnsupportedPlatformMessage } from '../detectors/platformSupport';
import { getPlatform } from '../platform/platform';
import { detectToolStatus } from '../detectors/toolDetector';
import { getConfig } from '../utils/config';

export class InstallService {
  constructor(private readonly onInstalled?: () => void) {}

  async installTool(toolId: string, options?: { skipConfirm?: boolean }): Promise<boolean> {
    const tool = getTool(toolId);
    if (!tool) {
      vscode.window.showErrorMessage(`EasyInstaller: Unknown tool "${toolId}".`);
      return false;
    }

    const config = getConfig();
    const supported = await assertInstallEnvironment(config.supportedUbuntuOnly);
    if (!supported) {
      vscode.window.showWarningMessage(getUnsupportedPlatformMessage(config.supportedUbuntuOnly));
      return false;
    }

    const missingDependencies = await this.getMissingDependencies(tool);
    if (missingDependencies.length > 0) {
      const dependencyNames = missingDependencies.map((dep) => getToolDisplayName(dep.id)).join(', ');
      const choice = await vscode.window.showWarningMessage(
        `${tool.name} requires ${dependencyNames}. Install ${dependencyNames} first?`,
        'Install Dependencies',
        'Cancel',
      );

      if (choice !== 'Install Dependencies') {
        return false;
      }

      for (const dependency of missingDependencies) {
        const installed = await this.installTool(dependency.id, { skipConfirm: true });
        if (!installed) {
          return false;
        }
      }
    }

    if (tool.id === 'node' && getPlatform() !== 'win32') {
      const nvmStatus = await detectToolStatus(getTool('nvm')!);
      if (!nvmStatus.installed) {
        const choice = await vscode.window.showWarningMessage(
          'Node.js is installed via NVM. NVM is not installed. Install NVM first?',
          'Install NVM',
          'Cancel',
        );
        if (choice !== 'Install NVM') {
          return false;
        }
        await this.installTool('nvm', { skipConfirm: true });
      }
    }

    if (tool.id === 'cargo') {
      const rustStatus = await detectToolStatus(getTool('rust')!);
      if (!rustStatus.installed) {
        const choice = await vscode.window.showInformationMessage(
          'Cargo is installed automatically with Rust. Install Rust?',
          'Install Rust',
          'Cancel',
        );
        if (choice !== 'Install Rust') {
          return false;
        }
        return this.installTool('rust', options);
      }
    }

    if (config.askBeforeInstall && !options?.skipConfirm) {
      const confirm = await vscode.window.showInformationMessage(
        `Install ${tool.name} in a terminal?`,
        'Install',
        'Cancel',
      );
      if (confirm !== 'Install') {
        return false;
      }
    }

    try {
      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: `EasyInstaller: Installing ${tool.name}...`,
          cancellable: false,
        },
        async () => {
          await tool.install();
        },
      );

      vscode.window.showInformationMessage(
        `EasyInstaller: ${tool.name} installation started in the terminal. The shell will refresh when it finishes; use Refresh Tools to update detection.`,
      );
      this.onInstalled?.();
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      vscode.window.showErrorMessage(`EasyInstaller: Failed to install ${tool.name}. ${message}`);
      return false;
    }
  }

  async installMany(toolIds: string[]): Promise<void> {
    for (const toolId of toolIds) {
      await this.installTool(toolId);
    }
  }

  private async getMissingDependencies(tool: InstallableTool): Promise<InstallableTool[]> {
    const missing: InstallableTool[] = [];

    for (const dependencyId of tool.dependencies) {
      const dependency = getTool(dependencyId);
      if (!dependency) {
        continue;
      }

      const status = await detectToolStatus(dependency);
      if (!status.installed) {
        missing.push(dependency);
      }
    }

    return missing;
  }
}
