import * as vscode from 'vscode';
import { TOOL_CATEGORIES } from '../models/installableTool';
import { getToolsByCategory } from '../models/toolRegistry';
import { detectAllToolStatuses, getInstalledToolStatuses } from '../detectors/toolDetector';

export type TreeNodeKind = 'category' | 'tool' | 'installedSummary';

export class ToolTreeItem extends vscode.TreeItem {
  constructor(
    public readonly kind: TreeNodeKind,
    public readonly toolId: string | undefined,
    label: string,
    collapsibleState: vscode.TreeItemCollapsibleState,
    contextValue?: string,
  ) {
    super(label, collapsibleState);
    this.contextValue = contextValue;
  }
}

export class ToolTreeProvider implements vscode.TreeDataProvider<ToolTreeItem> {
  private readonly _onDidChangeTreeData = new vscode.EventEmitter<ToolTreeItem | undefined>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  refresh(): void {
    this._onDidChangeTreeData.fire(undefined);
  }

  getTreeItem(element: ToolTreeItem): vscode.TreeItem {
    return element;
  }

  async getChildren(element?: ToolTreeItem): Promise<ToolTreeItem[]> {
    if (!element) {
      return TOOL_CATEGORIES.map(
        (category) =>
          new ToolTreeItem(
            'category',
            category.id,
            category.label,
            category.id === 'installed'
              ? vscode.TreeItemCollapsibleState.Expanded
              : vscode.TreeItemCollapsibleState.Collapsed,
          ),
      );
    }

    if (element.kind !== 'category' || !element.toolId) {
      return [];
    }

    if (element.toolId === 'installed') {
      const installed = await getInstalledToolStatuses();
      if (installed.length === 0) {
        return [
          new ToolTreeItem(
            'installedSummary',
            undefined,
            'No tools installed yet',
            vscode.TreeItemCollapsibleState.None,
          ),
        ];
      }

      return installed.map((status) => {
        const item = new ToolTreeItem(
          'tool',
          status.tool.id,
          status.tool.name,
          vscode.TreeItemCollapsibleState.None,
          'easyInstaller.installed',
        );
        item.description = status.version ?? 'installed';
        item.tooltip = `${status.tool.name}\nStatus: Installed\nVersion: ${status.version ?? 'unknown'}`;
        item.iconPath = new vscode.ThemeIcon('check', new vscode.ThemeColor('charts.green'));
        item.command = {
          command: 'easyInstaller.reinstall',
          title: 'Reinstall',
          arguments: [item],
        };
        return item;
      });
    }

    const category = TOOL_CATEGORIES.find((entry) => entry.id === element.toolId);
    if (!category) {
      return [];
    }

    const statuses = await detectAllToolStatuses();
    const tools = getToolsByCategory(category.category);

    return tools.map((tool) => {
      const status = statuses.find((entry) => entry.tool.id === tool.id);
      const installed = status?.installed ?? false;
      const item = new ToolTreeItem(
        'tool',
        tool.id,
        tool.name,
        vscode.TreeItemCollapsibleState.None,
        installed ? 'easyInstaller.installed' : 'easyInstaller.notInstalled',
      );

      item.description = installed ? (status?.version ?? 'installed') : 'Not installed';
      item.tooltip = installed
        ? `${tool.name}\nStatus: Installed\nVersion: ${status?.version ?? 'unknown'}`
        : `${tool.name}\nStatus: Not installed`;
      item.iconPath = installed
        ? new vscode.ThemeIcon('check', new vscode.ThemeColor('charts.green'))
        : new vscode.ThemeIcon('circle-outline', new vscode.ThemeColor('descriptionForeground'));
      item.command = {
        command: installed ? 'easyInstaller.reinstall' : 'easyInstaller.install',
        title: installed ? 'Reinstall' : 'Install',
        arguments: [item],
      };

      return item;
    });
  }
}
