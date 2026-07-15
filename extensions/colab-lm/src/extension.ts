import * as vscode from "vscode";
import { ColabChatModelProvider } from "./provider";

export function activate(_context: vscode.ExtensionContext) {
  vscode.lm.registerLanguageModelChatProvider(
    "colab",
    new ColabChatModelProvider(),
  );
}

export function deactivate() {}
