import { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { Center, Environment, OrbitControls, useAnimations, useGLTF } from '@react-three/drei';
import { Loader2, Pause, Play, RotateCcw } from 'lucide-react';
import * as THREE from 'three';

function AnimatedModel({ url, playing, onReady }) {
  const group = useRef();
  const { scene, animations } = useGLTF(url);
  const { actions, names } = useAnimations(animations, group);
  const clonedScene = useMemo(() => scene.clone(true), [scene]);

  useEffect(() => {
    onReady?.({ hasAnimations: names.length > 0, animationNames: names });
  }, [names, onReady]);

  useEffect(() => {
    if (!names.length) return undefined;
    const first = names[0];
    const action = actions[first];
    if (!action) return undefined;
    action.reset();
    if (playing) {
      action.fadeIn(0.2).play();
    } else {
      action.fadeOut(0.2);
    }
    return () => action.stop();
  }, [actions, names, playing]);

  return (
    <group ref={group}>
      <Center>
        <primitive object={clonedScene} />
      </Center>
    </group>
  );
}

function supportsGltf(url) {
  return /\.(glb|gltf)(\?|$)/i.test(url || '');
}

/**
 * Interactive 3D model viewer (glTF/GLB with optional skeletal animation).
 */
export default function ModelViewer3D({ url, title, labels = {} }) {
  const controlsRef = useRef(null);
  const [autoRotate, setAutoRotate] = useState(true);
  const [playing, setPlaying] = useState(true);
  const [meta, setMeta] = useState({ hasAnimations: false, animationNames: [] });
  const [error, setError] = useState(null);

  const isGltf = useMemo(() => supportsGltf(url), [url]);

  const resetCamera = () => {
    const controls = controlsRef.current;
    if (!controls) return;
    controls.reset();
    controls.target.set(0, 0, 0);
    controls.update();
  };

  if (!url) {
    return <p className="text-footnote muted media-viewer-error">{labels.empty || 'No 3D model URL.'}</p>;
  }

  if (!isGltf) {
    return (
      <div className="model-viewer-3d model-viewer-3d--fallback">
        <p className="text-footnote muted">
          {labels.unsupported ||
            'Preview for this 3D format is not supported in-browser. Download the file to open in a 3D app.'}
        </p>
        <a className="btn btn-secondary btn-sm" href={url} download={title} target="_blank" rel="noreferrer">
          {labels.download || 'Download model'}
        </a>
      </div>
    );
  }

  return (
    <div className="model-viewer-3d">
      <div className="media-viewer-toolbar model-viewer-3d-toolbar" role="toolbar" aria-label={labels.toolbar || '3D controls'}>
        <button
          type="button"
          className={`media-viewer-btn${autoRotate ? ' media-viewer-btn--active' : ''}`}
          onClick={() => setAutoRotate((v) => !v)}
          title={labels.autoRotate || 'Auto-rotate'}
        >
          <RotateCcw size={14} aria-hidden />
        </button>
        {meta.hasAnimations ? (
          <button
            type="button"
            className="media-viewer-btn"
            onClick={() => setPlaying((p) => !p)}
            title={playing ? labels.pause || 'Pause animation' : labels.play || 'Play animation'}
          >
            {playing ? <Pause size={14} aria-hidden /> : <Play size={14} aria-hidden />}
          </button>
        ) : null}
        <button type="button" className="media-viewer-btn" onClick={resetCamera} title={labels.reset || 'Reset view'}>
          {labels.resetShort || 'Reset'}
        </button>
        <a className="media-viewer-btn media-viewer-btn--link" href={url} download={title} target="_blank" rel="noreferrer">
          {labels.download || 'Download'}
        </a>
      </div>

      <div className="model-viewer-3d-canvas-wrap">
        <Suspense
          fallback={
            <div className="media-viewer-loading model-viewer-3d-loading">
              <Loader2 size={24} className="spin" aria-hidden />
              <span>{labels.loading || 'Loading 3D model…'}</span>
            </div>
          }
        >
          <Canvas
            camera={{ position: [2.4, 1.6, 2.4], fov: 45, near: 0.01, far: 1000 }}
            gl={{ antialias: true, alpha: true, toneMapping: THREE.ACESFilmicToneMapping }}
            onCreated={({ gl }) => {
              gl.setClearColor(0x000000, 0);
            }}
            onError={() => setError(labels.failed || 'Could not load 3D model.')}
          >
            <ambientLight intensity={0.55} />
            <directionalLight position={[4, 6, 3]} intensity={1.1} castShadow />
            <directionalLight position={[-3, 2, -2]} intensity={0.35} />
            <Environment preset="city" />
            <AnimatedModel url={url} playing={playing} onReady={setMeta} />
            <OrbitControls
              ref={controlsRef}
              makeDefault
              autoRotate={autoRotate}
              autoRotateSpeed={0.85}
              enableDamping
              dampingFactor={0.08}
              minDistance={0.4}
              maxDistance={24}
            />
          </Canvas>
        </Suspense>
      </div>

      {error ? <p className="media-viewer-error">{error}</p> : null}
      <p className="text-caption muted model-viewer-3d-hint">
        {labels.hint || 'Drag to orbit · Scroll to zoom · Right-drag to pan'}
      </p>
    </div>
  );
}

// Preload hook for drei — optional, called when URL known
export function preloadModel3d(url) {
  if (supportsGltf(url)) useGLTF.preload(url);
}
