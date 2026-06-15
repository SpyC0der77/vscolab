import * as fs from 'fs';
import * as os from 'os';
import { execFile } from 'child_process';
import { promisify } from 'util';
import { getPlatform } from '../platform/platform';

const execFileAsync = promisify(execFile);

export interface ShellResult {
  stdout: string;
  stderr: string;
  code: number;
}

function expandHome(filePath: string): string {
  if (filePath.startsWith('~/') || filePath.startsWith('~\\') || filePath === '~') {
    return os.homedir() + filePath.replace(/^~\\?/, '');
  }
  return filePath;
}

export async function runShellCommand(command: string): Promise<ShellResult> {
  const platform = getPlatform();

  try {
    if (platform === 'win32') {
      const { stdout, stderr } = await execFileAsync(
        'powershell.exe',
        ['-NoProfile', '-Command', command],
        { timeout: 15000, maxBuffer: 1024 * 1024 },
      );
      return { stdout: stdout ?? '', stderr: stderr ?? '', code: 0 };
    }

    const { stdout, stderr } = await execFileAsync('/bin/bash', ['-lc', command], {
      timeout: 15000,
      maxBuffer: 1024 * 1024,
    });
    return { stdout: stdout ?? '', stderr: stderr ?? '', code: 0 };
  } catch (error) {
    const err = error as NodeJS.ErrnoException & { stdout?: string; stderr?: string; code?: number };
    return {
      stdout: err.stdout ?? '',
      stderr: err.stderr ?? '',
      code: typeof err.code === 'number' ? err.code : 1,
    };
  }
}

export async function pathExists(filePath: string): Promise<boolean> {
  try {
    await fs.promises.access(expandHome(filePath));
    return true;
  } catch {
    return false;
  }
}

export async function commandOnPath(command: string): Promise<boolean> {
  const platform = getPlatform();
  if (platform === 'win32') {
    const result = await runShellCommand(
      `Get-Command ${command} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name`,
    );
    return result.stdout.trim().length > 0;
  }

  const result = await runShellCommand(`command -v ${command} 2>/dev/null || which ${command} 2>/dev/null`);
  return result.code === 0 && result.stdout.trim().length > 0;
}
