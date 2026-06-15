import * as fs from 'fs';
import { runShellCommand } from './shellRunner';

export async function isUbuntuLinux(): Promise<boolean> {
  if (process.platform !== 'linux') {
    return false;
  }

  try {
    const content = fs.readFileSync('/etc/os-release', 'utf8');
    return (
      /(^|\n)ID=ubuntu(\n|$)/m.test(content) ||
      /ID_LIKE=.*ubuntu/.test(content) ||
      /(^|\n)ID=debian(\n|$)/m.test(content) ||
      /ID_LIKE=.*debian/.test(content)
    );
  } catch {
    const result = await runShellCommand(
      'grep -Eqi "ubuntu|debian" /etc/os-release 2>/dev/null && echo yes || echo no',
    );
    return result.stdout.trim() === 'yes';
  }
}

export async function assertUbuntuSupported(supportedUbuntuOnly: boolean): Promise<boolean> {
  if (!supportedUbuntuOnly) {
    return true;
  }

  return isUbuntuLinux();
}
