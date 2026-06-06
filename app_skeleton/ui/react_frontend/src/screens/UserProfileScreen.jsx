import React, { useState, useEffect } from 'react';
import { useApiContext } from '../api/ApiContext.jsx';
import { User, Mail, Award, BookOpen, Code, Link, ExternalLink, Briefcase } from 'lucide-react';
import { userProfilesData } from '../data/userProfilesData.js';
import './UserProfileScreen.css';

export default function UserProfileScreen({ title, description }) {
  const { authUser, userProfile } = useApiContext();
  
  // Try to match the logged in user with our detailed mock data
  const loggedInEmail = authUser?.email || userProfile?.email || '';
  const matchedUserKey = Object.keys(userProfilesData).find(
    k => userProfilesData[k].email === loggedInEmail
  ) || 'debdeba'; // Fallback to IT specialist for demo purposes

  const [selectedUserKey, setSelectedUserKey] = useState(matchedUserKey);

  const selectedProfile = userProfilesData[selectedUserKey];

  return (
    <div className="profile-container">
      <div className="profile-selector">
        <label htmlFor="user-select" style={{ fontWeight: 600 }}>View Profile:</label>
        <select 
          id="user-select" 
          className="input" 
          style={{ maxWidth: '300px' }}
          value={selectedUserKey}
          onChange={(e) => setSelectedUserKey(e.target.value)}
        >
          {Object.values(userProfilesData).map(profile => (
            <option key={profile.username} value={profile.username}>
              {profile.full_name} ({profile.role})
            </option>
          ))}
        </select>
      </div>

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
