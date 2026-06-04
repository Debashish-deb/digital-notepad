import React, { useState } from 'react';
import { firebaseAuthEnabled, signInEmailPassword } from '../config/firebase.js';

/**
 * Email/password login for Firebase project farkki-digital-notebook.
 * Shown when VITE_FIREBASE_* is configured and auth is required.
 */
export default function AuthLoginPanel({ onToken }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  if (!firebaseAuthEnabled) {
    return (
      <p className="text-footnote">
        Firebase login not configured. Add VITE_FIREBASE_API_KEY to enable Email/Password sign-in
        (OMEIA.AI web app, project farkki-digital-notebook).
      </p>
    );
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const token = await signInEmailPassword(email, password);
      if (onToken) onToken(token);
    } catch (err) {
      setError(err.message || 'Sign-in failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="panel" onSubmit={handleSubmit} style={{ maxWidth: '24rem' }}>
      <h3 className="panel-title">Lab platform sign-in</h3>
      <p className="text-footnote" style={{ marginBottom: '1rem' }}>
        University email and password (Firebase Email/Password — not Google).
      </p>
      <div className="form-group">
        <label className="form-label">Email</label>
        <input
          type="email"
          className="form-input"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="username"
          required
        />
      </div>
      <div className="form-group">
        <label className="form-label">Password</label>
        <input
          type="password"
          className="form-input"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          required
        />
      </div>
      {error && <p className="text-footnote" style={{ color: 'var(--color-danger)' }}>{error}</p>}
      <button type="submit" className="btn btn-primary" disabled={busy}>
        {busy ? 'Signing in…' : 'Sign in'}
      </button>
    </form>
  );
}
