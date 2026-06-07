import { useCallback, useId, useLayoutEffect, useMemo, useRef, useState } from 'react';
import './TaxonomyConnectorMap.css';

/** Parent folder relationships for scope chips (smart_taxonomy.json ids). */
const SCOPE_PARENT_BY_ID = {
  protocols: 'all_wet_lab',
  reagents_panels: 'all_wet_lab',
  spreadsheets: 'all_wet_lab',
  proto_spatial: 'protocols',
  proto_staining: 'protocols',
  proto_tissue: 'protocols',
  proto_sample_prep: 'protocols',
  patient_protocols: 'protocols',
  reagents_inventory: 'reagents_panels',
  reagents_geomx: 'reagents_panels',
  reagents_xenium: 'reagents_panels',
  reagents_spreadsheets: 'reagents_panels',
};

function filtersSubset(subset, superset) {
  return Object.entries(subset).every(([key, value]) => superset[key] === value);
}

function resolveRootId(chips, initialFilters) {
  const ids = new Set(chips.map((c) => c.id));
  const hasHierarchy = chips.some(
    (c) => SCOPE_PARENT_BY_ID[c.id] && ids.has(SCOPE_PARENT_BY_ID[c.id]),
  );
  if (!hasHierarchy) return null;

  if (ids.has('all_wet_lab')) return 'all_wet_lab';
  if (ids.has('protocols') && !ids.has('all_wet_lab')) return 'protocols';
  if (ids.has('reagents_panels') && !ids.has('all_wet_lab')) return 'reagents_panels';

  const exact = chips.find((chip) => chip.filter && filtersSubset(chip.filter, initialFilters));
  if (exact) return exact.id;

  const orphan = chips.find((c) => !SCOPE_PARENT_BY_ID[c.id] || !ids.has(SCOPE_PARENT_BY_ID[c.id]));
  return orphan?.id || chips[0]?.id || null;
}

function buildTreeTiers(chips, rootId, scopeLabel) {
  if (!chips.length) return null;

  const byId = Object.fromEntries(chips.map((c) => [c.id, c]));
  const ids = new Set(chips.map((c) => c.id));

  if (!rootId || !byId[rootId]) {
    const total = chips.reduce((sum, c) => sum + (c.count || 0), 0);
    return {
      topTier: {
        anchor: {
          id: '__root__',
          label: scopeLabel || 'Library scope',
          count: total,
          synthetic: true,
        },
        peers: chips,
      },
      subTiers: [],
    };
  }

  const directChildren = chips.filter((c) => SCOPE_PARENT_BY_ID[c.id] === rootId);
  const topPeers = directChildren.length
    ? directChildren
    : chips.filter((c) => c.id !== rootId);

  const subTiers = directChildren
    .map((hub) => ({
      hub,
      peers: chips.filter((c) => SCOPE_PARENT_BY_ID[c.id] === hub.id),
    }))
    .filter((tier) => tier.peers.length > 0 && ids.has(tier.hub.id));

  return {
    topTier: {
      anchor: byId[rootId],
      peers: topPeers,
    },
    subTiers,
  };
}

function TaxonomyNode({ chip, active, onClick, variant = 'leaf' }) {
  const shortLabel = chip.label?.replace(/^All /, '') || chip.label;
  return (
    <button
      type="button"
      className={[
        'tcx-node',
        `tcx-node--${variant}`,
        active ? 'is-active' : '',
        chip.synthetic ? 'tcx-node--synthetic' : '',
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

function ConnectorBranch({ peers, isChipActive, onChipClick, variant = 'peer' }) {
  if (!peers.length) return null;

  return (
    <div className="tcx-branch-row" role="group">
      <div className="tcx-branch-nodes">
        {peers.map((chip) => (
          <TaxonomyNode
            key={chip.id}
            chip={chip}
            active={isChipActive(chip)}
            onClick={onChipClick}
            variant={variant}
          />
        ))}
      </div>
    </div>
  );
}

function TreeTier({
  tier,
  tierIndex,
  isChipActive,
  onChipClick,
  onAnchorClick,
  peerVariant = 'peer',
}) {
  const { anchor, peers } = tier;
  const anchorActive = anchor.synthetic
    ? peers.every((c) => !isChipActive(c))
    : isChipActive(anchor);

  const handleAnchorClick = () => {
    if (anchor.synthetic) {
      onAnchorClick();
      return;
    }
    onChipClick(anchor);
  };

  const anchorVariant = tierIndex === 0 ? 'root' : 'hub';
  const hasBranches = peers.length > 0;

  return (
    <div
      className={[
        'tcx-tier',
        tierIndex === 0 ? 'tcx-tier--root' : 'tcx-tier--child',
      ].filter(Boolean).join(' ')}
      data-tier-index={tierIndex}
    >
      <div className="tcx-tier__row">
        <TaxonomyNode
          chip={anchor}
          active={anchorActive}
          onClick={handleAnchorClick}
          variant={anchorVariant}
        />
        {hasBranches ? (
          <ConnectorBranch
            peers={peers}
            isChipActive={isChipActive}
            onChipClick={onChipClick}
            variant={peerVariant}
          />
        ) : null}
      </div>
    </div>
  );
}

function TaxonomyWireCanvas({ frameRef, hasSubTiers, tiersKey }) {
  const uid = useId().replace(/:/g, '');
  const [geometry, setGeometry] = useState(null);
  const rafRef = useRef(0);

  const measure = useCallback(() => {
    const frame = frameRef.current;
    if (!frame) return false;

    const fr = frame.getBoundingClientRect();
    if (fr.width < 1 || fr.height < 1) return false;

    const tierEls = [...frame.querySelectorAll('.tcx-tier')];
    const tierSegments = tierEls.map((tierEl) => {
      const anchor = tierEl.querySelector('.tcx-node--root, .tcx-node--hub');
      const peers = [...tierEl.querySelectorAll('.tcx-node--peer, .tcx-node--leaf')];
      if (!anchor || !peers.length) return null;

      const ar = anchor.getBoundingClientRect();
      const anchorPt = {
        x: ar.right - fr.left,
        y: ar.top + ar.height / 2 - fr.top,
      };

      const peerPts = peers.map((peer) => {
        const pr = peer.getBoundingClientRect();
        return {
          x: pr.left - fr.left,
          y: pr.top + pr.height / 2 - fr.top,
          active: peer.classList.contains('is-active'),
        };
      });

      const junctionX = anchorPt.x + Math.max(10, (peerPts[0].x - anchorPt.x) * 0.22);
      const busY = anchorPt.y;
      const busEnd = peerPts[peerPts.length - 1].x - 6;

      return {
        anchor: anchorPt,
        junction: { x: junctionX, y: busY },
        bus: { x1: junctionX, y1: busY, x2: busEnd, y2: busY },
        peers: peerPts,
        active: anchor.classList.contains('is-active') || peerPts.some((p) => p.active),
      };
    }).filter(Boolean);

    let spine = null;
    if (hasSubTiers && tierSegments.length > 1) {
      const spineX = Math.min(
        ...tierSegments.slice(1).map((s) => s.anchor.x - 14),
        tierSegments[0].anchor.x - 6,
      );
      const rootY = tierSegments[0].anchor.y;
      const childAnchors = tierSegments.slice(1).map((s) => s.anchor);
      const childYs = childAnchors.map((a) => a.y);
      spine = {
        x: spineX,
        y1: rootY,
        y2: Math.max(...childYs),
        hooks: childAnchors.map((a) => ({
          x1: spineX,
          y1: a.y,
          x2: a.x - 4,
          y2: a.y,
          active: tierEls.slice(1).some((el) => el.querySelector('.tcx-node.is-active')),
        })),
      };
    }

    setGeometry({ tierSegments, spine, width: fr.width, height: fr.height });
    return true;
  }, [frameRef, hasSubTiers]);

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
  }, [scheduleMeasure, tiersKey, hasSubTiers]);

  if (!geometry) return null;

  const { tierSegments, spine, width, height } = geometry;
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
        <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="var(--text-muted)" stopOpacity="0.22" />
          <stop offset="45%" stopColor="var(--text-muted)" stopOpacity="0.55" />
          <stop offset="100%" stopColor="var(--text-muted)" stopOpacity="0.3" />
        </linearGradient>
        <linearGradient id={gradActiveId} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="var(--color-primary)" stopOpacity="0.35" />
          <stop offset="50%" stopColor="var(--color-primary)" stopOpacity="1" />
          <stop offset="100%" stopColor="var(--color-primary)" stopOpacity="0.45" />
        </linearGradient>
        <filter id={glowId} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2.2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {spine ? (
        <g className="tcx-wire tcx-wire--spine">
          <line
            x1={spine.x}
            y1={spine.y1}
            x2={spine.x}
            y2={spine.y2}
            stroke={`url(#${gradId})`}
            strokeWidth="1.5"
            strokeDasharray="5 4"
            strokeLinecap="round"
          />
          {spine.hooks.map((hook, i) => (
            <path
              key={`hook-${i}`}
              d={`M ${hook.x1} ${hook.y1} H ${hook.x2}`}
              fill="none"
              stroke={hook.active ? `url(#${gradActiveId})` : `url(#${gradId})`}
              strokeWidth={hook.active ? 2 : 1.5}
              strokeLinecap="round"
              filter={hook.active ? `url(#${glowId})` : undefined}
            />
          ))}
        </g>
      ) : null}

      {tierSegments.map((seg, tierIdx) => {
        const stroke = seg.active ? `url(#${gradActiveId})` : `url(#${gradId})`;
        const sw = seg.active ? 2.25 : 1.65;

        return (
          <g key={`tier-wire-${tierIdx}`} className="tcx-wire tcx-wire--tier">
            <path
              d={`M ${seg.anchor.x} ${seg.anchor.y} H ${seg.junction.x}`}
              fill="none"
              stroke={stroke}
              strokeWidth={sw}
              strokeLinecap="round"
              filter={seg.active ? `url(#${glowId})` : undefined}
            />
            <circle
              cx={seg.junction.x}
              cy={seg.junction.y}
              r={seg.active ? 4.2 : 3.2}
              className={`tcx-wire-junction${seg.active ? ' is-active' : ''}`}
              filter={seg.active ? `url(#${glowId})` : undefined}
            />
            <circle
              cx={seg.junction.x}
              cy={seg.junction.y}
              r={1.4}
              className="tcx-wire-junction__core"
            />
            <line
              x1={seg.bus.x1}
              y1={seg.bus.y1}
              x2={seg.bus.x2}
              y2={seg.bus.y2}
              stroke={stroke}
              strokeWidth={sw}
              strokeLinecap="round"
              filter={seg.active ? `url(#${glowId})` : undefined}
            />
            {seg.peers.map((peer, i) => (
              <g key={`peer-tap-${tierIdx}-${i}`}>
                <line
                  x1={peer.x - 5}
                  y1={seg.bus.y1}
                  x2={peer.x}
                  y2={peer.y}
                  stroke={peer.active ? `url(#${gradActiveId})` : `url(#${gradId})`}
                  strokeWidth={peer.active ? 2 : 1.5}
                  strokeLinecap="round"
                  filter={peer.active ? `url(#${glowId})` : undefined}
                />
                <circle
                  cx={peer.x - 5}
                  cy={seg.bus.y1}
                  r={peer.active ? 2.8 : 2}
                  className={`tcx-wire-tap${peer.active ? ' is-active' : ''}`}
                />
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
  initialFilters = {},
  isChipActive,
  onChipClick,
  onResetScope,
}) {
  const frameRef = useRef(null);

  const tree = useMemo(
    () => buildTreeTiers(chips, resolveRootId(chips, initialFilters), scopeLabel),
    [chips, initialFilters, scopeLabel],
  );

  if (!tree) return null;

  const { topTier, subTiers } = tree;
  const hasSubTiers = subTiers.length > 0;
  const tiersKey = `${topTier.anchor.id}-${subTiers.map((t) => t.hub.id).join(',')}-${chips.length}`;

  return (
    <section
      className={`tcx-map${hasSubTiers ? ' tcx-map--layered' : ''}`}
      aria-label="Folder taxonomy map"
    >
      <div className="tcx-tree-frame" ref={frameRef}>
        <TaxonomyWireCanvas
          frameRef={frameRef}
          hasSubTiers={hasSubTiers}
          tiersKey={tiersKey}
        />
        <div className="tcx-tree">
          <div className="tcx-tree__tiers">
            <TreeTier
              tier={topTier}
              tierIndex={0}
              isChipActive={isChipActive}
              onChipClick={onChipClick}
              onAnchorClick={onResetScope}
              peerVariant="peer"
            />
            {subTiers.map((tier) => (
              <TreeTier
                key={tier.hub.id}
                tier={{ anchor: tier.hub, peers: tier.peers }}
                tierIndex={1}
                isChipActive={isChipActive}
                onChipClick={onChipClick}
                onAnchorClick={() => onChipClick(tier.hub)}
                peerVariant="leaf"
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
