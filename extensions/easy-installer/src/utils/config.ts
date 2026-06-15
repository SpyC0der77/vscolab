import * as vscode from 'vscode';

export interface EasyInstallerConfig {
  enableWorkspaceDetection: boolean;
  enableFileDetection: boolean;
  askBeforeInstall: boolean;
  supportedUbuntuOnly: boolean;
  dismissedFileExtensions: string[];
  ignoredWorkspaceSuggestions: string[];
}

export function getConfig(): EasyInstallerConfig {
  const config = vscode.workspace.getConfiguration('easyInstaller');
  return {
    enableWorkspaceDetection: config.get<boolean>('enableWorkspaceDetection', true),
    enableFileDetection: config.get<boolean>('enableFileDetection', true),
    askBeforeInstall: config.get<boolean>('askBeforeInstall', true),
    supportedUbuntuOnly: config.get<boolean>('supportedUbuntuOnly', false),
    dismissedFileExtensions: config.get<string[]>('dismissedFileExtensions', []),
    ignoredWorkspaceSuggestions: config.get<string[]>('ignoredWorkspaceSuggestions', []),
  };
}

export async function addDismissedFileExtension(extension: string): Promise<void> {
  const config = vscode.workspace.getConfiguration('easyInstaller');
  const current = config.get<string[]>('dismissedFileExtensions', []);
  if (current.includes(extension)) {
    return;
  }
  await config.update('dismissedFileExtensions', [...current, extension], vscode.ConfigurationTarget.Global);
}

export async function addIgnoredWorkspaceSuggestion(key: string): Promise<void> {
  const config = vscode.workspace.getConfiguration('easyInstaller');
  const current = config.get<string[]>('ignoredWorkspaceSuggestions', []);
  if (current.includes(key)) {
    return;
  }
  await config.update('ignoredWorkspaceSuggestions', [...current, key], vscode.ConfigurationTarget.Global);
}
