import { InstallableTool, ToolStatus } from '../models/installableTool';
import { getAllTools } from '../models/toolRegistry';

export async function detectToolStatus(tool: InstallableTool): Promise<ToolStatus> {
  const installed = await tool.isInstalled();
  const version = installed ? await tool.getVersion() : null;
  return { tool, installed, version };
}

export async function detectAllToolStatuses(): Promise<ToolStatus[]> {
  const tools = getAllTools();
  return Promise.all(tools.map((tool) => detectToolStatus(tool)));
}

export async function getInstalledToolStatuses(): Promise<ToolStatus[]> {
  const statuses = await detectAllToolStatuses();
  return statuses.filter((status) => status.installed);
}
