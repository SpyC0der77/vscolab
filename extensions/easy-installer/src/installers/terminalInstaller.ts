import * as vscode from 'vscode';
import { withShellRefresh } from '../utils/shellRefresh';

export function runInTerminal(label: string, command: string): void {
  const terminal = vscode.window.createTerminal({
    name: `EasyInstaller: ${label}`,
    hideFromUser: false,
  });
  terminal.show(true);
  terminal.sendText(withShellRefresh(command), true);
}
