import { useMemo, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, MeshDistortMaterial, Sphere } from '@react-three/drei';
import * as THREE from 'three';

const CELL_CLUSTERS = [
  {
    position: [-2.8, 0.75, -0.7],
    scale: 0.82,
    color: '#b84aa0',
    nucleus: '#6d3de8',
    marker: '#39ead7',
    speed: 1.05,
  },
  {
    position: [2.25, -0.35, 0.05],
    scale: 1.04,
    color: '#d85aa6',
    nucleus: '#5636c9',
    marker: '#ffcf6b',
    speed: 0.85,
  },
  {
    position: [0.18, 1.28, -1.28],
    scale: 0.66,
    color: '#ff7dbd',
    nucleus: '#7654ff',
    marker: '#4be1ff',
    speed: 1.35,
  },
  {
    position: [-0.65, -1.18, -0.15],
    scale: 0.9,
    color: '#a345d0',
    nucleus: '#4b2ea8',
    marker: '#61ffb8',
    speed: 0.95,
  },
  {
    position: [3.65, 1.05, -1.75],
    scale: 0.48,
    color: '#ff8cc7',
    nucleus: '#6845e8',
    marker: '#f7ff8a',
    speed: 1.55,
  },
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

  const markers = useMemo(() => {
    return Array.from({ length: 18 }, (_, index) => {
      const angle = rand() * Math.PI * 2;
      const radius = 0.52 + rand() * 0.5;
      const z = (rand() - 0.5) * 0.84;

      return {
        key: `marker-${index}`,
        position: [
          Math.cos(angle) * radius,
          Math.sin(angle) * radius * 0.82,
          z,
        ],
        size: 0.035 + rand() * 0.045,
      };
    });
  }, [rand]);

  const speckles = useMemo(() => {
    return Array.from({ length: 26 }, (_, index) => {
      const angle = rand() * Math.PI * 2;
      const radius = 0.18 + rand() * 0.72;
      const z = (rand() - 0.5) * 0.72;

      return {
        key: `speckle-${index}`,
        position: [
          Math.cos(angle) * radius,
          Math.sin(angle) * radius * 0.88,
          z,
        ],
        size: 0.014 + rand() * 0.03,
      };
    });
  }, [rand]);

  useFrame((state, delta) => {
    if (!groupRef.current) return;

    groupRef.current.rotation.y += delta * 0.1 * speed;
    groupRef.current.rotation.z =
      Math.sin(state.clock.elapsedTime * 0.28 * speed + position[0]) * 0.08;
  });

  return (
    <Float speed={speed} rotationIntensity={0.28} floatIntensity={0.7}>
      <group ref={groupRef} position={position} scale={scale}>
        <Sphere args={[1.16, 64, 64]}>
          <MeshDistortMaterial
            color={color}
            distort={0.48}
            speed={1.25}
            roughness={0.38}
            metalness={0.04}
            transparent
            opacity={0.18}
            emissive={color}
            emissiveIntensity={0.28}
            depthWrite={false}
          />
        </Sphere>

        <Sphere args={[0.98, 64, 64]}>
          <MeshDistortMaterial
            color={color}
            distort={0.62}
            speed={1.7}
            roughness={0.48}
            metalness={0.08}
            transparent
            opacity={0.72}
            emissive={color}
            emissiveIntensity={0.2}
          />
        </Sphere>

        <group position={[-0.13, 0.04, 0.2]}>
          <Sphere args={[0.48, 48, 48]} scale={[1.16, 0.92, 0.78]}>
            <MeshDistortMaterial
              color={nucleus}
              distort={0.42}
              speed={1.25}
              roughness={0.32}
              metalness={0.05}
              emissive={nucleus}
              emissiveIntensity={0.42}
            />
          </Sphere>

          <Sphere args={[0.13, 24, 24]} position={[0.18, 0.04, 0.24]}>
            <meshStandardMaterial
              color="#e7d6ff"
              emissive="#9a78ff"
              emissiveIntensity={0.58}
              roughness={0.24}
            />
          </Sphere>

          <Sphere args={[0.09, 20, 20]} position={[-0.2, -0.11, 0.2]}>
            <meshStandardMaterial
              color="#ffd2ef"
              emissive="#ff8ed1"
              emissiveIntensity={0.42}
              roughness={0.28}
            />
          </Sphere>
        </group>

        <Sphere args={[0.28, 32, 32]} position={[0.62, 0.34, 0.15]} scale={[1.18, 0.86, 0.72]}>
          <MeshDistortMaterial
            color={nucleus}
            distort={0.36}
            speed={1.1}
            roughness={0.36}
            emissive={nucleus}
            emissiveIntensity={0.3}
          />
        </Sphere>

        <Sphere args={[0.22, 32, 32]} position={[-0.62, -0.38, 0.32]} scale={[0.95, 1.14, 0.8]}>
          <MeshDistortMaterial
            color="#8f5cff"
            distort={0.34}
            speed={1.25}
            roughness={0.34}
            emissive="#8f5cff"
            emissiveIntensity={0.28}
          />
        </Sphere>

        {markers.map((item) => (
          <Sphere key={item.key} args={[item.size, 12, 12]} position={item.position}>
            <meshStandardMaterial
              color={marker}
              emissive={marker}
              emissiveIntensity={0.85}
              roughness={0.22}
            />
          </Sphere>
        ))}

        {speckles.map((item) => (
          <Sphere key={item.key} args={[item.size, 10, 10]} position={item.position}>
            <meshStandardMaterial
              color="#ffe8f7"
              emissive="#ff9ed4"
              emissiveIntensity={0.35}
              transparent
              opacity={0.72}
              roughness={0.44}
            />
          </Sphere>
        ))}
      </group>
    </Float>
  );
}

function TissueRing() {
  const ref = useRef();

  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.z += delta * 0.075;
  });

  return (
    <group ref={ref} position={[0, -0.18, -1.82]} rotation={[Math.PI / 2.12, 0, 0]}>
      <mesh>
        <torusGeometry args={[3.25, 0.035, 16, 160]} />
        <meshStandardMaterial
          color="#40f4db"
          emissive="#35e9d2"
          emissiveIntensity={0.5}
          transparent
          opacity={0.62}
          depthWrite={false}
        />
      </mesh>

      <mesh rotation={[0, 0, 0.65]}>
        <torusGeometry args={[2.46, 0.022, 12, 140]} />
        <meshStandardMaterial
          color="#b58cff"
          emissive="#8b66ff"
          emissiveIntensity={0.38}
          transparent
          opacity={0.42}
          depthWrite={false}
        />
      </mesh>

      <mesh rotation={[0, 0, -0.48]}>
        <torusGeometry args={[4.05, 0.018, 12, 180]} />
        <meshStandardMaterial
          color="#ff88c8"
          emissive="#ff66b5"
          emissiveIntensity={0.36}
          transparent
          opacity={0.36}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}

function StromaFiber({ position, rotation, length }) {
  return (
    <Float speed={0.55} rotationIntensity={0.12} floatIntensity={0.25}>
      <mesh position={position} rotation={rotation}>
        <cylinderGeometry args={[0.018, 0.035, length, 12, 1, true]} />
        <meshStandardMaterial
          color="#ffbadc"
          emissive="#b95093"
          emissiveIntensity={0.18}
          transparent
          opacity={0.28}
          roughness={0.64}
          depthWrite={false}
        />
      </mesh>
    </Float>
  );
}

function StromaParticles() {
  const points = useMemo(() => {
    const count = 260;
    const rand = seededRandom(78291);
    const positions = new Float32Array(count * 3);

    for (let i = 0; i < count; i += 1) {
      const spread = rand();
      positions[i * 3] = (rand() - 0.5) * 13.8;
      positions[i * 3 + 1] = (rand() - 0.5) * 8.2;
      positions[i * 3 + 2] = (rand() - 0.5) * 5.4 - 1.8 - spread * 0.45;
    }

    return positions;
  }, []);

  const ref = useRef();

  useFrame((state) => {
    if (!ref.current) return;

    ref.current.rotation.y = state.clock.elapsedTime * 0.018;
    ref.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.08) * 0.025;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[points, 3]} />
      </bufferGeometry>

      <pointsMaterial
        size={0.038}
        color="#f7a8d2"
        transparent
        opacity={0.56}
        sizeAttenuation
        depthWrite={false}
      />
    </points>
  );
}

function BiomarkerMist() {
  const points = useMemo(() => {
    const count = 110;
    const rand = seededRandom(24519);
    const positions = new Float32Array(count * 3);

    for (let i = 0; i < count; i += 1) {
      positions[i * 3] = (rand() - 0.5) * 10.5;
      positions[i * 3 + 1] = (rand() - 0.5) * 6.7;
      positions[i * 3 + 2] = (rand() - 0.5) * 4.4 - 0.8;
    }

    return positions;
  }, []);

  const ref = useRef();

  useFrame((state) => {
    if (!ref.current) return;

    ref.current.rotation.z = Math.sin(state.clock.elapsedTime * 0.12) * 0.08;
    ref.current.position.y = Math.sin(state.clock.elapsedTime * 0.22) * 0.08;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[points, 3]} />
      </bufferGeometry>

      <pointsMaterial
        size={0.055}
        color="#37f1df"
        transparent
        opacity={0.48}
        sizeAttenuation
        depthWrite={false}
      />
    </points>
  );
}

function SceneContent() {
  return (
    <>
      <ambientLight intensity={0.42} />

      <directionalLight position={[4, 6, 5]} intensity={1.28} color="#ffe6f7" />
      <directionalLight position={[-5, -2.5, 3.5]} intensity={0.56} color="#54f1e0" />
      <pointLight position={[0, 2.1, 2.4]} intensity={0.88} color="#ff78bd" />
      <pointLight position={[-3.2, -1.4, 1.5]} intensity={0.42} color="#7c5cff" />
      <pointLight position={[3.8, 1.4, 1.2]} intensity={0.36} color="#ffe082" />

      {CELL_CLUSTERS.map((cell) => (
        <CancerCell
          key={`${cell.position.join('-')}-${cell.color}`}
          position={cell.position}
          color={cell.color}
          nucleus={cell.nucleus}
          marker={cell.marker}
          scale={cell.scale}
          speed={cell.speed}
        />
      ))}

      <TissueRing />

      {FIBER_STRANDS.map((fiber) => (
        <StromaFiber
          key={`${fiber.position.join('-')}-${fiber.length}`}
          position={fiber.position}
          rotation={fiber.rotation}
          length={fiber.length}
        />
      ))}

      <StromaParticles />
      <BiomarkerMist />

      <fog attach="fog" args={['#080718', 5.6, 15.5]} />
    </>
  );
}

export default function LoginOvarianScene() {
  return (
    <div className="login-scene" aria-hidden="true">
      <Canvas
        camera={{ position: [0, 0, 6.7], fov: 42 }}
        dpr={[1, 1.75]}
        gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
        onCreated={({ gl }) => {
          gl.setClearColor(new THREE.Color('#080718'), 1);
          gl.outputColorSpace = THREE.SRGBColorSpace;
          gl.toneMapping = THREE.ACESFilmicToneMapping;
          gl.toneMappingExposure = 1.08;
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