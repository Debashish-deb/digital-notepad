import { Users } from 'lucide-react';
import { buildProjectTeamRoster } from '../utils/teamRoster.js';

function MemberChip({ member, isLead = false, isInactive = false }) {
  const isActualLead = isLead || /lead/i.test(member.role || '');
  return (
    <div
      className={`project-team-member-chip${isActualLead ? ' is-lead' : ''}${isInactive ? ' is-inactive' : ''}`}
      title={`${member.name} — ${member.role || 'Collaborator'}`}
    >
      {member.photoUrl ? (
        <img className="project-team-member-photo" src={member.photoUrl} alt="" />
      ) : null}
      <span className="project-team-member-name">{member.name}</span>
      {member.role ? (
        <span className="project-team-member-role">
          {isActualLead ? 'Lead' : member.role}
        </span>
      ) : null}
    </div>
  );
}

/** Layout with PI featured left, active / alumni flow chips right. */
export default function ProjectTeamRoster({ personnel = [], identity = {}, className = '' }) {
  const { pi, active, inactive } = buildProjectTeamRoster(personnel, identity);

  if (!pi && !active.length && !inactive.length) {
    return null;
  }

  return (
    <div className={`project-team-roster${className ? ` ${className}` : ''}`}>
      {pi ? (
        <div className="project-team-roster__pi">
          <span className="project-team-roster__pi-label">Principal investigator</span>
          <strong className="project-team-roster__pi-name">{pi.name}</strong>
          <span className="project-team-roster__pi-badge">PI</span>
        </div>
      ) : null}

      <div className="project-team-roster__groups">
        {active.length > 0 && (
          <div className="project-team-roster__group">
            <h4 className="project-team-roster__group-title">Active</h4>
            <div className="project-team-roster-v2__flow">
              {active.map((member) => (
                <MemberChip key={member.key || member.name} member={member} />
              ))}
            </div>
          </div>
        )}

        {inactive.length > 0 && (
          <div className="project-team-roster__group project-team-roster__group--muted">
            <h4 className="project-team-roster__group-title">Inactive / alumni</h4>
            <div className="project-team-roster-v2__flow">
              {inactive.map((member) => (
                <MemberChip key={member.key || member.name} member={member} isInactive />
              ))}
            </div>
          </div>
        )}

        {!active.length && !inactive.length && (
          <p className="text-footnote muted">No additional team members listed.</p>
        )}
      </div>
    </div>
  );
}

export function ProjectTeamSection({ personnel = [], identity = {} }) {
  const hasTeam = (personnel?.length || 0) > 0 || identity?.principal_investigator;
  if (!hasTeam) return null;

  return (
    <div className="project-intro-team workspace-subsection">
      <h3 className="workspace-subpanel-title workspace-subpanel-title--compact">
        <Users size={14} /> Team
      </h3>
      <ProjectTeamRoster personnel={personnel} identity={identity} />
    </div>
  );
}
