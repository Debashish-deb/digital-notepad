import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { apiFetch, getApiUrl, setAuthToken, clearAuthToken } from './client.js';
import {
  isFirebaseAuthEnabled,
  resolveFirebaseConfig,
  subscribeAuth,
  signOutFirebase,
} from '../config/firebase.js';
import { getUserProfile, clearUserProfile } from '../utils/userProfile.js';
import {
  clearAuthSkipActive,
  isAuthSkipActive,
  setAuthSkipActive,
} from '../utils/authSkip.js';

const ApiContext = createContext(null);

export function ApiProvider({ children }) {
  const [apiUrl] = useState(getApiUrl);
  const [authToken, setAuthTokenState] = useState(() => {
    try {
      return window.localStorage.getItem('farkki_id_token');
    } catch {
      return null;
    }
  });
  const [authUser, setAuthUser] = useState(null);
  const [userProfile, setUserProfile] = useState(() => getUserProfile());
  const [authConfigLoaded, setAuthConfigLoaded] = useState(false);
  const [firebaseAuthEnabled, setFirebaseAuthEnabled] = useState(isFirebaseAuthEnabled());
  const [firebaseAuthChecked, setFirebaseAuthChecked] = useState(false);
  const [authDisabled, setAuthDisabled] = useState(false);
  const [authAllowSkip, setAuthAllowSkip] = useState(false);
  const [authSkipped, setAuthSkipped] = useState(() => isAuthSkipActive());

  const authReady = authConfigLoaded && firebaseAuthChecked;

  useEffect(() => {
    let cancelled = false;
    apiFetch('/api/auth/config', { timeoutMs: 8_000 })
      .then((cfg) => {
        if (cancelled) return;
        setAuthDisabled(Boolean(cfg?.auth_disabled));
        setAuthAllowSkip(Boolean(cfg?.auth_allow_skip));
        if (!cfg?.auth_allow_skip && isAuthSkipActive()) {
          clearAuthSkipActive();
          setAuthSkipped(false);
        }
      })
      .catch(() => {
        // Config unreachable — treat as auth required (no dev bypass).
      })
      .finally(() => {
        if (!cancelled) setAuthConfigLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    let unsubscribe = () => {};

    resolveFirebaseConfig()
      .then(() => {
        if (cancelled) return;
        const enabled = isFirebaseAuthEnabled();
        setFirebaseAuthEnabled(enabled);
        if (!enabled) {
          setFirebaseAuthChecked(true);
          return;
        }
        unsubscribe = subscribeAuth((user) => {
          // Unblock the UI immediately; token refresh can lag when the API was down on first paint.
          setFirebaseAuthChecked(true);
          if (user) {
            clearAuthSkipActive();
            setAuthSkipped(false);
            void (async () => {
              try {
                const token = await user.getIdToken();
                setAuthToken(token);
                setAuthTokenState(token);
                setAuthUser({
                  uid: user.uid,
                  email: user.email,
                  displayName: user.displayName,
                });
              } catch {
                clearAuthToken();
                setAuthTokenState(null);
                setAuthUser(null);
              }
            })();
          } else if (!isAuthSkipActive()) {
            clearAuthToken();
            setAuthTokenState(null);
            setAuthUser(null);
          }
        });
      })
      .catch(() => {
        if (!cancelled) setFirebaseAuthChecked(true);
      });

    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, []);

  const onAuthToken = useCallback((token) => {
    setAuthToken(token);
    setAuthTokenState(token || null);
  }, []);

  const setProfile = useCallback((profile) => {
    setUserProfile(profile);
  }, []);

  const skipAuth = useCallback(() => {
    setAuthSkipActive();
    setAuthSkipped(true);
  }, []);

  const signOut = useCallback(async () => {
    try {
      await signOutFirebase();
    } catch {
      // ignore
    }
    clearAuthSkipActive();
    setAuthSkipped(false);
    clearAuthToken();
    clearUserProfile();
    setAuthTokenState(null);
    setAuthUser(null);
    setUserProfile(null);
  }, []);

  const isAuthenticated =
    authDisabled || Boolean(authToken) || (authAllowSkip && authSkipped);

  const value = useMemo(
    () => ({
      API_URL: apiUrl,
      authToken,
      authUser,
      userProfile,
      authReady,
      firebaseAuthEnabled,
      authDisabled,
      authAllowSkip,
      authSkipped,
      skipAuth,
      onAuthToken,
      setProfile,
      signOut,
      isAuthenticated,
    }),
    [
      apiUrl,
      authToken,
      authUser,
      userProfile,
      authReady,
      firebaseAuthEnabled,
      authDisabled,
      authAllowSkip,
      authSkipped,
      skipAuth,
      onAuthToken,
      setProfile,
      signOut,
      isAuthenticated,
    ],
  );

  return <ApiContext.Provider value={value}>{children}</ApiContext.Provider>;
}

export function useApiContext() {
  const ctx = useContext(ApiContext);
  if (!ctx) {
    return {
      API_URL: getApiUrl(),
      authToken: null,
      authUser: null,
      userProfile: null,
      authReady: true,
      firebaseAuthEnabled: false,
      authDisabled: true,
      authAllowSkip: false,
      authSkipped: false,
      skipAuth: () => {},
      onAuthToken: setAuthToken,
      setProfile: () => {},
      signOut: clearAuthToken,
      isAuthenticated: true,
    };
  }
  return ctx;
}
