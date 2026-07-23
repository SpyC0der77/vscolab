import * as vscode from "vscode";
import { BridgeClient } from "./bridgeClient";
import { ColabChatModelProvider } from "./provider";
import { BridgeStatusBar } from "./statusBar";

export function activate(context: vscode.ExtensionContext) {
  vscode.lm.registerLanguageModelChatProvider(
    "colab",
    new ColabChatModelProvider(),
  );

  const statusBar = new BridgeStatusBar();
  statusBar.start();
  context.subscriptions.push(statusBar);

  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("colabLm.bridgeUrl")) {
        void statusBar.refresh();
      }
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("colabLm.manage", async () => {
      const config = vscode.workspace.getConfiguration("colabLm");
      const baseUrl = config
        .get<string>("bridgeUrl", "http://127.0.0.1:8787")
        .replace(/\/$/, "");
      const client = new BridgeClient(baseUrl);
      const healthy = await client.health();
      void statusBar.refresh();
      if (!healthy) {
        await vscode.window.showWarningMessage(
          `Colab AI bridge is not reachable at ${baseUrl}. Run the vscolab AI notebook cell first.`,
        );
        return;
      }
      const models = await client.listModels();
      const names = models.map((m) => m.name).join(", ") || "(none)";
      await vscode.window.showInformationMessage(
        `Colab AI bridge OK at ${baseUrl}. Models: ${names}`,
      );
    }),
  );
}

export function deactivate() {}
