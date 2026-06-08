import { useMemo, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, MeshDistortMaterial, Sphere, Instances, Instance } from '@react-three/drei';
import * as THREE from 'three';

const CELL_CLUSTERS = [
  { position: [-2.8, 0.75, -0.7], scale: 0.82, color: '#b84aa0', nucleus: '#6d3de8', marker: '#39ead7', speed: 1.05 },
  { position: [2.25, -0.35, 0.05], scale: 1.04, color: '#d85aa6', nucleus: '#5636c9', marker: '#ffcf6b', speed: 0.85 },
  { position: [0.18, 1.28, -1.28], scale: 0.66, color: '#ff7dbd', nucleus: '#7654ff', marker: '#4be1ff', speed: 1.35 },
  { position: [-0.65, -1.18, -0.15], scale: 0.9, color: '#a345d0', nucleus: '#4b2ea8', marker: '#61ffb8', speed: 0.95 },
  { position: [3.65, 1.05, -1.75], scale: 0.48, color: '#ff8cc7', nucleus: '#6845e8', marker: '#f7ff8a', speed: 1.55 },
];

const FIBER_STRANDS = [
  { position: [-2.9, -1.65, -2.1], rotation: [0.18, 0.2, -0.74], length: 4.8 },
  { position: [0.1, -2.08, -2.35], rotation: [0.2, -0.12, 0.22], length: 5.8 },
  { position: [2.65, -1.62, -2.1], rotation: [0.1, -0.22, 0.72], length: 4.3 },
  { position: [-3.45, 1.85, -2.6], rotation: [-0.2, 0.32, 0.64], length: 3.7 },
  { position: [1.85, 2.05, -2.4], rotation: [-0.18, -0.28, -0.48], length: 4.5 },
];

function seededRandom(seed) {
  let value = seed % 2147483647;
  return () => {
    value = (value * 16807) % 2147483647;
    return (value - 1) / 2147483646;
  };
}

function CancerCell({ position, color, nucleus, marker, scale = 1, speed = 1 }) {
  const groupRef = useRef();
  const rand = useMemo(() => seededRandom(Math.floor(scale * 1000) + color.length * 17), [color, scale]);

  // Pre-calculate instanced data for performance
  const surfaceBlebs = useMemo(() => {
    return Array.from({ length: 24 }, (_, i) => {
      const angle = rand() * Math.PI * 2;
      const radius = 0.95 + rand() * 0.2; // Push to surface
      const z = (rand() - 0.5) * 1.5;
      return {
        key: `bleb-${i}`,
        position: [Math.cos(angle) * radius, Math.sin(angle) * radius * 0.9, z],
        scale: 0.04 + rand() * 0.05,
      };
    });
  }, [rand]);

  const exosomes = useMemo(() => {
    return Array.from({ length: 35 }, (_, i) => {
      const angle = rand() * Math.PI * 2;
      const radius = 0.4 + rand() * 0.8;
      const z = (rand() - 0.5) * 1.2;
      return {
        key: `exo-${i}`,
        position: [Math.cos(angle) * radius, Math.sin(angle) * radius, z],
        scale: 0.015 + rand() * 0.025,
      };
    });
  }, [rand]);

  useFrame((state, delta) => {
    if (!groupRef.current) return;
    groupRef.current.rotation.y += delta * 0.08 * speed;
    groupRef.current.rotation.z = Math.sin(state.clock.elapsedTime * 0.25 * speed + position[0]) * 0.06;
  });

  return (
    <Float speed={speed * 0.8} rotationIntensity={0.3} floatIntensity={0.8}>
      <group ref={groupRef} position={position} scale={scale}>

        {/* Outer Cytoplasm - Lowered polycount, increased distortion for "blebbing" */}
        <Sphere args={[1.16, 48, 48]}>
          <MeshDistortMaterial
            color={color}
            distort={0.55} // Increased for aggressive cancer morphology
            speed={1.5}
            roughness={0.4}
            metalness={0.1}
            transparent
            opacity={0.15}
            emissive={color}
            emissiveIntensity={0.2}
            depthWrite={false}
          />
        </Sphere>

        {/* Inner Cytoskeleton */}
        <Sphere args={[0.98, 48, 48]}>
          <MeshDistortMaterial
            color={color}
            distort={0.65}
            speed={2.0}
            roughness={0.5}
            transparent
            opacity={0.6}
            emissive={color}
            emissiveIntensity={0.15}
          />
        </Sphere>

        {/* Multi-nucleated Core (Hallmark of Malignancy) */}
        <group position={[-0.1, 0.05, 0.15]}>
          {/* Primary irregular nucleus */}
          <Sphere args={[0.45, 32, 32]} position={[0, 0, 0]} scale={[1.2, 0.9, 0.8]}>
            <MeshDistortMaterial color={nucleus} distort={0.45} speed={1.1} roughness={0.3} emissive={nucleus} emissiveIntensity={0.4} />
          </Sphere>
          {/* Secondary nuclei (Pleomorphism) */}
          <Sphere args={[0.25, 24, 24]} position={[0.35, 0.2, -0.15]}>
            <MeshDistortMaterial color={nucleus} distort={0.5} speed={1.3} roughness={0.3} emissive={nucleus} emissiveIntensity={0.45} />
          </Sphere>
          <Sphere args={[0.2, 24, 24]} position={[-0.25, -0.25, 0.1]}>
            <MeshDistortMaterial color={"#8f5cff"} distort={0.4} speed={1.4} roughness={0.3} emissive={"#8f5cff"} emissiveIntensity={0.35} />
          </Sphere>
        </group>

        {/* Surface Proteins / Receptors (Instanced for Performance) */}
        <Instances limit={surfaceBlebs.length}>
          <sphereGeometry args={[1, 12, 12]} />
          <meshStandardMaterial color={marker} emissive={marker} emissiveIntensity={0.9} roughness={0.2} />
          {surfaceBlebs.map((bleb) => (
            <Instance key={bleb.key} position={bleb.position} scale={[bleb.scale, bleb.scale, bleb.scale]} />
          ))}
        </Instances>

        {/* Internal Shedding Vesicles / Lysosomes (Instanced) */}
        <Instances limit={exosomes.length}>
          <sphereGeometry args={[1, 10, 10]} />
          <meshStandardMaterial color="#ffe8f7" emissive="#ff9ed4" emissiveIntensity={0.4} transparent opacity={0.7} roughness={0.4} />
          {exosomes.map((exo) => (
            <Instance key={exo.key} position={exo.position} scale={[exo.scale, exo.scale, exo.scale]} />
          ))}
        </Instances>

      </group>
    </Float>
  );
}

function TissueRing() {
  const ref = useRef();
  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.z += delta * 0.05;
  });

  return (
    <group ref={ref} position={[0, -0.18, -1.82]} rotation={[Math.PI / 2.12, 0, 0]}>
      {/* Lowered segments on rings for background elements */}
      <mesh>
        <torusGeometry args={[3.25, 0.035, 8, 100]} />
        <meshStandardMaterial color="#40f4db" emissive="#35e9d2" emissiveIntensity={0.5} transparent opacity={0.6} depthWrite={false} />
      </mesh>
      <mesh rotation={[0, 0, 0.65]}>
        <torusGeometry args={[2.46, 0.022, 8, 80]} />
        <meshStandardMaterial color="#b58cff" emissive="#8b66ff" emissiveIntensity={0.38} transparent opacity={0.4} depthWrite={false} />
      </mesh>
    </group>
  );
}

function StromaFiber({ position, rotation, length }) {
  return (
    <Float speed={0.4} rotationIntensity={0.15} floatIntensity={0.2}>
      <mesh position={position} rotation={rotation}>
        <cylinderGeometry args={[0.015, 0.025, length, 8, 1, true]} />
        <meshStandardMaterial color="#ffbadc" emissive="#b95093" emissiveIntensity={0.2} transparent opacity={0.35} roughness={0.8} depthWrite={false} />
      </mesh>
    </Float>
  );
}

function BiomarkerMist() {
  const points = useMemo(() => {
    const count = 300; // Increased count safely because it's a Points material
    const rand = seededRandom(24519);
    const positions = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      positions[i * 3] = (rand() - 0.5) * 12.0;
      positions[i * 3 + 1] = (rand() - 0.5) * 8.0;
      positions[i * 3 + 2] = (rand() - 0.5) * 6.0 - 1.0;
    }
    return positions;
  }, []);

  const ref = useRef();
  useFrame((state) => {
    if (!ref.current) return;
    ref.current.rotation.z = Math.sin(state.clock.elapsedTime * 0.1) * 0.05;
    ref.current.position.y = Math.sin(state.clock.elapsedTime * 0.15) * 0.05;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[points, 3]} />
      </bufferGeometry>
      {/* Softened the mist to act as extracellular fluid/ascites */}
      <pointsMaterial size={0.04} color="#37f1df" transparent opacity={0.35} sizeAttenuation depthWrite={false} />
    </points>
  );
}

function SceneContent() {
  return (
    <>
      <ambientLight intensity={0.45} />
      <directionalLight position={[4, 6, 5]} intensity={1.3} color="#ffe6f7" />
      <directionalLight position={[-5, -2.5, 3.5]} intensity={0.6} color="#54f1e0" />
      <pointLight position={[0, 2.1, 2.4]} intensity={0.9} color="#ff78bd" />
      <pointLight position={[-3.2, -1.4, 1.5]} intensity={0.45} color="#7c5cff" />

      {CELL_CLUSTERS.map((cell) => (
        <CancerCell key={`${cell.position.join('-')}`} {...cell} />
      ))}

      <TissueRing />

      {FIBER_STRANDS.map((fiber, idx) => (
        <StromaFiber key={`fiber-${idx}`} {...fiber} />
      ))}

      <BiomarkerMist />
      <fog attach="fog" args={['#080718', 5.0, 16.0]} />
    </>
  );
}

export default function LoginOvarianScene() {
  return (
    <div className="login-scene" aria-hidden="true">
      <Canvas
        camera={{ position: [0, 0, 6.7], fov: 42 }}
        dpr={[1, 1.5]} // Capped DPR at 1.5 for background performance
        gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
        onCreated={({ gl }) => {
          gl.setClearColor(new THREE.Color('#080718'), 1);
          gl.outputColorSpace = THREE.SRGBColorSpace;
          gl.toneMapping = THREE.ACESFilmicToneMapping;
          gl.toneMappingExposure = 1.1;
        }}
      >
        <SceneContent />
      </Canvas>
      <div className="login-scene-veil" />
      <div className="login-scene-grid" />
      <div className="login-scene-vignette" />
    </div>
  );
}