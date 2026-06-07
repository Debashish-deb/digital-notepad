import { BrainCircuit } from 'lucide-react';

const ORBITS = [
  { id: 1, size: '100%', duration: 22, delay: 0, cell: 'md', tone: 'rose' },
  { id: 2, size: '80%', duration: 17, delay: -5, cell: 'lg', tone: 'coral' },
  { id: 3, size: '60%', duration: 13, delay: -9, cell: 'md', tone: 'magenta' },
  { id: 4, size: '44%', duration: 9, delay: -3, cell: 'sm', tone: 'pink' },
];

function NeuralNetworkSvg() {
  return (
    <svg className="ai3d-solar__neural-net" viewBox="0 0 120 120" aria-hidden="true">
      <g className="ai3d-solar__neural-lines">
        <line x1="60" y1="60" x2="24" y2="34" />
        <line x1="60" y1="60" x2="96" y2="30" />
        <line x1="60" y1="60" x2="98" y2="72" />
        <line x1="60" y1="60" x2="28" y2="88" />
        <line x1="60" y1="60" x2="60" y2="18" />
        <line x1="24" y1="34" x2="42" y2="22" />
        <line x1="96" y1="30" x2="78" y2="16" />
        <line x1="98" y1="72" x2="104" y2="92" />
        <line x1="28" y1="88" x2="18" y2="102" />
      </g>
      <g className="ai3d-solar__neural-nodes">
        <circle cx="60" cy="60" r="3.2" />
        <circle cx="24" cy="34" r="2.2" />
        <circle cx="96" cy="30" r="2.2" />
        <circle cx="98" cy="72" r="2.2" />
        <circle cx="28" cy="88" r="2.2" />
        <circle cx="60" cy="18" r="1.8" />
        <circle cx="42" cy="22" r="1.4" />
        <circle cx="78" cy="16" r="1.4" />
        <circle cx="104" cy="92" r="1.4" />
        <circle cx="18" cy="102" r="1.4" />
      </g>
    </svg>
  );
}

function DnaHelixSvg() {
  return (
    <svg className="ai3d-solar__dna" viewBox="0 0 48 120" aria-hidden="true">
      <path className="ai3d-solar__dna-strand ai3d-solar__dna-strand--a" d="M12,4 Q28,20 12,36 Q-4,52 12,68 Q28,84 12,100 Q-4,116 12,116" />
      <path className="ai3d-solar__dna-strand ai3d-solar__dna-strand--b" d="M36,4 Q20,20 36,36 Q52,52 36,68 Q20,84 36,100 Q52,116 36,116" />
      {[16, 32, 48, 64, 80, 96].map((y) => (
        <line key={y} className="ai3d-solar__dna-rung" x1="14" y1={y} x2="34" y2={y} />
      ))}
    </svg>
  );
}

function CancerCell({ size, tone }) {
  return (
    <div className={`ai3d-cancer-cell ai3d-cancer-cell--${size} ai3d-cancer-cell--${tone}`}>
      <span className="ai3d-cancer-cell__membrane" />
      <span className="ai3d-cancer-cell__bleb ai3d-cancer-cell__bleb--1" />
      <span className="ai3d-cancer-cell__bleb ai3d-cancer-cell__bleb--2" />
      <span className="ai3d-cancer-cell__cytoplasm">
        <span className="ai3d-cancer-cell__mito" />
        <span className="ai3d-cancer-cell__mito ai3d-cancer-cell__mito--b" />
      </span>
      <span className="ai3d-cancer-cell__nucleus">
        <span className="ai3d-cancer-cell__nucleolus" />
        <span className="ai3d-cancer-cell__chromatin" />
      </span>
    </div>
  );
}

export default function AiSolarBrainVisual({ compact = false }) {
  const brainSize = compact ? 38 : 44;

  return (
    <div className={`ai3d-solar${compact ? ' ai3d-solar--compact' : ''}`}>
      <div className="ai3d-solar__field" aria-hidden="true">
        <span className="ai3d-solar__hex ai3d-solar__hex--1" />
        <span className="ai3d-solar__hex ai3d-solar__hex--2" />
        <span className="ai3d-solar__hex ai3d-solar__hex--3" />
      </div>

      <div className="ai3d-solar__scan" aria-hidden="true" />
      <div className="ai3d-solar__corona" aria-hidden="true" />
      <div className="ai3d-solar__glow" aria-hidden="true" />

      <DnaHelixSvg />

      {ORBITS.map((orbit) => (
        <div
          key={`trail-${orbit.id}`}
          className="ai3d-solar__trail"
          style={{ width: orbit.size, height: orbit.size }}
        />
      ))}

      {ORBITS.map((orbit) => (
        <div
          key={orbit.id}
          className="ai3d-solar__track"
          style={{
            width: orbit.size,
            height: orbit.size,
            animationDuration: `${orbit.duration}s`,
            animationDelay: `${orbit.delay}s`,
          }}
        >
          <CancerCell size={orbit.cell} tone={orbit.tone} />
        </div>
      ))}

      <div className="ai3d-solar__synapse-ring" aria-hidden="true" />
      <div className="ai3d-solar__synapse-ring ai3d-solar__synapse-ring--b" aria-hidden="true" />

      <div className="ai3d-solar__brain" aria-hidden="true">
        <NeuralNetworkSvg />
        <div className="ai3d-solar__brain-halo" />
        <div className="ai3d-solar__brain-core">
          <span className="ai3d-solar__brain-sulci" />
          <BrainCircuit size={brainSize} strokeWidth={1.6} />
          <span className="ai3d-solar__brain-scanline" />
        </div>
        <div className="ai3d-solar__brain-pulse" />
        <div className="ai3d-solar__brain-pulse ai3d-solar__brain-pulse--delayed" />
      </div>

      <div className="ai3d-solar__signals" aria-hidden="true">
        <span className="ai3d-solar__signal ai3d-solar__signal--1" />
        <span className="ai3d-solar__signal ai3d-solar__signal--2" />
        <span className="ai3d-solar__signal ai3d-solar__signal--3" />
      </div>

      <div className="ai3d-solar__ions" aria-hidden="true">
        {Array.from({ length: 8 }, (_, i) => (
          <span key={i} className={`ai3d-solar__ion ai3d-solar__ion--${i + 1}`} />
        ))}
      </div>
    </div>
  );
}
