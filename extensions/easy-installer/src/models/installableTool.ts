export type ToolCategory = 'language' | 'packageManager' | 'tool';

export interface InstallableTool {
  id: string;
  name: string;
  category: ToolCategory;
  dependencies: string[];
  isInstalled(): Promise<boolean>;
  getVersion(): Promise<string | null>;
  install(): Promise<void>;
}

export interface ToolStatus {
  tool: InstallableTool;
  installed: boolean;
  version: string | null;
}

export interface ToolCategoryGroup {
  id: string;
  label: string;
  category: ToolCategory;
}

export const TOOL_CATEGORIES: ToolCategoryGroup[] = [
  { id: 'languages', label: 'Languages', category: 'language' },
  { id: 'packageManagers', label: 'Package Managers', category: 'packageManager' },
  { id: 'tools', label: 'Tools', category: 'tool' },
  { id: 'installed', label: 'Installed Tools', category: 'tool' },
];
