import { useCallback, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { PIPELINE_3D_METADATA } from '@/data/imageProcessingPipelineContent.js';

/**
 * LUMI-centric data flow:
 * - Raw copies: LOLA → Allas, P-drive, personal HD (parallel)
 * - Primary: raw upload into LUMI; full pipeline + output stay inside LUMI
 * - After analysis: LUMI distributes to Allas, P-drive, personal HD; published → Databank
 */

const COLUMNS = [
  { id: 'source', label: 'Source' },
  { id: 'storage', label: 'Storage' },
  { id: 'lumi', label: 'LUMI · raw → compute → output' },
  { id: 'publish', label: 'Publish' },
];

const STORAGE_NODE_IDS = ['allas', 'pdrive', 'external'];
const PROCESS_MICRO_IDS = ['illum', 'stitch', 'seg', 'quant', 'filter'];

const FLOW_EDGES = [
  { from: 'lola', to: 'lumi-in', kind: 'primary', z: 3 },
  { from: 'lola', to: 'allas', kind: 'raw-copy', z: 0 },
  { from: 'lola', to: 'pdrive', kind: 'raw-copy', z: 0 },
  { from: 'lola', to: 'external', kind: 'raw-copy', z: 0 },
  { from: 'lumi', to: 'allas', kind: 'distribute', z: 1 },
  { from: 'lumi', to: 'pdrive', kind: 'distribute', z: 1 },
  { from: 'lumi', to: 'external', kind: 'distribute', z: 1 },
  { from: 'lumi', to: 'databank', kind: 'publish', z: 2 },
];

/** Shared geometry for every data-flow arrow. */
const FLOW_BEND = 16;

const SYNTHETIC_NODES = {
  databank: {
    id: 'databank',
    zone: 'qc',
    label: 'CSC Databank',
    short: 'Databank',
    color: '#facc15',
    detail: 'Long-term archive when a dataset is approved and published.',
    meta: { trigger: 'Published?', role: 'Public archive' },
  },
};

const DISPLAY_LABELS = {
  lola: {
    title: 'Raw data',
    subtitle: 'from LOLA → Allas · P-drive · personal HD · LUMI',
  },
  allas: { title: 'Allas', subtitle: 'raw copy + results' },
  pdrive: { title: 'P-drive', subtitle: 'raw copy + results' },
  external: { title: 'Personal HD', subtitle: 'raw copy + results' },
  lumi: { title: 'LUMI HPC', subtitle: 'orchestrates full pipeline' },
  archive: { title: 'Output', subtitle: 'inside LUMI' },
};

const STORAGE_FLOW_IN = [
  { kind: 'raw-copy', label: 'raw ← LOLA' },
  { kind: 'distribute', label: 'results ← LUMI' },
];

const SVG_VIEWBOX = { width: 1000, height: 520 };
const FLOW_ANCHOR_IDS = ['lola', 'allas', 'pdrive', 'external', 'lumi', 'lumi-in', 'databank'];
const FLOW_ANCHOR_ID_SET = new Set(FLOW_ANCHOR_IDS);

function measureFlowAnchors(boardEl) {
  if (!boardEl) return null;

  const boardRect = boardEl.getBoundingClientRect();
  if (!boardRect.width || !boardRect.height) return null;

  const scaleX = SVG_VIEWBOX.width / boardRect.width;
  const scaleY = SVG_VIEWBOX.height / boardRect.height;
  const anchors = {};

  for (const id of FLOW_ANCHOR_IDS) {
    const el = boardEl.querySelector(`[data-flow-anchor="${id}"]`);
    if (!el) continue;

    const rect = el.getBoundingClientRect();
    const left = (rect.left - boardRect.left) * scaleX;
    const right = (rect.right - boardRect.left) * scaleX;
    const top = (rect.top - boardRect.top) * scaleY;
    const bottom = (rect.bottom - boardRect.top) * scaleY;

    anchors[id] = {
      x: (left + right) / 2,
      y: (top + bottom) / 2,
      left,
      right,
      top,
      bottom,
    };
  }

  return anchors;
}

function anchorsReady(anchors) {
  return Boolean(anchors && FLOW_ANCHOR_IDS.every((id) => anchors[id]));
}

function buildStorageNodes(metadata) {
  const byId = new Map((metadata.nodes || []).map((node) => [node.id, node]));
  const stacks = { allas: 'top', pdrive: 'mid', external: 'bot' };

  return STORAGE_NODE_IDS.map((id) => {
    const base = byId.get(id);
    if (!base) return null;
    const copy = DISPLAY_LABELS[id];
    return {
      ...base,
      displayTitle: copy?.title || base.short,
      displaySubtitle: copy?.subtitle || null,
      layoutStack: stacks[id],
    };
  }).filter(Boolean);
}

function buildLumiHub(metadata) {
  const lumi = metadata.nodes?.find((node) => node.id === 'lumi');
  const copy = DISPLAY_LABELS.lumi;
  return {
    ...lumi,
    id: 'lumi',
    displayTitle: copy?.title || 'LUMI HPC',
    displaySubtitle: copy?.subtitle,
  };
}

function buildOutputNode(metadata) {
  const archive = metadata.nodes?.find((node) => node.id === 'archive');
  if (!archive) return null;
  const copy = DISPLAY_LABELS.archive;
  return {
    ...archive,
    displayTitle: copy?.title || 'Output',
    displaySubtitle: copy?.subtitle,
    isOutput: true,
  };
}

function buildMicroNodes(metadata) {
  const byId = new Map((metadata.nodes || []).map((node) => [node.id, node]));
  return PROCESS_MICRO_IDS.map((id) => {
    const base = byId.get(id);
    if (!base) return null;
    return { ...base, isMicro: true };
  }).filter(Boolean);
}

function pathStraight(sx, sy, ex, ey) {
  return `M ${sx} ${sy} L ${ex} ${ey}`;
}

/** Orthogonal fan-out: exit source → bend → align to target row → enter target. */
function pathFanOut(sx, sy, ex, ey) {
  const bend = FLOW_BEND;
  return `M ${sx} ${sy} L ${sx + bend} ${sy} L ${sx + bend} ${ey} L ${ex} ${ey}`;
}

/** Orthogonal bus lane above storage (primary upload only). */
function pathBusLane(sx, sy, ex, ey, busY) {
  const bend = FLOW_BEND;
  return `M ${sx} ${sy} L ${sx + bend} ${sy} L ${sx + bend} ${busY} L ${ex - bend} ${busY} L ${ex - bend} ${ey} L ${ex} ${ey}`;
}

function primaryBusY(lola, storageAnchors) {
  const topStorage = storageAnchors.reduce((min, node) => (node && node.top < min ? node.top : min), lola.top);
  return Math.max(14, topStorage - 26);
}

function edgePath(edge, anchors) {
  const from = anchors?.[edge.from];
  const to = anchors?.[edge.to];
  if (!from || !to) return '';

  if (edge.kind === 'primary') {
    return pathBusLane(from.right, from.y, to.left, to.y, primaryBusY(from, [anchors.allas, anchors.pdrive, anchors.external]));
  }
  if (edge.kind === 'raw-copy') {
    return pathFanOut(from.right, from.y, to.left, to.y);
  }
  if (edge.kind === 'distribute') {
    return pathStraight(from.left, to.y, to.right, to.y);
  }
  if (edge.kind === 'publish') {
    return pathStraight(from.right, to.y, to.left, to.y);
  }

  return pathStraight(from.right, from.y, to.left, to.y);
}

function StorageRow({ node, selected, onSelect }) {
  return (
    <div className="ipp-pipeline-25d__storage-row">
      <IsoBlock node={node} selected={selected} onSelect={onSelect} />
      <div className="ipp-pipeline-25d__storage-flows" aria-label={`Data flows for ${node.displayTitle}`}>
        {STORAGE_FLOW_IN.map((flow) => (
          <span
            key={`${node.id}-${flow.kind}`}
            className={`ipp-pipeline-25d__storage-flow ipp-pipeline-25d__storage-flow--${flow.kind}`}
          >
            {flow.label}
          </span>
        ))}
      </div>
    </div>
  );
}

function IsoBlock({ node, selected, onSelect, className = '' }) {
  const active = selected === node.id;

  return (
    <button
      type="button"
      className={`ipp-iso-block${active ? ' ipp-iso-block--active' : ''}${node.isMicro ? ' ipp-iso-block--micro' : ''}${node.isOutput ? ' ipp-iso-block--output' : ''} ${className}`.trim()}
      style={{ '--block-color': node.color }}
      onClick={(event) => {
        event.stopPropagation();
        onSelect(node.id);
      }}
      aria-pressed={active}
      aria-label={node.displayTitle || node.label}
      data-flow-anchor={FLOW_ANCHOR_ID_SET.has(node.id) ? node.id : undefined}
    >
      {node.isMicro ? (
        <span className="ipp-iso-block__micro">{node.short}</span>
      ) : (
        <>
          <span className="ipp-iso-block__title">{node.displayTitle || node.short}</span>
          {node.displaySubtitle ? <span className="ipp-iso-block__subtitle">{node.displaySubtitle}</span> : null}
        </>
      )}
    </button>
  );
}

function FlowSvg({ selected, anchors }) {
  const ready = anchorsReady(anchors);

  return (
    <svg className="ipp-iso-flow" viewBox={`0 0 ${SVG_VIEWBOX.width} ${SVG_VIEWBOX.height}`} aria-hidden>
      <defs>
        <marker id="ipp-arrow-flow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
          <path d="M0,0 L7,3.5 L0,7 Z" fill="context-stroke" />
        </marker>
      </defs>

      {[...FLOW_EDGES]
        .sort((a, b) => (a.z ?? 0) - (b.z ?? 0))
        .map((edge) => {
          if (!ready) return null;

          const active =
            selected === edge.from ||
            selected === edge.to ||
            (edge.to === 'lumi-in' && selected === 'lumi');
          const path = edgePath(edge, anchors);
          if (!path) return null;

          return (
            <g key={`${edge.from}-${edge.to}-${edge.kind}`} className={active ? 'ipp-iso-flow__edge--active' : ''}>
              <path
                d={path}
                className={`ipp-iso-flow__path ipp-iso-flow__path--${edge.kind}`}
                markerEnd="url(#ipp-arrow-flow)"
              />
            </g>
          );
        })}
    </svg>
  );
}

function MetadataPanel({ node, zonesById }) {
  const zone = zonesById.get(node.zone);
  const entries = Object.entries(node.meta || {});

  return (
    <aside className="ipp-pipeline-3d__metadata-panel" style={{ '--node-color': node.color }}>
      <div className="ipp-pipeline-3d__metadata-kicker">Selected node</div>
      <h4>{node.displayTitle || node.label}</h4>
      <p>{node.detail}</p>

      <div className="ipp-pipeline-3d__zone-stack">
        {zone ? <span className="ipp-pipeline-3d__zone-pill">{zone.label}</span> : null}
        {node.id === 'lola' ? (
          <span className="ipp-pipeline-3d__zone-pill">raw saved to Allas · P-drive · personal HD</span>
        ) : null}
        {node.id === 'lumi' ? <span className="ipp-pipeline-3d__zone-pill">controls raw → output</span> : null}
        {STORAGE_NODE_IDS.includes(node.id) ? (
          <>
            <span className="ipp-pipeline-3d__zone-pill">raw copy from LOLA</span>
            <span className="ipp-pipeline-3d__zone-pill">results from LUMI</span>
          </>
        ) : null}
        {node.isOutput ? <span className="ipp-pipeline-3d__zone-pill">inside LUMI</span> : null}
      </div>

      {entries.length ? (
        <dl className="ipp-pipeline-3d__metadata-list">
          {entries.map(([key, value]) => (
            <div key={key}>
              <dt>{key}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      ) : null}
    </aside>
  );
}

export function Pipeline3DScene({ ariaLabel, metadata = PIPELINE_3D_METADATA }) {
  const sourceNode = useMemo(() => {
    const lola = metadata.nodes?.find((node) => node.id === 'lola');
    const copy = DISPLAY_LABELS.lola;
    return {
      ...lola,
      displayTitle: copy.title,
      displaySubtitle: copy.subtitle,
    };
  }, [metadata]);

  const storageNodes = useMemo(() => buildStorageNodes(metadata), [metadata]);
  const lumiHub = useMemo(() => buildLumiHub(metadata), [metadata]);
  const outputNode = useMemo(() => buildOutputNode(metadata), [metadata]);
  const microNodes = useMemo(() => buildMicroNodes(metadata), [metadata]);
  const publishNode = useMemo(() => SYNTHETIC_NODES.databank, []);

  const allNodes = useMemo(
    () => [sourceNode, ...storageNodes, lumiHub, outputNode, ...microNodes, publishNode].filter(Boolean),
    [sourceNode, storageNodes, lumiHub, outputNode, microNodes, publishNode],
  );

  const [selected, setSelected] = useState('lumi');
  const [flowAnchors, setFlowAnchors] = useState(null);
  const boardRef = useRef(null);
  const selectedNode = allNodes.find((node) => node.id === selected) || lumiHub;
  const zonesById = useMemo(() => new Map((metadata.zones || []).map((zone) => [zone.id, zone])), [metadata.zones]);

  const measureAnchors = useCallback(() => {
    const measured = measureFlowAnchors(boardRef.current);
    if (measured) setFlowAnchors(measured);
  }, []);

  useLayoutEffect(() => {
    measureAnchors();

    const board = boardRef.current;
    if (!board) return undefined;

    const observer = new ResizeObserver(() => measureAnchors());
    observer.observe(board);

    window.addEventListener('resize', measureAnchors);
    return () => {
      observer.disconnect();
      window.removeEventListener('resize', measureAnchors);
    };
  }, [measureAnchors, sourceNode, storageNodes, lumiHub, publishNode, selected]);

  return (
    <div className="ipp-pipeline-3d ipp-pipeline-25d" role="img" aria-label={ariaLabel || metadata.title}>
      <div className="ipp-pipeline-3d__topbar">
        <div>
          <span className="ipp-pipeline-3d__kicker">LUMI-centric data flow</span>
          <strong>{metadata.title}</strong>
        </div>
        <div className="ipp-pipeline-3d__mini-metrics ipp-pipeline-25d__flow-legend" aria-label="Data flow legend">
          <span className="ipp-pipeline-25d__legend-item ipp-pipeline-25d__legend-item--primary">raw upload</span>
          <span className="ipp-pipeline-25d__legend-item ipp-pipeline-25d__legend-item--raw">raw copy</span>
          <span className="ipp-pipeline-25d__legend-item ipp-pipeline-25d__legend-item--distribute">results</span>
          <span className="ipp-pipeline-25d__legend-item ipp-pipeline-25d__legend-item--publish">published</span>
        </div>
      </div>

      <div className="ipp-pipeline-3d__stage">
        <div className="ipp-pipeline-25d__viewport">
          <div className="ipp-pipeline-25d__board" ref={boardRef}>
            <FlowSvg selected={selected} anchors={flowAnchors} />

            <div className="ipp-pipeline-25d__columns ipp-pipeline-25d__columns--lumi-hub">
              <div className="ipp-pipeline-25d__column ipp-pipeline-25d__column--source">
                <div className="ipp-pipeline-25d__column-head">Source</div>
                <div className="ipp-pipeline-25d__stack">
                  <IsoBlock node={sourceNode} selected={selected} onSelect={setSelected} />
                </div>
              </div>

              <div className="ipp-pipeline-25d__column ipp-pipeline-25d__column--storage">
                <div className="ipp-pipeline-25d__column-head">Storage · raw saved on all</div>
                <div className="ipp-pipeline-25d__stack ipp-pipeline-25d__stack--triple">
                  {storageNodes.map((node) => (
                    <StorageRow key={node.id} node={node} selected={selected} onSelect={setSelected} />
                  ))}
                </div>
              </div>

              <div className="ipp-pipeline-25d__column ipp-pipeline-25d__column--lumi">
                <div
                  role="group"
                  aria-label="LUMI HPC pipeline hub"
                  data-flow-anchor="lumi"
                  className={`ipp-pipeline-25d__lumi-zone${selected === 'lumi' ? ' ipp-pipeline-25d__lumi-zone--active' : ''}`}
                  onClick={() => setSelected('lumi')}
                >
                  <div className="ipp-pipeline-25d__lumi-zone-title">
                    <span>LUMI HPC</span>
                    <span>Snakemake · SLURM · scratch/Lustre</span>
                  </div>

                  <div className="ipp-pipeline-25d__internal-flow" aria-label="Pipeline inside LUMI">
                    <span
                      className="ipp-pipeline-25d__flow-pill ipp-pipeline-25d__flow-pill--raw"
                      data-flow-anchor="lumi-in"
                    >
                      Raw in
                    </span>
                    <span className="ipp-pipeline-25d__flow-arrow" aria-hidden>
                      →
                    </span>
                    <div className="ipp-pipeline-25d__micro-row">
                      {microNodes.map((node, index) => (
                        <span key={node.id} style={{ display: 'contents' }}>
                          {index > 0 ? (
                            <span className="ipp-pipeline-25d__flow-arrow ipp-pipeline-25d__flow-arrow--micro" aria-hidden>
                              →
                            </span>
                          ) : null}
                          <IsoBlock node={node} selected={selected} onSelect={setSelected} />
                        </span>
                      ))}
                    </div>
                    <span className="ipp-pipeline-25d__flow-arrow" aria-hidden>
                      →
                    </span>
                    {outputNode ? (
                      <IsoBlock node={outputNode} selected={selected} onSelect={setSelected} />
                    ) : null}
                  </div>

                  <p className="ipp-pipeline-25d__lumi-foot">
                    On ingest, LOLA saves raw copies to Allas · P-drive · personal HD. After analysis, LUMI sends
                    results to the same three; published data goes to Databank.
                  </p>
                </div>
              </div>

              <div className="ipp-pipeline-25d__column ipp-pipeline-25d__column--publish">
                <div className="ipp-pipeline-25d__column-head">Publish</div>
                <div className="ipp-pipeline-25d__stack">
                  <IsoBlock node={publishNode} selected={selected} onSelect={setSelected} />
                </div>
              </div>
            </div>
          </div>
        </div>

        {selectedNode ? <MetadataPanel node={selectedNode} zonesById={zonesById} /> : null}
      </div>

      <p className="ipp-pipeline-3d__hint">
        Every acquisition: <strong>LOLA</strong> saves raw data to <strong>Allas</strong>, <strong>P-drive</strong>, and{' '}
        <strong>personal HD</strong>, and uploads the working copy into <strong>LUMI</strong>. LUMI runs the full pipeline
        with <strong>output inside</strong>, then returns results to all three storage targets; published datasets go to{' '}
        <strong>Databank</strong>.
      </p>
    </div>
  );
}

export default Pipeline3DScene;
