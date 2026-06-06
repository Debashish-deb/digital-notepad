/**
 * Firebase web app OMEIA.AI — npm SDK (Console also shows CDN 12.14.0; we use npm only).
 * See configs/FIREBASE_WEB_SETUP.md for full firebaseConfig + CDN reference.
 * measurementId (G-24JLFQYRTG) is optional per Firebase; Auth does not require it.
 * Auth: Email/Password only (no Google Sign-In for lab users).
 */
import { initializeApp, getApps } from 'firebase/app';
import {
  getAuth,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  updateProfile,
  signOut,
  onAuthStateChanged,
} from 'firebase/auth';
import { getApiUrl } from '../api/client.js';

const DEFAULTS = {
  authDomain: 'farkki-digital-notebook.firebaseapp.com',
  projectId: 'farkki-digital-notebook',
  storageBucket: 'farkki-digital-notebook.firebasestorage.app',
  messagingSenderId: '570069536455',
  appId: '1:570069536455:web:4c4623a81262e6c4eef8e2',
  measurementId: 'G-24JLFQYRTG',
};

function configFromViteEnv() {
  return {
    apiKey: import.meta.env.VITE_FIREBASE_API_KEY || '',
    authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || DEFAULTS.authDomain,
    projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || DEFAULTS.projectId,
    storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || DEFAULTS.storageBucket,
    messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || DEFAULTS.messagingSenderId,
    appId: import.meta.env.VITE_FIREBASE_APP_ID || DEFAULTS.appId,
    measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID || DEFAULTS.measurementId,
  };
}

function configFromApiPayload(fb) {
  if (!fb?.api_key) return null;
  return {
    apiKey: fb.api_key,
    authDomain: fb.auth_domain || DEFAULTS.authDomain,
    projectId: fb.project_id || DEFAULTS.projectId,
    storageBucket: fb.storage_bucket || DEFAULTS.storageBucket,
    messagingSenderId: fb.messaging_sender_id || DEFAULTS.messagingSenderId,
    appId: fb.app_id || DEFAULTS.appId,
    measurementId: fb.measurement_id || DEFAULTS.measurementId,
  };
}

/** Same shape as Firebase Console → Project settings → Your apps → OMEIA.AI */
export let firebaseConfig = configFromViteEnv();

let _resolvePromise = null;

/** Resolve Firebase web config from Vite env, then /api/auth/config as fallback. */
export async function resolveFirebaseConfig() {
  if (_resolvePromise) return _resolvePromise;

  _resolvePromise = (async () => {
    let config = configFromViteEnv();
    if (!config.apiKey) {
      try {
        const res = await fetch(`${getApiUrl()}/api/auth/config`, { signal: AbortSignal.timeout(8_000) });
        if (res.ok) {
          const data = await res.json();
          const fromApi = configFromApiPayload(data?.firebase);
          if (fromApi) config = fromApi;
        }
      } catch {
        // API unreachable — keep env-only config
      }
    }
    firebaseConfig = config;
    return config;
  })();

  return _resolvePromise;
}

export function isFirebaseAuthEnabled() {
  return Boolean(firebaseConfig.apiKey);
}

/** @deprecated Use isFirebaseAuthEnabled() after resolveFirebaseConfig(); kept for static imports. */
export const firebaseAuthEnabled = isFirebaseAuthEnabled();

export function mapFirebaseAuthError(err) {
  const code = err?.code || '';
  switch (code) {
    case 'auth/invalid-credential':
    case 'auth/wrong-password':
    case 'auth/user-not-found':
      return (
        'Incorrect email or password. Create an account first if you are new, or reset your ' +
        'password in Firebase Console. This platform uses email/password only — not Google Sign-In.'
      );
    case 'auth/too-many-requests':
      return 'Too many failed attempts. Wait a few minutes and try again.';
    case 'auth/user-disabled':
      return 'This account has been disabled. Contact the lab administrator.';
    case 'auth/invalid-email':
      return 'Please enter a valid email address.';
    case 'auth/email-already-in-use':
      return 'This email is already registered. Try signing in instead.';
    case 'auth/weak-password':
      return 'Password is too weak. Use at least 8 characters.';
    case 'auth/operation-not-allowed':
      return (
        'Email/password sign-in is not enabled for this Firebase project. ' +
        'Enable it under Firebase Console → Authentication → Sign-in method.'
      );
    default:
      if (typeof err?.message === 'string' && err.message.includes('auth/invalid-credential')) {
        return mapFirebaseAuthError({ code: 'auth/invalid-credential' });
      }
      return err?.message || 'Sign-in failed';
  }
}

export function getFirebaseApp() {
  if (!isFirebaseAuthEnabled()) return null;
  return getApps().length ? getApps()[0] : initializeApp(firebaseConfig);
}

export function getFirebaseAuth() {
  const app = getFirebaseApp();
  return app ? getAuth(app) : null;
}

/** Optional — mirrors `getAnalytics(app)` from console snippet. */
export async function initFirebaseAnalytics() {
  await resolveFirebaseConfig();
  if (!firebaseConfig.measurementId || typeof window === 'undefined') return null;
  const app = getFirebaseApp();
  if (!app) return null;
  try {
    const { getAnalytics, isSupported } = await import('firebase/analytics');
    if (!(await isSupported())) return null;
    return getAnalytics(app);
  } catch {
    return null;
  }
}

export async function signInEmailPassword(email, password) {
  await resolveFirebaseConfig();
  const auth = getFirebaseAuth();
  if (!auth) throw new Error('Firebase not configured (set VITE_FIREBASE_API_KEY or start the API)');
  const cred = await signInWithEmailAndPassword(auth, email.trim(), password);
  return cred.user.getIdToken();
}

export async function registerEmailPassword({ email, password, displayName }) {
  await resolveFirebaseConfig();
  const auth = getFirebaseAuth();
  if (!auth) throw new Error('Firebase not configured (set VITE_FIREBASE_API_KEY or start the API)');
  const cred = await createUserWithEmailAndPassword(auth, email.trim(), password);
  if (displayName?.trim()) {
    await updateProfile(cred.user, { displayName: displayName.trim() });
  }
  return cred.user.getIdToken();
}

export async function refreshIdToken() {
  const auth = getFirebaseAuth();
  const user = auth?.currentUser;
  if (!user) return null;
  return user.getIdToken(true);
}

export async function signOutFirebase() {
  const auth = getFirebaseAuth();
  if (auth) await signOut(auth);
}

export function subscribeAuth(callback) {
  const auth = getFirebaseAuth();
  if (!auth) {
    callback(null);
    return () => {};
  }
  return onAuthStateChanged(auth, callback);
}
