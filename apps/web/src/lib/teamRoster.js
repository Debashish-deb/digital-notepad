import { resolveLabMemberPhoto } from './labMemberPhotos.js';

/** Lab team display order: PI alone on top → row 2 starts with Joonas → Debashish last. */

const PI_MATCH = /färkkilä|farkkila|anniina/i;
const JOONAS_MATCH = /jukonen|joonas/i;
const DEB_MATCH = /debashish|deb,?\s*msc/i;

export function isPiMember(member) {
  const role = `${member.role || ''}`.toLowerCase();
  const name = `${member.name || member.full_name || ''}`;
  return role.includes('principal investigator') || role === 'pi' || PI_MATCH.test(name);
}

export function isJoonasMember(member) {
  const username = `${member.username || ''}`.toLowerCase();
  return username === 'jjukonen' || JOONAS_MATCH.test(`${member.name || member.full_name || ''}`);
}

export function isDebashishMember(member) {
  const username = `${member.username || ''}`.toLowerCase();
  return username === 'debdeba' || DEB_MATCH.test(`${member.name || member.full_name || ''}`);
}

export function sortLabTeamMembers(members) {
  const list = [...(members || [])];
  const pi = list.find(isPiMember);
  const joonas = list.find(isJoonasMember);
  const deb = list.find(isDebashishMember);
  const middle = list.filter((m) => m !== pi && m !== joonas && m !== deb);

  const ordered = [];
  if (pi) ordered.push(pi);
  if (joonas) ordered.push(joonas);
  ordered.push(...middle);
  if (deb) ordered.push(deb);
  return ordered;
}

export function splitLabTeamRoster(members) {
  const ordered = sortLabTeamMembers(members);
  const pi = ordered.find(isPiMember) || null;
  const rest = ordered.filter((m) => m !== pi);
  return { pi, rest, ordered };
}

export function normalizeTeamMember(member) {
  const photoUrl = resolveLabMemberPhoto(member);
  return {
    key: member.username || member.name || member.full_name,
    name: member.name || member.full_name || 'Unknown',
    role: formatProjectRole(member.role) || 'Team member',
    focus:
      member.focus
      || (Array.isArray(member.allowed_projects) && member.allowed_projects.length > 0
        ? `Projects: ${member.allowed_projects.join(', ')}`
        : ''),
    username: member.username,
    photoUrl: photoUrl || undefined,
  };
}

const INACTIVE_RE = /alumni|inactive|former|past|completed|archived/i;
const NON_PERSON_HINTS =
  /\b(pathway|pathways|inhibitor|inhibitors|levels|samples|panck|p21|p27|cdk|pi3k|akt|mtor|fgfr|treatment|resistant|tumou?r|protein|marker|magenta|yellow|green)\b/i;
const PERSON_NAME_PART =
  /^[A-ZÀ-ÖØ-ÞÄÖÅ][a-zà-öø-ÿäöå\-']+$/;

function formatProjectRole(role) {
  const raw = `${role || ''}`.trim();
  if (!raw) return '';
  if (/^project[_\s-]?lead$/i.test(raw)) return 'Project lead';
  if (/^principal investigator$/i.test(raw) || raw.toLowerCase() === 'pi') return 'Principal investigator';
  return raw.replace(/_/g, ' ');
}

export function isLikelyPersonName(name) {
  const raw = `${name || ''}`.trim();
  if (!raw || raw.length < 4 || raw.length > 72) return false;
  if (NON_PERSON_HINTS.test(raw)) return false;
  if (/https?:\/\//i.test(raw) || /^\.{0,2}\/?\d/.test(raw)) return false;
  const parts = raw.split(',')[0].trim().split(/\s+/).filter(Boolean);
  if (parts.length < 2 || parts.length > 4) return false;
  return parts.every((part) => PERSON_NAME_PART.test(part));
}

export function parsePrincipalInvestigator(raw) {
  if (!raw) return null;
  const name = String(raw).split(',')[0].trim();
  if (!name) return null;
  return { name, role: 'Principal investigator', focus: '' };
}

export function memberMatchesPi(member, piName) {
  if (!piName) return false;
  const name = `${member.name || member.full_name || ''}`.trim();
  if (!name) return false;
  const piShort = piName.split(',')[0].trim().toLowerCase();
  return name.toLowerCase() === piShort || PI_MATCH.test(name);
}

export function isInactiveMember(member) {
  const status = `${member.status || member.involvement || ''}`;
  const role = `${member.role || ''}`;
  const focus = `${member.focus || ''}`;
  return (
    member.active === false
    || INACTIVE_RE.test(status)
    || INACTIVE_RE.test(role)
    || INACTIVE_RE.test(focus)
  );
}

function projectMemberSort(a, b) {
  const aLead = /project lead|lead/i.test(a.role || '');
  const bLead = /project lead|lead/i.test(b.role || '');
  if (aLead !== bLead) return aLead ? -1 : 1;
  return a.name.localeCompare(b.name, undefined, { sensitivity: 'base' });
}

/** Project workspace roster: PI featured, others grouped by involvement. */
export function buildProjectTeamRoster(personnel = [], identity = {}) {
  const piRaw = identity.principal_investigator;
  const piParsed = parsePrincipalInvestigator(piRaw);
  const pi = piParsed && isPiMember({ name: piParsed.name, role: piParsed.role })
    ? normalizeTeamMember(piParsed)
    : piParsed
      ? normalizeTeamMember(piParsed)
      : null;

  const active = [];
  const inactive = [];

  for (const member of personnel || []) {
    if (!isLikelyPersonName(member.name || member.full_name)) continue;
    const normalized = normalizeTeamMember(member);
    if (pi && memberMatchesPi(normalized, piRaw || pi.name)) continue;
    if (isInactiveMember(member)) inactive.push(normalized);
    else active.push(normalized);
  }

  active.sort(projectMemberSort);
  inactive.sort(projectMemberSort);

  return { pi, active, inactive };
}
