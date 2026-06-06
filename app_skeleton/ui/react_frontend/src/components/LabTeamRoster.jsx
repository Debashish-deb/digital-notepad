import {
  ClipboardList,
  Cpu,
  FlaskConical,
  GraduationCap,
  Microscope,
  Stethoscope,
  User,
  Crown,
} from 'lucide-react';
import {
  normalizeTeamMember,
  splitLabTeamRoster,
} from '../utils/teamRoster.js';

function roleIcon(role, { featured = false } = {}) {
  const r = `${role || ''}`.toLowerCase();
  const size = featured ? 22 : 18;
  if (r.includes('principal investigator') || r === 'pi') {
    return <Crown size={size} aria-hidden />;
  }
  if (r.includes('it specialist') || r.includes('platform')) {
    return <Cpu size={size} aria-hidden />;
  }
  if (r.includes('lab manager') || r.includes('laboratory manager')) {
    return <FlaskConical size={size} aria-hidden />;
  }
  if (r.includes('research coordinator')) {
    return <ClipboardList size={size} aria-hidden />;
  }
  if (r.includes('clinical')) {
    return <Stethoscope size={size} aria-hidden />;
  }
  if (r.includes('doctoral') || r.includes('phd student') || r.includes('researcher')) {
    return <GraduationCap size={size} aria-hidden />;
  }
  if (r.includes('spatial') || r.includes('omics')) {
    return <Microscope size={size} aria-hidden />;
  }
  return <User size={size} aria-hidden />;
}

function roleTone(role) {
  const r = `${role || ''}`.toLowerCase();
  if (r.includes('principal investigator') || r === 'pi') return 'pi';
  if (r.includes('it specialist')) return 'it';
  if (r.includes('lab manager') || r.includes('laboratory manager')) return 'lab';
  if (r.includes('research coordinator')) return 'coord';
  if (r.includes('clinical')) return 'clinical';
  if (r.includes('doctoral')) return 'phd';
  return 'default';
}

function MemberCard({ member, featured = false }) {
  const normalized = normalizeTeamMember(member);
  const tone = roleTone(normalized.role);

  return (
    <article
      className={`lab-team-card lab-team-card--${tone}${featured ? ' lab-team-card--featured' : ''}`}
    >
      <span
        className={`lab-team-card__icon${normalized.photoUrl ? ' lab-team-card__icon--photo' : ''}`}
        aria-hidden
      >
        {normalized.photoUrl ? (
          <img className="lab-team-card__photo" src={normalized.photoUrl} alt="" />
        ) : (
          roleIcon(normalized.role, { featured })
        )}
      </span>
      <div className="lab-team-card__copy">
        <strong className="lab-team-card__name">{normalized.name}</strong>
        <span className="lab-team-card__role">{normalized.role}</span>
        {normalized.focus ? (
          <p className="lab-team-card__focus">{normalized.focus}</p>
        ) : null}
      </div>
    </article>
  );
}

export default function LabTeamRoster({
  members = [],
  className = '',
  showHint = false,
  hint = null,
}) {
  const { pi, rest } = splitLabTeamRoster(members);

  if (!pi && !rest.length) {
    return (
      <p className="lab-team-roster__empty text-caption muted">
        No team members listed yet.
      </p>
    );
  }

  return (
    <div className={`lab-team-roster${className ? ` ${className}` : ''}`}>
      {showHint && hint ? <p className="lab-team-roster__hint text-caption muted">{hint}</p> : null}
      {pi ? (
        <div className="lab-team-roster__pi-row">
          <MemberCard member={pi} featured />
        </div>
      ) : null}
      {rest.length ? (
        <div className="lab-team-roster__grid">
          {rest.map((member) => (
            <MemberCard key={normalizeTeamMember(member).key} member={member} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
