import { InstallableTool } from '../models/installableTool';
import { runInTerminal } from '../installers/terminalInstaller';
import { commandOnPath, pathExists, runShellCommand } from '../detectors/shellRunner';
import {
  TOOL_RECIPES,
  getPlatformSpec,
  getToolDependencies,
} from '../platform/installRecipes';
import { getPlatform } from '../platform/platform';

function parseVersion(output: string): string {
  return output.trim().split('\n')[0]?.trim() ?? '';
}

export function getTool(id: string): InstallableTool | undefined {
  const recipe = TOOL_RECIPES.find((entry) => entry.id === id);
  if (!recipe) {
    return undefined;
  }

  const platform = getPlatform();
  const spec = getPlatformSpec(recipe, platform);

  return {
    id: recipe.id,
    name: recipe.name,
    category: recipe.category,
    dependencies: getToolDependencies(recipe, platform),

    async isInstalled(): Promise<boolean> {
      for (const cmd of spec.whichCommands) {
        if (await commandOnPath(cmd)) {
          return true;
        }
      }

      if (spec.extraPaths) {
        for (const p of spec.extraPaths) {
          if (await pathExists(p)) {
            return true;
          }
        }
      }

      return false;
    },

    async getVersion(): Promise<string | null> {
      if (!(await this.isInstalled())) {
        return null;
      }

      const result = await runShellCommand(spec.versionCommand);
      if (result.code !== 0 && !result.stdout && !result.stderr) {
        return null;
      }

      const version = parseVersion(result.stdout || result.stderr);
      return version || null;
    },

    async install(): Promise<void> {
      runInTerminal(recipe.name, spec.installCommand);
    },
  };
}

export function getAllTools(): InstallableTool[] {
  return TOOL_RECIPES.map((recipe) => getTool(recipe.id)!);
}

export function getToolsByCategory(category: InstallableTool['category']): InstallableTool[] {
  return getAllTools().filter((tool) => tool.category === category);
}

export function getToolDisplayName(id: string): string {
  return getTool(id)?.name ?? id;
}
