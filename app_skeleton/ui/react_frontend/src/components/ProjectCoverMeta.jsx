import { Calendar, Target } from 'lucide-react';

function MetaAsideCell({ icon: Icon, label, value }) {
  if (!value) return null;
  return (
    <div className="project-cover-meta-aside__cell">
      <span className="project-cover-meta-aside__label">
        {Icon ? <Icon size={11} aria-hidden /> : null}
        {label}
      </span>
      <span className="project-cover-meta-aside__value">{value}</span>
    </div>
  );
}

/** Focus + timeline column on the right side of the glass cover card. */
export default function ProjectCoverMeta({ identity = {} }) {
  const items = [
    { icon: Target, label: 'Focus', value: identity.disease_focus },
    { icon: Calendar, label: 'Timeline', value: identity.timeline },
  ].filter((item) => item.value);

  if (!items.length) return null;

  return (
    <aside className="project-cover-meta-aside" aria-label="Project metadata">
      {items.map((item) => (
        <MetaAsideCell key={item.label} icon={item.icon} label={item.label} value={item.value} />
      ))}
    </aside>
  );
}
