import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { getApiUrl, setAuthToken, clearAuthToken } from './client.js';

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

  const onAuthToken = useCallback((token) => {
    setAuthToken(token);
    setAuthTokenState(token || null);
  }, []);

  const signOut = useCallback(() => {
    clearAuthToken();
    setAuthTokenState(null);
  }, []);

  const value = useMemo(
    () => ({
      API_URL: apiUrl,
      authToken,
      onAuthToken,
      signOut,
      isAuthenticated: Boolean(authToken),
    }),
    [apiUrl, authToken, onAuthToken, signOut],
  );

  return <ApiContext.Provider value={value}>{children}</ApiContext.Provider>;
}

export function useApiContext() {
  const ctx = useContext(ApiContext);
  if (!ctx) {
    return {
      API_URL: getApiUrl(),
      authToken: null,
      onAuthToken: setAuthToken,
      signOut: clearAuthToken,
      isAuthenticated: false,
    };
  }
  return ctx;
}
