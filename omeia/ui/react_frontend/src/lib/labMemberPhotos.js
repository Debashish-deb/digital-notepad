/** Lab member photo manifest and resolver — assets in /lab-members/. */

const PHOTO_BASE = '/lab-members';

/** Slug → preferred extension (webp unless noted). */
export const LAB_MEMBER_PHOTO_MANIFEST = {
  ada: 'webp',
  aino: 'webp',
  aleksandra: 'webp',
  anastasia: 'webp',
  andreas: 'webp',
  aniinna: 'webp',
  anni: 'webp',
  annik: 'webp',
  antti: 'webp',
  deb: 'webp',
  elias: 'webp',
  ella: 'webp',
  foteini: 'jpg',
  hanna: 'webp',
  iga: 'webp',
  inga: 'webp',
  joonas: 'webp',
  karen: 'webp',
  kursat: 'webp',
  laura: 'webp',
  maija: 'webp',
  maria: 'webp',
  matilda: 'webp',
  naipunya: 'webp',
  nika: 'webp',
  noora: 'webp',
  pablo: 'webp',
  sara: 'webp',
  sarah: 'webp',
  saun: 'webp',
  silija: 'webp',
  ulla: 'webp',
  wenqing: 'webp',
  zhihan: 'webp',
  ziqi: 'webp',
};

const USERNAME_TO_SLUG = {
  afarkkila: 'aniinna',
  alundgren: 'anastasia',
  jjukonen: 'joonas',
  mvaariskoski: 'maija',
  sshah: 'saun',
  debdeba: 'deb',
};

const NAME_SLUG_ALIASES = [
  [/anniina|färkkilä|farkkila/i, 'aniinna'],
  [/anastasia|lundgren/i, 'anastasia'],
  [/joonas|jukonen/i, 'joonas'],
  [/maija|vää?riskoski|vaariskoski/i, 'maija'],
  [/saun|saundarya/i, 'saun'],
  [/debashish/i, 'deb'],
  [/foteini|foteni|chamchougia/i, 'foteini'],
];

function slugToUrl(slug) {
  const ext = LAB_MEMBER_PHOTO_MANIFEST[slug];
  if (!ext) return null;
  return `${PHOTO_BASE}/${slug}.${ext}`;
}

function normalizeToken(value) {
  return `${value || ''}`
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]/g, '');
}

function extractNickname(name) {
  const match = `${name || ''}`.match(/\(([^)]+)\)/);
  return match ? match[1].trim() : '';
}

function extractFirstName(name) {
  const clean = `${name || ''}`.split(',')[0].trim();
  const withoutNick = clean.replace(/\([^)]*\)/g, '').trim();
  const first = withoutNick.split(/\s+/)[0] || '';
  return normalizeToken(first);
}

function matchSlugByName(name) {
  const full = `${name || ''}`;

  for (const [pattern, slug] of NAME_SLUG_ALIASES) {
    if (pattern.test(full)) return slug;
  }

  const nickname = normalizeToken(extractNickname(full));
  if (nickname && LAB_MEMBER_PHOTO_MANIFEST[nickname]) return nickname;

  const firstName = extractFirstName(full);
  if (firstName && LAB_MEMBER_PHOTO_MANIFEST[firstName]) return firstName;

  const normalizedFull = normalizeToken(full);
  for (const slug of Object.keys(LAB_MEMBER_PHOTO_MANIFEST)) {
    if (normalizedFull.includes(slug)) return slug;
  }

  return null;
}

export function resolveLabMemberPhoto(member) {
  if (!member) return null;

  const username = `${member.username || ''}`.toLowerCase();
  if (username && USERNAME_TO_SLUG[username]) {
    return slugToUrl(USERNAME_TO_SLUG[username]);
  }

  const name = member.name || member.full_name || '';
  const slug = matchSlugByName(name);
  return slug ? slugToUrl(slug) : null;
}
