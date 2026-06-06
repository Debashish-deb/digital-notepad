/** Testing-period bypass — only when backend sets PLATFORM_AUTH_ALLOW_SKIP=true */

export const AUTH_SKIP_STORAGE_KEY = 'farkki_auth_test_skip';
export const AUTH_SKIP_HEADER_VALUE = 'testing';

export function isAuthSkipActive() {
  try {
    return window.localStorage.getItem(AUTH_SKIP_STORAGE_KEY) === '1';
  } catch {
    return false;
  }
}

export function setAuthSkipActive() {
  try {
    window.localStorage.setItem(AUTH_SKIP_STORAGE_KEY, '1');
  } catch {
    // ignore
  }
}

export function clearAuthSkipActive() {
  try {
    window.localStorage.removeItem(AUTH_SKIP_STORAGE_KEY);
  } catch {
    // ignore
  }
}
