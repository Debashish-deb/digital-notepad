import { useEffect, useMemo, useState } from 'react';
import { LogIn, LogOut, ShieldAlert, User } from 'lucide-react';
import AuthLoginPanel from '@/features/auth/components/AuthLoginPanel.jsx';
import { useApiContext } from '@/services/ApiContext.jsx';
import { Award, BookOpen, Briefcase, Code, ExternalLink, Link, Mail } from 'lucide-react';
import { userProfilesData } from '@/data/userProfilesData.js';
import './UserProfileScreen.css';

function resolveProfileKey(email = '') {
  const normalized = email.trim().toLowerCase();
  if (!normalized) return null;
  return (
    Object.keys(userProfilesData).find(
      (key) => userProfilesData[key].email?.toLowerCase() === normalized,
    ) || null
  );
}

export default function UserProfileScreen() {
  const {
    authUser,
    userProfile,
    authToken,
    firebaseAuthEnabled,
    authDisabled,
    onAuthToken,
    signOut,
  } = useApiContext();

  const loggedInEmail = authUser?.email || userProfile?.email || '';
  const isSignedIn = Boolean(authToken || authUser);
  const matchedUserKey = useMemo(() => resolveProfileKey(loggedInEmail), [loggedInEmail]);
  const [browseUserKey, setBrowseUserKey] = useState(matchedUserKey || Object.keys(userProfilesData)[0]);

  useEffect(() => {
    if (matchedUserKey) setBrowseUserKey(matchedUserKey);
  }, [matchedUserKey]);

  const selectedUserKey = isSignedIn && matchedUserKey ? matchedUserKey : browseUserKey;
  const selectedProfile = userProfilesData[selectedUserKey];

  return (
    <div className="profile-container">
      <section className="profile-auth-card">
        <div className="profile-auth-card__header">
          <h3 className="profile-auth-card__title">
            {isSignedIn ? 'Signed in' : 'Lab account'}
          </h3>
          <p className="profile-auth-card__status">
            {isSignedIn
              ? (authUser?.email || userProfile?.email || 'Authenticated')
              : authDisabled
                ? 'Authentication is optional in this environment (PLATFORM_AUTH_DISABLED).'
                : 'You are not signed in. Use your university email and password to access your profile.'}
          </p>
        </div>

        {isSignedIn ? (
          <div className="profile-auth-card__actions">
            <span className="profile-auth-card__email">{authUser?.email || userProfile?.email}</span>
            <button type="button" className="btn btn-secondary profile-auth-btn" onClick={() => signOut()}>
              <LogOut size={16} aria-hidden="true" />
              Sign out
            </button>
          </div>
        ) : firebaseAuthEnabled ? (
          <div className="profile-auth-card__login">
            <p className="profile-auth-card__hint">
              <LogIn size={16} aria-hidden="true" />
              Sign in with Firebase Email/Password (not Google).
            </p>
            <AuthLoginPanel onToken={onAuthToken} />
          </div>
        ) : (
          <p className="profile-auth-card__warning">
            <ShieldAlert size={16} aria-hidden="true" />
            Firebase login is not configured. Set <code>FIREBASE_WEB_API_KEY</code> in{' '}
            <code>configs/.env</code> or <code>VITE_FIREBASE_API_KEY</code> in the frontend env, then restart the API and Vite dev server.
          </p>
        )}
      </section>

      {!isSignedIn ? (
        <div className="profile-selector">
          <label htmlFor="user-select" style={{ fontWeight: 600 }}>Browse team member:</label>
          <select
            id="user-select"
            className="input"
            style={{ maxWidth: '320px' }}
            value={browseUserKey}
            onChange={(e) => setBrowseUserKey(e.target.value)}
          >
            {Object.values(userProfilesData).map((profile) => (
              <option key={profile.username} value={profile.username}>
                {profile.full_name} ({profile.role})
              </option>
            ))}
          </select>
        </div>
      ) : null}

      <div className="profile-layout">
        {/* Sidebar */}
        <aside className="profile-sidebar">
          <div className="profile-avatar-container">
            <img src={selectedProfile.imageUrl} alt={selectedProfile.full_name} className="profile-avatar" />
          </div>
          <div>
            <h2 className="profile-name">{selectedProfile.full_name}</h2>
            <p className="profile-role">{selectedProfile.role}</p>
          </div>

          <div className="profile-contact">
            <a href={`mailto:${selectedProfile.email}`} className="profile-contact-item">
              <Mail size={16} />
              <span>{selectedProfile.email}</span>
            </a>
            {selectedProfile.socialLinks?.linkedin && (
              <a href={selectedProfile.socialLinks.linkedin} className="profile-contact-item">
                <Link size={16} />
                <span>LinkedIn Profile</span>
              </a>
            )}
            {selectedProfile.socialLinks?.github && (
              <a href={selectedProfile.socialLinks.github} className="profile-contact-item">
                <ExternalLink size={16} />
                <span>GitHub Profile</span>
              </a>
            )}
          </div>
        </aside>

        {/* Main Content */}
        <main className="profile-main">
          <section className="profile-section">
            <h3 className="profile-section-title">
              <User size={20} /> About
            </h3>
            <p className="profile-bio">{selectedProfile.bio}</p>
          </section>

          {selectedProfile.achievements && selectedProfile.achievements.length > 0 && (
            <section className="profile-section">
              <h3 className="profile-section-title">
                <Award size={20} /> Achievements & Milestones
              </h3>
              <ul className="profile-list">
                {selectedProfile.achievements.map((item, idx) => (
                  <li key={idx} className="profile-list-item">
                    <Award size={18} style={{ color: 'var(--color-primary)', flexShrink: 0, marginTop: '2px' }} />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {selectedProfile.publications && selectedProfile.publications.length > 0 && (
            <section className="profile-section">
              <h3 className="profile-section-title">
                {selectedProfile.role.includes('IT') ? <Briefcase size={20} /> : <BookOpen size={20} />} 
                {selectedProfile.role.includes('IT') ? ' Key Projects' : ' Selected Publications'}
              </h3>
              <ul className="profile-list">
                {selectedProfile.publications.map((item, idx) => (
                  <li key={idx} className="profile-list-item">
                    <BookOpen size={18} style={{ color: 'var(--color-primary)', flexShrink: 0, marginTop: '2px' }} />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {selectedProfile.skills && selectedProfile.skills.length > 0 && (
            <section className="profile-section">
              <h3 className="profile-section-title">
                <Code size={20} /> Expertise & Skills
              </h3>
              <div className="profile-skills">
                {selectedProfile.skills.map((skill, idx) => (
                  <span key={idx} className="profile-skill-tag">{skill}</span>
                ))}
              </div>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
