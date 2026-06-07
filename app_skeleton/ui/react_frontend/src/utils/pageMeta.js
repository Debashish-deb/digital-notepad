/** Per-route and default document / Open Graph metadata. */

export const PAGE_META_DEFAULT = {
  title: 'Färkkilä Digital Research NotePad',
  description:
    'OMEIA — the Färkkilä Lab digital research notebook for ONCOSYS projects, wet-lab protocols, spatial imaging, bioinformatics, and AI-assisted knowledge search.',
  image: '/covers/overview.png',
  siteName: 'Färkkilä Lab · OMEIA',
};

const META_SELECTORS = {
  description: { attr: 'name', key: 'description' },
  'og:title': { attr: 'property', key: 'og:title' },
  'og:description': { attr: 'property', key: 'og:description' },
  'og:image': { attr: 'property', key: 'og:image' },
  'og:type': { attr: 'property', key: 'og:type' },
  'og:site_name': { attr: 'property', key: 'og:site_name' },
  'twitter:card': { attr: 'name', key: 'twitter:card' },
  'twitter:title': { attr: 'name', key: 'twitter:title' },
  'twitter:description': { attr: 'name', key: 'twitter:description' },
  'twitter:image': { attr: 'name', key: 'twitter:image' },
};

function setMetaTag(name, content, attr = 'name') {
  if (!content) return;
  let el = document.querySelector(`meta[${attr}="${name}"]`);
  if (!el) {
    el = document.createElement('meta');
    el.setAttribute(attr, name);
    document.head.appendChild(el);
  }
  el.setAttribute('content', content);
}

function absoluteImageUrl(imagePath) {
  if (!imagePath) return '';
  if (/^https?:\/\//i.test(imagePath)) return imagePath;
  const origin = typeof window !== 'undefined' ? window.location.origin : '';
  return `${origin}${imagePath.startsWith('/') ? imagePath : `/${imagePath}`}`;
}

/**
 * @param {{ title: string, description?: string, image?: string, siteName?: string }} meta
 */
export function applyPageMeta(meta) {
  const title = meta.title || PAGE_META_DEFAULT.title;
  const description = meta.description || PAGE_META_DEFAULT.description;
  const image = absoluteImageUrl(meta.image || PAGE_META_DEFAULT.image);
  const siteName = meta.siteName || PAGE_META_DEFAULT.siteName;

  document.title = title;

  const values = {
    description,
    'og:title': title,
    'og:description': description,
    'og:image': image,
    'og:type': 'website',
    'og:site_name': siteName,
    'twitter:card': 'summary_large_image',
    'twitter:title': title,
    'twitter:description': description,
    'twitter:image': image,
  };

  for (const [key, spec] of Object.entries(META_SELECTORS)) {
    setMetaTag(spec.key, values[key], spec.attr);
  }
}
