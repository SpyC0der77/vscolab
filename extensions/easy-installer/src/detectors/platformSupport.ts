import { assertPlatformSupported } from './platformDetector';
import { getPlatformLabel, isSupportedPlatform } from '../platform/platform';

export async function assertInstallEnvironment(restrictUbuntuOnly: boolean): Promise<boolean> {
  return assertPlatformSupported(restrictUbuntuOnly);
}

export function getUnsupportedPlatformMessage(restrictUbuntuOnly: boolean): string {
  if (restrictUbuntuOnly) {
    return 'EasyInstaller is configured for Ubuntu Linux only. Disable easyInstaller.supportedUbuntuOnly to use EasyInstaller on this system.';
  }

  if (!isSupportedPlatform()) {
    return `EasyInstaller does not support this environment (${getPlatformLabel()}). Install commands may not work as expected.`;
  }

  return `EasyInstaller on ${getPlatformLabel()} may require Homebrew (macOS) or winget (Windows) in your PATH.`;
}

export async function isInstallEnvironmentReady(): Promise<boolean> {
  const { getConfig } = await import('../utils/config');
  const config = getConfig();
  return assertInstallEnvironment(config.supportedUbuntuOnly);
}
