import * as vscode from 'vscode';
import { EasyPlatform, getPlatform } from '../platform/platform';

const LINUX_REFRESH =
  '([ -f "$HOME/.bashrc" ] && . "$HOME/.bashrc") || ([ -f /root/.bashrc ] && . /root/.bashrc) || true';

const DARWIN_REFRESH =
  '([ -f "$HOME/.zshrc" ] && . "$HOME/.zshrc") || ([ -f "$HOME/.bash_profile" ] && . "$HOME/.bash_profile") || true; command -v brew >/dev/null 2>&1 && eval "$(brew shellenv)" || true';

const WIN32_PS_REFRESH =
  "$env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User'); if (Test-Path $PROFILE) { . $PROFILE }";

function isUnixShell(shellPath?: string): boolean {
  const shell = (shellPath ?? vscode.env.shell).toLowerCase();
  return shell.includes('bash') || shell.includes('wsl') || shell.includes('/sh');
}

export function getShellRefreshCommand(platform?: EasyPlatform, shellPath?: string): string {
  const resolvedPlatform = platform ?? getPlatform();

  if (resolvedPlatform === 'win32') {
    return isUnixShell(shellPath) ? LINUX_REFRESH : WIN32_PS_REFRESH;
  }

  if (resolvedPlatform === 'darwin') {
    return DARWIN_REFRESH;
  }

  return LINUX_REFRESH;
}

export function withShellRefresh(command: string, shellPath?: string): string {
  const refresh = getShellRefreshCommand(undefined, shellPath);
  return `${command}; ${refresh}`;
}

export function refreshAllTerminals(): void {
  const refresh = getShellRefreshCommand();
  for (const terminal of vscode.window.terminals) {
    terminal.sendText(refresh, true);
  }
}
