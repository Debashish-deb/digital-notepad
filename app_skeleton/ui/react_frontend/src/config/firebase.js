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
  signOut,
  onAuthStateChanged,
} from 'firebase/auth';

/** Same shape as Firebase Console → Project settings → Your apps → OMEIA.AI */
export const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || '',
  authDomain:
    import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || 'farkki-digital-notebook.firebaseapp.com',
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || 'farkki-digital-notebook',
  storageBucket:
    import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || 'farkki-digital-notebook.firebasestorage.app',
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || '570069536455',
  appId: import.meta.env.VITE_FIREBASE_APP_ID || '1:570069536455:web:4c4623a81262e6c4eef8e2',
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID || 'G-24JLFQYRTG',
};

export const firebaseAuthEnabled = Boolean(firebaseConfig.apiKey);

export function getFirebaseApp() {
  if (!firebaseAuthEnabled) return null;
  return getApps().length ? getApps()[0] : initializeApp(firebaseConfig);
}

export function getFirebaseAuth() {
  const app = getFirebaseApp();
  return app ? getAuth(app) : null;
}

/** Optional — mirrors `getAnalytics(app)` from console snippet. */
export async function initFirebaseAnalytics() {
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
  const auth = getFirebaseAuth();
  if (!auth) throw new Error('Firebase not configured (set VITE_FIREBASE_API_KEY)');
  const cred = await signInWithEmailAndPassword(auth, email.trim(), password);
  return cred.user.getIdToken();
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
