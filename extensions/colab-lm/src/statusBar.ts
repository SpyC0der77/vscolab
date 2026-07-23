import * as vscode from "vscode";
import { BridgeClient } from "./bridgeClient";

const POLL_MS = 15_000;

export class BridgeStatusBar implements vscode.Disposable {
  private readonly item: vscode.StatusBarItem;
  private timer: ReturnType<typeof setInterval> | undefined;
  private disposed = false;

  constructor() {
    this.item = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left,
      50,
    );
    this.item.command = "colabLm.manage";
    this.item.text = "$(loading~spin) Colab AI";
    this.item.tooltip = "Checking Colab AI bridge…";
    this.item.show();
  }

  start() {
    void this.refresh();
    this.timer = setInterval(() => void this.refresh(), POLL_MS);
  }

  async refresh() {
    if (this.disposed) {
      return;
    }
    const config = vscode.workspace.getConfiguration("colabLm");
    const baseUrl = config
      .get<string>("bridgeUrl", "http://127.0.0.1:8787")
      .replace(/\/$/, "");
    const healthy = await new BridgeClient(baseUrl).health();
    if (this.disposed) {
      return;
    }
    if (healthy) {
      this.item.text = "$(check) Colab AI";
      this.item.tooltip = `Bridge OK at ${baseUrl}\nClick for details`;
      this.item.backgroundColor = undefined;
    } else {
      this.item.text = "$(warning) Colab AI";
      this.item.tooltip = `Bridge not reachable at ${baseUrl}\nRun the vscolab AI notebook cell, then click for details`;
      this.item.backgroundColor = new vscode.ThemeColor(
        "statusBarItem.warningBackground",
      );
    }
  }

  dispose() {
    this.disposed = true;
    if (this.timer) {
      clearInterval(this.timer);
    }
    this.item.dispose();
  }
}
