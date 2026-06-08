import React, { Suspense, useState } from 'react';
import { LazyViewFallback } from '@/shared/ui/common/LazyViewFallback.jsx';
import { Dna, Microscope, ShieldCheck } from 'lucide-react';
import {
  mapFirebaseAuthError,
  registerEmailPassword,
  signInEmailPassword,
} from '@/config/firebase.js';
import { useApiContext } from '@/services/ApiContext.jsx';
import { apiPost } from '@/services/client.js';
import { saveUserProfile } from '@/lib/userProfile.js';
const LoginOvarianScene = React.lazy(() => import('@/features/auth/components/LoginOvarianScene.jsx'));
import './LoginScreen.css';

const ORGANIZATIONS = [
  { id: 'uh', label: 'University of Helsinki' },
  { id: 'farkkila', label: 'Färkkilä Lab' },
  { id: 'other', label: 'Other' },
];

function resolveOrganization(orgChoice, orgOther) {
  if (orgChoice === 'other') return orgOther.trim();
  const match = ORGANIZATIONS.find((o) => o.id === orgChoice);
  return match?.label || 'University of Helsinki';
}

function normalizeEmail(value) {
  return value.trim().toLowerCase();
}

export default function LoginScreen({ onAuthenticated }) {
  const { firebaseAuthEnabled } = useApiContext();
  const [mode, setMode] = useState('signin');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [orgChoice, setOrgChoice] = useState('uh');
  const [orgOther, setOrgOther] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);

  const switchMode = (nextMode) => {
    setMode(nextMode);
    setError(null);
    setNotice(null);
  };

  const handleSignIn = async (e) => {
    e.preventDefault();
    if (busy) return;

    setError(null);
    setNotice(null);

    const cleanedEmail = normalizeEmail(email);

    if (!cleanedEmail.includes('@')) {
      setError('Please enter a valid email address.');
      return;
    }

    if (!password) {
      setError('Please enter your password.');
      return;
    }

    setBusy(true);

    try {
      const token = await signInEmailPassword(cleanedEmail, password);
      if (onAuthenticated) onAuthenticated(token);
    } catch (err) {
      setError(mapFirebaseAuthError(err));
    } finally {
      setBusy(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    if (busy) return;

    setError(null);
    setNotice(null);

    const cleanedName = name.trim();
    const cleanedEmail = normalizeEmail(email);
    const organization = resolveOrganization(orgChoice, orgOther);

    if (!cleanedName) {
      setError('Please enter your full name.');
      return;
    }

    if (!cleanedEmail.includes('@')) {
      setError('Please enter a valid email address.');
      return;
    }

    if (orgChoice === 'other' && !orgOther.trim()) {
      setError('Please specify your organization.');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }

    setBusy(true);

    try {
      const token = await registerEmailPassword({
        email: cleanedEmail,
        password,
        displayName: cleanedName,
      });

      const reg = await apiPost('/api/auth/register-request', {
        body: {
          email: cleanedEmail,
          display_name: cleanedName,
          organization,
        },
      });

      saveUserProfile({
        name: cleanedName,
        email: cleanedEmail,
        organization,
        role: reg.role || reg.status,
      });

      if (reg.status === 'approved') {
        if (onAuthenticated) onAuthenticated(token);
        return;
      }

      setNotice(
        'Account created. Your registration is pending lab administrator approval — you will be able to sign in once approved.',
      );

      setMode('signin');
      setPassword('');
    } catch (err) {
      setError(mapFirebaseAuthError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-page__scene-wrap">
        <Suspense fallback={<LazyViewFallback variant="scene-3d" label="Loading scene…" showBars={false} />}>
          <LoginOvarianScene />
        </Suspense>

        <div className="login-page__brand">
          <p className="login-page__brand-eyebrow">
            <Dna size={14} aria-hidden="true" />
            Systems Oncology · Spatial HGSC Research
          </p>

          <h1 className="login-page__brand-title">
            Färkkilä Lab Digital Research NotePad
          </h1>

          <p className="login-page__brand-lead">
            Secure workspace for ovarian cancer spatial biology, multi-omics pipelines,
            and lab knowledge — HGSC-focused computational and wet-lab research at the
            University of Helsinki.
          </p>

          <div className="login-page__brand-pills" aria-hidden="true">
            <span>
              <Microscope size={13} />
              Spatial biology
            </span>
            <span>
              <Dna size={13} />
              HGSC atlas
            </span>
            <span>
              <ShieldCheck size={13} />
              Lab secure
            </span>
          </div>
        </div>
      </div>

      <div className="login-page__panel-wrap">
        <div className="login-card">
          {!firebaseAuthEnabled ? (
            <div className="login-card__disabled">
              <div className="login-card__orb">
                <ShieldCheck size={24} aria-hidden="true" />
              </div>

              <h2 className="login-card__title">Authentication is not configured</h2>

              <p className="login-message login-message--info">
                Firebase is not configured. Add <code>VITE_FIREBASE_API_KEY</code> to enable
                email sign-in, or set <code>PLATFORM_AUTH_DISABLED=true</code> for local
                development without login.
              </p>
            </div>
          ) : (
            <>
              <header className="login-card__header">
                <div className="login-card__orb" aria-hidden="true">
                  <Microscope size={23} />
                </div>

                <p className="login-card__kicker">Private lab access</p>

                <h2 className="login-card__title">
                  {mode === 'signin' ? 'Sign in to the lab platform' : 'Create your lab account'}
                </h2>

                <p className="login-card__subtitle">
                  University email and password via Firebase — not Google Sign-In.
                </p>
              </header>

              <div className="login-mode-tabs" role="tablist" aria-label="Authentication mode">
                <button
                  type="button"
                  id="login-tab-signin"
                  role="tab"
                  aria-selected={mode === 'signin'}
                  aria-controls="login-auth-form"
                  className={`login-mode-tab${mode === 'signin' ? ' login-mode-tab--active' : ''}`}
                  onClick={() => switchMode('signin')}
                >
                  Sign in
                </button>

                <button
                  type="button"
                  id="login-tab-register"
                  role="tab"
                  aria-selected={mode === 'register'}
                  aria-controls="login-auth-form"
                  className={`login-mode-tab${mode === 'register' ? ' login-mode-tab--active' : ''}`}
                  onClick={() => switchMode('register')}
                >
                  Create account
                </button>
              </div>

              <form
                id="login-auth-form"
                className="login-form"
                onSubmit={mode === 'signin' ? handleSignIn : handleRegister}
              >
                {mode === 'register' && (
                  <div className="login-field">
                    <label htmlFor="login-name">Full name</label>
                    <input
                      id="login-name"
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      autoComplete="name"
                      required
                      placeholder="Debashish Deb"
                      disabled={busy}
                    />
                  </div>
                )}

                <div className="login-field">
                  <label htmlFor="login-email">Email</label>
                  <input
                    id="login-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="username"
                    required
                    placeholder="name@helsinki.fi"
                    disabled={busy}
                  />
                </div>

                {mode === 'register' && (
                  <>
                    <div className="login-field">
                      <label htmlFor="login-org">Organization</label>
                      <select
                        id="login-org"
                        value={orgChoice}
                        onChange={(e) => setOrgChoice(e.target.value)}
                        disabled={busy}
                        required
                      >
                        {ORGANIZATIONS.map((org) => (
                          <option key={org.id} value={org.id}>
                            {org.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    {orgChoice === 'other' && (
                      <div className="login-field">
                        <label htmlFor="login-org-other">Organization name</label>
                        <input
                          id="login-org-other"
                          type="text"
                          value={orgOther}
                          onChange={(e) => setOrgOther(e.target.value)}
                          placeholder="Institute or company name"
                          disabled={busy}
                          required
                        />
                      </div>
                    )}
                  </>
                )}

                <div className="login-field">
                  <label htmlFor="login-password">Password</label>
                  <input
                    id="login-password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
                    required
                    minLength={mode === 'register' ? 8 : undefined}
                    disabled={busy}
                  />
                </div>

                <div className="login-status-region" aria-live="polite">
                  {error && <p className="login-message login-message--error">{error}</p>}
                  {notice && <p className="login-message login-message--success">{notice}</p>}
                </div>

                <button type="submit" className="login-submit" disabled={busy}>
                  <span className="login-submit__glow" aria-hidden="true" />
                  <span>
                    {busy
                      ? mode === 'signin'
                        ? 'Signing in…'
                        : 'Creating account…'
                      : mode === 'signin'
                        ? 'Sign in'
                        : 'Create account'}
                  </span>
                </button>
              </form>

              <p className="login-footnote">
                Passwords are stored securely by Firebase Authentication — never on this
                application server. Platform admins are approved automatically; other accounts
                require lab allowlist approval.
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}