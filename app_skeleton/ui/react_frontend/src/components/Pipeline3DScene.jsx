import { useMemo, useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, Html, Line, OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { PIPELINE_3D_METADATA } from '../data/imageProcessingPipelineContent.js';

/**
 * Tree-style 3D CyCIF / LUMI pipeline map.
 *
 * This component intentionally controls the diagram layout locally. The metadata file
 * can keep describing pipeline nodes, colors, zones, details and edges; this file decides
 * where those nodes sit visually.
 */
const CAMERA = {
  position: [0.4, 6.4, 11.8],
  zoom: 62,
  near: 0.1,
  far: 100,
};

const TREE_NODE_LAYOUT = {
  lola: { position: [-5.7, 1.12, 0], tier: 'Acquisition', branch: 'root' },

  external: { position: [-3.95, 2.18, -1.08], tier: 'Storage', branch: 'raw backup' },
  allas: { position: [-3.72, 1.12, 0], tier: 'Storage', branch: 'staging trunk' },
  pdrive: { position: [-3.95, 0.08, 1.08], tier: 'Storage', branch: 'shared review' },

  lumi: { position: [-1.95, 1.12, 0], tier: 'LUMI orchestration', branch: 'compute root' },

  illum: { position: [-0.48, 2.0, -0.74], tier: 'CPU processing', branch: 'correction' },
  stitch: { position: [0.78, 1.12, 0], tier: 'CPU processing', branch: 'registration' },

  seg: { position: [2.05, 2.0, 0.78], tier: 'GPU segmentation', branch: 'mask tree' },

  quant: { position: [3.25, 1.12, 0], tier: 'Single-cell analytics', branch: 'tables' },
  filter: { position: [4.35, 2.0, -0.76], tier: 'Single-cell analytics', branch: 'marker images' },

  qc: { position: [5.42, 1.12, 0.42], tier: 'QC gates', branch: 'human review' },
  archive: { position: [6.35, 0.3, -0.48], tier: 'Archive', branch: 'final package' },
};

const TREE_LEVELS = [
  { id: 'acq', label: '01 · Acquisition', x: -5.7, color: '#a78bfa' },
  { id: 'storage', label: '02 · Storage branches', x: -3.85, color: '#38bdf8' },
  { id: 'lumi', label: '03 · LUMI root', x: -1.95, color: '#22d3ee' },
  { id: 'cpu', label: '04 · CPU stages', x: 0.2, color: '#2dd4bf' },
  { id: 'gpu', label: '05 · GPU masks', x: 2.05, color: '#fbbf24' },
  { id: 'analysis', label: '06 · Quant / filter', x: 3.9, color: '#34d399' },
  { id: 'qc', label: '07 · QC / archive', x: 5.92, color: '#fb7185' },
];

function toVector(position) {
  return new THREE.Vector3(position[0], position[1], position[2]);
}

function midpoint(a, b, t = 0.5) {
  return a.clone().lerp(b, t);
}

function normalizeLabel(text) {
  return String(text || '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function getNodeLayout(node, index) {
  const known = TREE_NODE_LAYOUT[node.id];
  if (known) return known;

  // Fallback for future metadata nodes: place them as leaves after the main tree.
  if (Array.isArray(node.position)) {
    return { position: node.position, tier: normalizeLabel(node.zone), branch: 'metadata position' };
  }

  return {
    position: [-5.7 + index * 1.05, 1.12 + (index % 2 ? 0.62 : -0.36), index % 3 === 0 ? -0.72 : 0.72],
    tier: normalizeLabel(node.zone),
    branch: 'auto leaf',
  };
}

function NodeGeometry({ kind, scale }) {
  if (kind === 'hub') return <icosahedronGeometry args={[0.72 * scale, 2]} />;
  if (kind === 'gpu') return <octahedronGeometry args={[0.68 * scale, 1]} />;
  if (kind === 'storage' || kind === 'archive') return <cylinderGeometry args={[0.46 * scale, 0.52 * scale, 0.38 * scale, 48]} />;
  if (kind === 'qc') return <dodecahedronGeometry args={[0.58 * scale, 0]} />;
  if (kind === 'analysis') return <sphereGeometry args={[0.48 * scale, 36, 18]} />;
  return <boxGeometry args={[0.92 * scale, 0.44 * scale, 0.62 * scale]} />;
}

function DataRing({ color, scale, active }) {
  return (
    <group rotation={[Math.PI / 2, 0, 0]}>
      <mesh>
        <torusGeometry args={[0.62 * scale, active ? 0.018 : 0.012, 12, 72]} />
        <meshBasicMaterial color={color} transparent opacity={active ? 0.9 : 0.36} />
      </mesh>
      <mesh rotation={[0, 0, Math.PI / 2.8]}>
        <torusGeometry args={[0.78 * scale, active ? 0.014 : 0.009, 12, 72]} />
        <meshBasicMaterial color={color} transparent opacity={active ? 0.58 : 0.2} />
      </mesh>
    </group>
  );
}

function TreeLeafGlow({ color, active, scale }) {
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.62 * scale, 0]}>
        <ringGeometry args={[0.58 * scale, 0.72 * scale, 72]} />
        <meshBasicMaterial color={color} transparent opacity={active ? 0.34 : 0.16} side={THREE.DoubleSide} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.63 * scale, 0]}>
        <circleGeometry args={[0.45 * scale, 72]} />
        <meshBasicMaterial color={color} transparent opacity={active ? 0.1 : 0.045} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

function StageNode({ node, selected, onSelect }) {
  const active = selected === node.id;
  const scale = node.scale || 0.7;

  return (
    <group position={node.layoutPosition}>
      <Float speed={active ? 2.2 : 0.95} rotationIntensity={active ? 0.1 : 0.025} floatIntensity={active ? 0.22 : 0.045}>
        <TreeLeafGlow color={node.color} active={active} scale={scale} />

        <mesh
          onClick={(event) => {
            event.stopPropagation();
            onSelect(node.id);
          }}
          castShadow
          receiveShadow
        >
          <NodeGeometry kind={node.kind} scale={scale} />
          <meshPhysicalMaterial
            color={node.color}
            emissive={node.color}
            emissiveIntensity={active ? 0.88 : 0.24}
            metalness={0.44}
            roughness={0.16}
            clearcoat={0.88}
            transparent
            opacity={active ? 0.98 : 0.84}
          />
        </mesh>

        <DataRing color={node.color} scale={scale} active={active} />
        <pointLight color={node.color} intensity={active ? 1.75 : 0.46} distance={active ? 5.2 : 3.1} />

        <Html
          transform
          occlude
          center
          distanceFactor={active ? 7.4 : 8.6}
          position={[0, 0.86 * scale + 0.18, 0]}
          className="ipp-3d-html"
        >
          <button
            type="button"
            className={`ipp-3d-stage-label${active ? ' ipp-3d-stage-label--active' : ''}`}
            style={{ '--node-color': node.color }}
            onClick={(event) => {
              event.stopPropagation();
              onSelect(node.id);
            }}
          >
            <span className="ipp-3d-stage-label__short">{node.short}</span>
            <span className="ipp-3d-stage-label__name">{node.label}</span>
          </button>
        </Html>
      </Float>
    </group>
  );
}

function makeTreePath(edge, from, to) {
  const start = toVector(from.layoutPosition);
  const end = toVector(to.layoutPosition);

  // Return edges are still shown, but as a low, faint under-branch so the main tree stays readable.
  if (edge.arc === 'return') {
    const y = -0.55;
    return [
      start,
      new THREE.Vector3(start.x - 0.15, y, start.z),
      new THREE.Vector3(end.x + 0.15, y, end.z),
      end,
    ];
  }

  const deltaY = Math.abs(start.y - end.y);
  const deltaZ = Math.abs(start.z - end.z);
  const mainTrunk = deltaY < 0.32 && deltaZ < 0.32;

  if (mainTrunk) {
    const mid = midpoint(start, end, 0.5);
    mid.y += 0.06;
    return [start, mid, end];
  }

  const elbowX = start.x + (end.x - start.x) * 0.55;

  return [
    start,
    new THREE.Vector3(elbowX, start.y, start.z),
    new THREE.Vector3(elbowX, end.y, end.z),
    end,
  ];
}

function FlowParticle({ points, color, active, delay = 0 }) {
  const ref = useRef(null);

  useFrame(({ clock }) => {
    if (!ref.current || points.length < 2) return;

    const cycle = (clock.elapsedTime * (active ? 0.28 : 0.16) + delay * 0.043) % 1;
    const segments = points.length - 1;
    const segmentFloat = cycle * segments;
    const segmentIndex = Math.min(Math.floor(segmentFloat), segments - 1);
    const localT = segmentFloat - segmentIndex;

    ref.current.position.lerpVectors(points[segmentIndex], points[segmentIndex + 1], localT);
  });

  return (
    <mesh ref={ref}>
      <sphereGeometry args={[active ? 0.055 : 0.036, 16, 8]} />
      <meshBasicMaterial color={color} transparent opacity={active ? 0.92 : 0.52} />
    </mesh>
  );
}

function TreeEdge({ edge, nodesById, selected }) {
  const from = nodesById.get(edge.from);
  const to = nodesById.get(edge.to);
  const active = selected === edge.from || selected === edge.to;

  const points = useMemo(() => {
    if (!from || !to) return [];
    return makeTreePath(edge, from, to);
  }, [edge, from, to]);

  if (!from || !to || !points.length) return null;

  return (
    <group>
      <Line
        points={points}
        color={edge.color || '#22d3ee'}
        lineWidth={active ? 2.55 : 1.28}
        transparent
        opacity={edge.arc === 'return' ? (active ? 0.72 : 0.28) : active ? 0.9 : 0.46}
        dashed={edge.arc === 'return'}
        dashSize={0.24}
        gapSize={0.18}
      />
      <FlowParticle points={points} color={edge.color || '#22d3ee'} active={active} delay={edge.label?.length || 0} />
    </group>
  );
}

function TreeLevelMarker({ level }) {
  return (
    <group position={[level.x, -0.9, 1.92]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.34, 0.47, 72]} />
        <meshBasicMaterial color={level.color} transparent opacity={0.2} side={THREE.DoubleSide} />
      </mesh>
      <mesh position={[0, 0.02, -0.02]}>
        <boxGeometry args={[0.045, 1.72, 0.035]} />
        <meshBasicMaterial color={level.color} transparent opacity={0.22} />
      </mesh>
      <Html transform center distanceFactor={9.5} position={[0, -0.03, 0.54]} className="ipp-3d-html">
        <span className="ipp-3d-zone-label" style={{ '--node-color': level.color }}>
          {level.label}
        </span>
      </Html>
    </group>
  );
}

function TreeBackplane() {
  return (
    <group position={[0.36, -1.05, 0]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[13.6, 5.3, 64, 24]} />
        <meshStandardMaterial color="#06111f" metalness={0.28} roughness={0.58} transparent opacity={0.94} />
      </mesh>

      <gridHelper args={[13.6, 34, '#22d3ee', '#1e293b']} position={[0, 0.012, 0]} />

      {/* Main tree trunk rail */}
      <mesh rotation={[-Math.PI / 2, 0, Math.PI / 2]} position={[0.7, 0.028, 0]}>
        <cylinderGeometry args={[0.012, 0.012, 12.1, 16]} />
        <meshBasicMaterial color="#22d3ee" transparent opacity={0.26} />
      </mesh>

      {/* Storage branch rails */}
      <mesh rotation={[-Math.PI / 2, 0, 0.76]} position={[-4.78, 0.033, -0.55]}>
        <cylinderGeometry args={[0.01, 0.01, 1.72, 16]} />
        <meshBasicMaterial color="#38bdf8" transparent opacity={0.22} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, -0.76]} position={[-4.78, 0.033, 0.55]}>
        <cylinderGeometry args={[0.01, 0.01, 1.72, 16]} />
        <meshBasicMaterial color="#38bdf8" transparent opacity={0.22} />
      </mesh>

      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[-1.95, 0.034, 0]}>
        <ringGeometry args={[0.86, 0.89, 96]} />
        <meshBasicMaterial color="#22d3ee" transparent opacity={0.22} side={THREE.DoubleSide} />
      </mesh>

      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[2.05, 0.036, 0.78]}>
        <ringGeometry args={[0.74, 0.77, 96]} />
        <meshBasicMaterial color="#fbbf24" transparent opacity={0.25} side={THREE.DoubleSide} />
      </mesh>

      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[5.78, 0.037, 0]}>
        <ringGeometry args={[0.9, 0.93, 96]} />
        <meshBasicMaterial color="#fb7185" transparent opacity={0.2} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

function SceneContent({ metadata, selected, setSelected }) {
  const nodes = useMemo(
    () =>
      (metadata.nodes || []).map((node, index) => {
        const layout = getNodeLayout(node, index);
        return {
          ...node,
          layoutTier: layout.tier,
          layoutBranch: layout.branch,
          layoutPosition: layout.position,
        };
      }),
    [metadata.nodes],
  );

  const edges = metadata.edges || [];
  const nodesById = useMemo(() => new Map(nodes.map((node) => [node.id, node])), [nodes]);

  return (
    <>
      <color attach="background" args={['#020617']} />
      <fog attach="fog" args={['#020617', 10, 26]} />

      <ambientLight intensity={0.58} />
      <directionalLight position={[0, 7, 7]} intensity={1.35} castShadow />
      <pointLight position={[-5.8, 3.4, 2.4]} intensity={1.65} color="#a78bfa" />
      <pointLight position={[-1.8, 3.8, -2.3]} intensity={2.0} color="#22d3ee" />
      <pointLight position={[2.1, 3.4, 2.8]} intensity={1.6} color="#fbbf24" />
      <pointLight position={[5.6, 3.2, -2.2]} intensity={1.45} color="#fb7185" />

      <TreeBackplane />

      {TREE_LEVELS.map((level) => (
        <TreeLevelMarker key={level.id} level={level} />
      ))}

      {edges.map((edge) => (
        <TreeEdge key={`${edge.from}-${edge.to}-${edge.label}`} edge={edge} nodesById={nodesById} selected={selected} />
      ))}

      {nodes.map((node) => (
        <StageNode key={node.id} node={node} selected={selected} onSelect={setSelected} />
      ))}

      <OrbitControls
        enablePan
        enableZoom
        minDistance={5.2}
        maxDistance={18}
        maxPolarAngle={Math.PI / 2.05}
        target={[0.35, 0.62, 0]}
      />
    </>
  );
}

function MetadataPanel({ node, zonesById }) {
  const zone = zonesById.get(node.zone);
  const entries = Object.entries(node.meta || {});

  return (
    <aside className="ipp-pipeline-3d__metadata-panel" style={{ '--node-color': node.color }}>
      <div className="ipp-pipeline-3d__metadata-kicker">Selected tree node</div>
      <h4>{node.label}</h4>
      <p>{node.detail}</p>

      <div className="ipp-pipeline-3d__zone-stack">
        {zone ? <span className="ipp-pipeline-3d__zone-pill">{zone.label}</span> : null}
        {node.layoutTier ? <span className="ipp-pipeline-3d__zone-pill">{node.layoutTier}</span> : null}
        {node.layoutBranch ? <span className="ipp-pipeline-3d__zone-pill">{node.layoutBranch}</span> : null}
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
  const rawNodes = metadata.nodes || [];

  const nodes = useMemo(
    () =>
      rawNodes.map((node, index) => {
        const layout = getNodeLayout(node, index);
        return {
          ...node,
          layoutTier: layout.tier,
          layoutBranch: layout.branch,
          layoutPosition: layout.position,
        };
      }),
    [rawNodes],
  );

  const [selected, setSelected] = useState(
    nodes.find((node) => node.id === 'lola')?.id || nodes.find((node) => node.id === 'lumi')?.id || nodes[0]?.id,
  );

  const selectedNode = nodes.find((node) => node.id === selected) || nodes[0];
  const zonesById = useMemo(() => new Map((metadata.zones || []).map((zone) => [zone.id, zone])), [metadata.zones]);

  return (
    <div className="ipp-pipeline-3d" role="img" aria-label={ariaLabel || metadata.title}>
      <div className="ipp-pipeline-3d__topbar">
        <div>
          <span className="ipp-pipeline-3d__kicker">Interactive 3D research tree</span>
          <strong>{metadata.title}</strong>
        </div>
        <div className="ipp-pipeline-3d__mini-metrics" aria-label="Pipeline summary">
          <span>{nodes.length} nodes</span>
          <span>{metadata.edges?.length || 0} links</span>
          <span>{TREE_LEVELS.length} levels</span>
        </div>
      </div>

      <div className="ipp-pipeline-3d__stage">
        <div className="ipp-pipeline-3d__canvas-wrap">
          <Canvas orthographic camera={CAMERA} shadows dpr={[1, 1.75]} gl={{ antialias: true, alpha: false }}>
            <SceneContent metadata={{ ...metadata, nodes }} selected={selected} setSelected={setSelected} />
          </Canvas>
        </div>

        {selectedNode ? <MetadataPanel node={selectedNode} zonesById={zonesById} /> : null}
      </div>

      <p className="ipp-pipeline-3d__hint">
        Tree layout · left-to-right hierarchy · branch nodes show storage routes, compute stages, GPU masks, quantification,
        filtering, QC, and final archive.
      </p>
    </div>
  );
}

export default Pipeline3DScene;
