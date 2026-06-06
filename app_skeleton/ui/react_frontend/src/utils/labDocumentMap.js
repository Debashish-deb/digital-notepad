/**
 * Lab-wide document landscape — zones, counts, and mermaid source for Data & Storage → Lab documents.
 */

export const LAB_DOCUMENT_ZONES = [
  {
    id: 'overview',
    label: 'Lab overview',
    emoji: '📋',
    blurb: 'Onboarding, guidelines, permits, personnel, cleaning',
    nav: { main: 'overview', sub: 'guidelines' },
    sectionIds: [
      'overview_guidelines',
      'overview_documents',
      'overview_cleaning',
      'overview_onboarding',
      'overview_personnel',
    ],
    filterCategoryPrefix: 'overview_',
    color: '#c45c8a',
  },
  {
    id: 'orders',
    label: 'Orders & procurement',
    emoji: '🧾',
    blurb: 'Billing instructions and order archives',
    nav: { main: 'orders', sub: 'billing' },
    sectionIds: ['orders_billing', 'orders_archive'],
    filterCategoryPrefix: 'orders_',
    color: '#d97706',
  },
  {
    id: 'meetings',
    label: 'Lab meetings',
    emoji: '🗓️',
    blurb: 'Meeting notes and presentation decks',
    nav: { main: 'overview', sub: 'get_started' },
    sectionIds: ['meetings'],
    filterCategoryPrefix: 'meetings_',
    color: '#6366f1',
  },
  {
    id: 'projects',
    label: 'Research projects',
    emoji: '🔬',
    blurb: 'Per-project logs, protocols, data & writing',
    nav: { main: 'projects_data', sub: 'portfolio' },
    sectionIds: [],
    filterCategoryPrefix: null,
    color: '#2563eb',
  },
  {
    id: 'wet_lab',
    label: 'Wet lab & CyCIF',
    emoji: '🧪',
    blurb: 'Protocols, inventory, instrument files',
    nav: { main: 'wet_lab', sub: 'files' },
    sectionIds: ['wet_lab_files'],
    filterCategoryPrefix: 'wet_lab_',
    color: '#16a34a',
  },
  {
    id: 'social',
    label: 'Social & outreach',
    emoji: '📸',
    blurb: 'Retreats, photos, visitor records',
    nav: { main: 'social', sub: 'lab_photos' },
    sectionIds: ['social_misc'],
    filterCategoryPrefix: 'social_',
    color: '#8b5cf6',
  },
  {
    id: 'storage',
    label: 'Storage & IT setup',
    emoji: '💾',
    blurb: 'Allas, DataCloud, disks, platform configs',
    nav: { main: 'data_storage', sub: 'landscape' },
    sectionIds: [],
    filterCategoryPrefix: 'storage_',
    color: '#0d9488',
  },
];

export function buildZoneStats(manifest, projectCount = 0) {
  const sections = manifest?.sections || [];
  const byId = Object.fromEntries(sections.map((s) => [s.section_id, s]));

  return LAB_DOCUMENT_ZONES.map((zone) => {
    const linked = zone.sectionIds.map((id) => byId[id]).filter(Boolean);
    const docCount = linked.reduce(
      (sum, s) => sum + (s.metrics?.document_count || 0),
      0,
    );
    const processed = linked.filter((s) => s.processed).length;
    return {
      ...zone,
      docCount: zone.id === 'projects' ? projectCount : docCount,
      unit: zone.id === 'projects' ? 'projects' : 'files',
      processedSections: processed,
      totalSections: zone.sectionIds.length,
    };
  });
}

/** Mermaid flowchart — biologist-friendly labels. */
export function buildLabDocumentMermaid(zones) {
  const find = (id) => zones.find((z) => z.id === id);
  const ov = find('overview');
  const ord = find('orders');
  const mtg = find('meetings');
  const prj = find('projects');
  const wet = find('wet_lab');
  const soc = find('social');
  const sto = find('storage');

  return `flowchart TB
    classDef hub fill:#f0f4ff,stroke:#4f6bed,stroke-width:2px,color:#1e293b
    classDef zone fill:#ffffff,stroke:#94a3b8,stroke-width:1.5px,color:#334155
    classDef hot fill:#ecfdf5,stroke:#0d9488,stroke-width:2px,color:#134e4a

    APP["OMEIA Lab Assistant<br/>your files in one place"]:::hub

    subgraph KNOW["Lab knowledge — shared folders"]
      OV["${ov.emoji} Overview<br/>${ov.docCount} files<br/>guidelines · permits · cleaning"]:::zone
      ORD["${ord.emoji} Orders<br/>${ord.docCount} files<br/>billing · archives"]:::zone
      MTG["${mtg.emoji} Meetings<br/>${mtg.docCount} files<br/>notes · slides"]:::zone
      SOC["${soc.emoji} Social<br/>events · photos"]:::zone
    end

    subgraph RES["Research work"]
      PRJ["${prj.emoji} Projects<br/>${prj.docCount} project folders<br/>log · plan · data · methods · writing"]:::hot
      WET["${wet.emoji} Wet lab / CyCIF<br/>protocols · inventory"]:::zone
    end

    subgraph STORE["Where data lives"]
      STO["${sto.emoji} Storage systems<br/>L-drive · P-drive · DataCloud · Allas"]:::zone
      CFG["Platform setup guides<br/>P-drive and DataCloud config"]:::zone
    end

    APP --> KNOW
    APP --> RES
    PRJ -->|"protocols and raw data"| STORE
    OV -->|"cleaning and inventory"| STO
    WET --> STO
    CFG --> STO`;
}
