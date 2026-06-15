export type EasyPlatform = 'linux' | 'darwin' | 'win32';

export function getPlatform(): EasyPlatform {
  if (process.platform === 'win32') {
    return 'win32';
  }
  if (process.platform === 'darwin') {
    return 'darwin';
  }
  return 'linux';
}

export function isSupportedPlatform(): boolean {
  return getPlatform() === 'linux' || getPlatform() === 'darwin' || getPlatform() === 'win32';
}

export function getPlatformLabel(): string {
  switch (getPlatform()) {
    case 'darwin':
      return 'macOS';
    case 'win32':
      return 'Windows';
    default:
      return 'Linux';
  }
}
