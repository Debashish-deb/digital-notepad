import { useCallback, useId, useLayoutEffect, useMemo, useRef, useState } from 'react';
import './TaxonomyConnectorMap.css';

/**
 * Parent relationships for wet-lab scope chips (smart_taxonomy.json ids).
 * Max two visual tiers — top-level library categories, then workflow sub-filters.
 */
const SCOPE_PARENT_BY_ID = {
  patient_samples: 'protocols_methods',
  sample_preparation: 'protocols_methods',
  tissue_processing: 'protocols_methods',
  spatial_assays: 'protocols_methods',
  staining_flow: 'protocols_methods',
  reagents_inventory: 'reagents_panels',
};

function buildHierarchyLayout(chips) {
  if (!chips.length) return null;

  const ids = new Set(chips.map((c) => c.id));
  const parentChips = chips.filter((chip) => {
    const parentId = SCOPE_PARENT_BY_ID[chip.id];
    return !parentId || !ids.has(parentId);
  });

  const childGroups = parentChips
    .map((parent) => ({
      parent,
      children: chips.filter((chip) => SCOPE_PARENT_BY_ID[chip.id] === parent.id),
    }))
    .filter((group) => group.children.length > 0);

  return { parentChips, childGroups };
}

function TaxonomyNode({ chip, active, onClick, variant = 'child', chipId }) {
  const shortLabel = chip.label?.replace(/^All /, '') || chip.label;
  const isEmpty = chip.count === 0;

  return (
    <button
      type="button"
      data-chip-id={chipId || chip.id}
      className={[
        'tcx-node',
        `tcx-node--${variant}`,
        active ? 'is-active' : '',
        chip.synthetic ? 'tcx-node--synthetic' : '',
        isEmpty ? 'tcx-node--empty' : '',
      ].filter(Boolean).join(' ')}
      onClick={() => onClick(chip)}
      title={chip.description || chip.label}
      aria-pressed={active}
    >
      <span className="tcx-node__dot" aria-hidden />
      <span className="tcx-node__label">{shortLabel}</span>
      {chip.count != null ? (
        <span className="tcx-node__count">{chip.count.toLocaleString()}</span>
      ) : null}
    </button>
  );
}

function TaxonomyWireCanvas({ frameRef, layoutKey, childGroupCount }) {
  const uid = useId().replace(/:/g, '');
  const [geometry, setGeometry] = useState(null);
  const rafRef = useRef(0);

  const measure = useCallback(() => {
    const frame = frameRef.current;
    if (!frame) return false;

    const fr = frame.getBoundingClientRect();
    if (fr.width < 1 || fr.height < 1) return false;

    const parentRow = frame.querySelector('.tcx-parent-row');
    if (!parentRow) return false;

    const parentNodes = [...parentRow.querySelectorAll('.tcx-node--parent')];
    const parentById = Object.fromEntries(
      parentNodes.map((node) => [node.dataset.chipId, node]),
    );

    const groups = [...frame.querySelectorAll('.tcx-child-group')].map((groupEl) => {
      const parentId = groupEl.dataset.parentId;
      const parentNode = parentById[parentId];
      const childNodes = [...groupEl.querySelectorAll('.tcx-node--child')];
      if (!parentNode || !childNodes.length) return null;

      const pr = parentNode.getBoundingClientRect();
      const parentPt = {
        x: pr.left + pr.width / 2 - fr.left,
        y: pr.bottom - fr.top + 2,
      };

      const childPts = childNodes.map((child) => {
        const cr = child.getBoundingClientRect();
        return {
          x: cr.left - fr.left,
          y: cr.top + cr.height / 2 - fr.top,
          active: child.classList.contains('is-active'),
        };
      });

      const trunkX = parentPt.x;
      const trunkTop = parentPt.y;
      const trunkBottom = childPts[childPts.length - 1].y;
      const busY = childPts[0].y;
      const busEnd = childPts[childPts.length - 1].x - 6;
      const active = parentNode.classList.contains('is-active')
        || childPts.some((pt) => pt.active);

      return {
        parent: parentPt,
        trunk: { x: trunkX, y1: trunkTop, y2: trunkBottom },
        bus: childPts.length > 1
          ? { x1: trunkX, y1: busY, x2: busEnd, y2: busY }
          : null,
        children: childPts,
        active,
      };
    }).filter(Boolean);

    setGeometry({
      groups,
      width: fr.width,
      height: fr.height,
    });
    return true;
  }, [frameRef]);

  const scheduleMeasure = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    measure();
    rafRef.current = requestAnimationFrame(() => {
      measure();
      rafRef.current = requestAnimationFrame(() => {
        rafRef.current = 0;
        measure();
      });
    });
  }, [measure]);

  useLayoutEffect(() => {
    scheduleMeasure();
    const frame = frameRef.current;
    if (!frame) return undefined;

    const ro = new ResizeObserver(scheduleMeasure);
    ro.observe(frame);
    frame.querySelectorAll('.tcx-node').forEach((node) => ro.observe(node));

    const mo = new MutationObserver(scheduleMeasure);
    mo.observe(frame, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['class'],
    });

    window.addEventListener('resize', scheduleMeasure);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      ro.disconnect();
      mo.disconnect();
      window.removeEventListener('resize', scheduleMeasure);
    };
  }, [scheduleMeasure, layoutKey, childGroupCount]);

  if (!geometry?.groups?.length) return null;

  const { groups, width, height } = geometry;
  const gradId = `tcx-grad-${uid}`;
  const gradActiveId = `tcx-grad-active-${uid}`;
  const glowId = `tcx-glow-${uid}`;

  return (
    <svg
      className="tcx-wire-canvas"
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      aria-hidden
    >
      <defs>
        <linearGradient id={gradId} x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="var(--text-muted)" stopOpacity="0.35" />
          <stop offset="100%" stopColor="var(--text-muted)" stopOpacity="0.55" />
        </linearGradient>
        <linearGradient id={gradActiveId} x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="var(--color-primary)" stopOpacity="0.45" />
          <stop offset="100%" stopColor="var(--color-primary)" stopOpacity="1" />
        </linearGradient>
        <filter id={glowId} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2.2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {groups.map((group, groupIdx) => {
        const stroke = group.active ? `url(#${gradActiveId})` : `url(#${gradId})`;
        const sw = group.active ? 2.25 : 1.65;

        return (
          <g key={`group-wire-${groupIdx}`} className="tcx-wire tcx-wire--group">
            <line
              x1={group.trunk.x}
              y1={group.trunk.y1}
              x2={group.trunk.x}
              y2={group.trunk.y2}
              stroke={stroke}
              strokeWidth={sw}
              strokeLinecap="round"
              filter={group.active ? `url(#${glowId})` : undefined}
            />
            <circle
              cx={group.parent.x}
              cy={group.parent.y - 2}
              r={group.active ? 3.5 : 2.8}
              className={`tcx-wire-anchor${group.active ? ' is-active' : ''}`}
            />
            {group.bus ? (
              <line
                x1={group.bus.x1}
                y1={group.bus.y1}
                x2={group.bus.x2}
                y2={group.bus.y2}
                stroke={stroke}
                strokeWidth={sw}
                strokeLinecap="round"
                filter={group.active ? `url(#${glowId})` : undefined}
              />
            ) : null}
            {group.children.map((child, childIdx) => (
              <g key={`child-wire-${groupIdx}-${childIdx}`}>
                {group.bus ? (
                  <>
                    <line
                      x1={group.bus.x1}
                      y1={group.bus.y1}
                      x2={child.x}
                      y2={child.y}
                      stroke={child.active ? `url(#${gradActiveId})` : `url(#${gradId})`}
                      strokeWidth={child.active ? 2 : 1.5}
                      strokeLinecap="round"
                      filter={child.active ? `url(#${glowId})` : undefined}
                    />
                    <circle
                      cx={group.bus.x1}
                      cy={group.bus.y1}
                      r={child.active ? 2.8 : 2}
                      className={`tcx-wire-tap${child.active ? ' is-active' : ''}`}
                    />
                  </>
                ) : (
                  <line
                    x1={group.trunk.x}
                    y1={group.trunk.y2}
                    x2={child.x}
                    y2={child.y}
                    stroke={child.active ? `url(#${gradActiveId})` : `url(#${gradId})`}
                    strokeWidth={child.active ? 2 : 1.5}
                    strokeLinecap="round"
                    filter={child.active ? `url(#${glowId})` : undefined}
                  />
                )}
              </g>
            ))}
          </g>
        );
      })}
    </svg>
  );
}

export default function TaxonomyConnectorMap({
  chips = [],
  scopeLabel = 'Library scope',
  isChipActive,
  onChipClick,
  onResetScope,
}) {
  const frameRef = useRef(null);

  const layout = useMemo(() => buildHierarchyLayout(chips), [chips]);
  if (!layout) return null;

  const { parentChips, childGroups } = layout;
  const layoutKey = `${parentChips.map((c) => c.id).join(',')}-${childGroups.map((g) => g.parent.id).join(',')}`;

  const handleParentClick = (chip) => {
    const hasChildren = childGroups.some((group) => group.parent.id === chip.id);
    if (hasChildren && isChipActive(chip)) {
      onResetScope?.();
      return;
    }
    onChipClick(chip);
  };

  return (
    <section className="tcx-map tcx-map--stacked" aria-label={`${scopeLabel} taxonomy`}>
      <header className="tcx-map__heading">
        <span className="tcx-map__title">{scopeLabel}</span>
      </header>
      <div className="tcx-tree-frame" ref={frameRef}>
        <TaxonomyWireCanvas
          frameRef={frameRef}
          layoutKey={layoutKey}
          childGroupCount={childGroups.length}
        />
        <div className="tcx-tree">
          <div className="tcx-parent-row" data-row="parents" role="group" aria-label="Categories">
            {parentChips.map((chip) => (
              <TaxonomyNode
                key={chip.id}
                chip={chip}
                active={isChipActive(chip)}
                onClick={handleParentClick}
                variant="parent"
                chipId={chip.id}
              />
            ))}
          </div>
          {childGroups.map((group) => (
            <div
              key={group.parent.id}
              className="tcx-child-group"
              data-parent-id={group.parent.id}
              role="group"
              aria-label={`${group.parent.label} subcategories`}
            >
              <div className="tcx-child-row" data-row="children">
                {group.children.map((chip) => (
                  <TaxonomyNode
                    key={chip.id}
                    chip={chip}
                    active={isChipActive(chip)}
                    onClick={onChipClick}
                    variant="child"
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
