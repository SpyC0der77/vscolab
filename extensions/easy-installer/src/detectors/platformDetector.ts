import { isSupportedPlatform } from '../platform/platform';
import { isUbuntuLinux } from './ubuntuDetector';

export async function assertPlatformSupported(restrictUbuntuOnly: boolean): Promise<boolean> {
  if (!isSupportedPlatform()) {
    return false;
  }

  if (restrictUbuntuOnly) {
    return isUbuntuLinux();
  }

  return true;
}
