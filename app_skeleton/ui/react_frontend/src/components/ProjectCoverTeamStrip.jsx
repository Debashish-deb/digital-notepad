import { buildProjectTeamRoster } from '../utils/teamRoster.js';

const MAX_ACTIVE_CARDS = 8;

function sortMembersForCover(members) {
  return [...members].sort((a, b) => {
    const aPhoto = Boolean(a.photoUrl);
    const bPhoto = Boolean(b.photoUrl);
    if (aPhoto !== bPhoto) return aPhoto ? -1 : 1;
    const aLead = /project lead|lead/i.test(a.role || '');
    const bLead = /project lead|lead/i.test(b.role || '');
    if (aLead !== bLead) return aLead ? -1 : 1;
    return (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' });
  });
}

function shortMemberName(name) {
  const parts = String(name || '').trim().split(/\s+/).filter(Boolean);
  if (parts.length <= 1) return parts[0] || 'Member';
  return `${parts[0]} ${parts[parts.length - 1].charAt(0)}.`;
}

function shortMemberRole(role) {
  const raw = String(role || '').trim();
  if (!raw) return 'Member';
  if (/project lead|lead/i.test(raw)) return 'Lead';
  if (raw.length <= 14) return raw;
  return `${raw.slice(0, 12)}…`;
}

function MemberMiniCard({ member }) {
  const initial = (member.name || '?').trim().charAt(0).toUpperCase();
  const isLead = /project lead|lead/i.test(member.role || '');
  return (
    <article
      className={`project-cover-member-card${isLead ? ' is-lead' : ''}`}
      title={`${member.name}${member.role ? ` — ${member.role}` : ''}`}
    >
      <span className="project-cover-member-card__photo" aria-hidden>
        {member.photoUrl ? (
          <img src={member.photoUrl} alt="" />
        ) : (
          <span className="project-cover-member-card__initial">{initial}</span>
        )}
      </span>
      <div className="project-cover-member-card__copy">
        <span className="project-cover-member-card__name">{shortMemberName(member.name)}</span>
        <span className="project-cover-member-card__role">{shortMemberRole(member.role)}</span>
      </div>
    </article>
  );
}

function OverflowChip({ count, title }) {
  if (!count) return null;
  return (
    <span
      className="project-cover-member-card project-cover-member-card--overflow"
      title={title}
      aria-label={title}
    >
      <span className="project-cover-member-card__overflow">+{count}</span>
    </span>
  );
}

function ProjectCoverPiPedestal({ pi }) {
  const initial = (pi.name || '?').trim().charAt(0).toUpperCase();
  return (
    <div className="project-cover-pi-pedestal">
      <span className="project-cover-pi-pedestal__photo" aria-hidden>
        {pi.photoUrl ? (
          <img src={pi.photoUrl} alt="" />
        ) : (
          <span className="project-cover-pi-pedestal__initial">{initial}</span>
        )}
      </span>
      <div className="project-cover-pi-pedestal__copy">
        <strong className="project-cover-pi-pedestal__name">{pi.name}</strong>
        <span className="project-cover-pi-pedestal__badge">Principal investigator</span>
      </div>
    </div>
  );
}

/** Footer team strip — PI + active member cards in one row; overflow/inactive as +N. */
export default function ProjectCoverTeamStrip({ personnel = [], identity = {} }) {
  const { pi, active, inactive } = buildProjectTeamRoster(personnel, identity);
  const activeSorted = sortMembersForCover(active);
  const inactiveCount = inactive.length;
  const activeCount = activeSorted.length;
  const visibleActive = activeSorted.slice(0, MAX_ACTIVE_CARDS);
  const activeOverflow = Math.max(0, activeCount - visibleActive.length);
  const totalTeam = activeCount + inactiveCount;

  if (!pi && !activeCount && !inactiveCount) return null;

  const inactiveNames = inactive.map((m) => m.name).filter(Boolean).join(', ');

  return (
    <div className="project-cover-team-strip">
      {pi ? (
        <div className="project-cover-team-strip__pi">
          <span className="project-cover-footer-cell__label">Principal investigator</span>
          <ProjectCoverPiPedestal pi={pi} />
        </div>
      ) : null}

      {totalTeam > 0 ? (
        <div className="project-cover-team-strip__members">
          <span className="project-cover-footer-cell__label">
            Team ({totalTeam})
          </span>
          <div className="project-cover-member-cards">
            {visibleActive.map((member) => (
              <MemberMiniCard key={member.key || member.name} member={member} />
            ))}
            <OverflowChip
              count={activeOverflow}
              title={`${activeOverflow} more active member${activeOverflow === 1 ? '' : 's'}`}
            />
            <OverflowChip
              count={inactiveCount}
              title={
                inactiveNames
                  ? `${inactiveCount} inactive / alumni: ${inactiveNames}`
                  : `${inactiveCount} inactive / alumni`
              }
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}
