import { useCallback, useEffect, useRef, useState } from 'react';

const MAX_SWIMMERS = 5;
const SPAWN_MIN_MS = 2200;
const SPAWN_JITTER_MS = 1400;

function shuffle(list) {
  const arr = [...list];
  for (let i = arr.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

/**
 * Project topic labels that drift through the hero card like small fish —
 * queued, staggered, never all visible at once.
 */
export default function SwimmingProjectTopics({ topics = [] }) {
  const [swimmers, setSwimmers] = useState([]);
  const queueRef = useRef([]);
  const idRef = useRef(0);

  const labels = topics.map((t) => String(t || '').trim()).filter(Boolean);

  const refillQueue = useCallback(() => {
    if (!labels.length) {
      queueRef.current = [];
      return;
    }
    queueRef.current = shuffle(labels);
  }, [labels]);

  useEffect(() => {
    refillQueue();
    setSwimmers([]);
  }, [refillQueue]);

  useEffect(() => {
    if (!labels.length) return undefined;

    const spawn = () => {
      setSwimmers((current) => {
        if (current.length >= MAX_SWIMMERS) return current;
        if (!queueRef.current.length) refillQueue();
        const label = queueRef.current.shift();
        if (!label) return current;

        const id = idRef.current + 1;
        idRef.current = id;

        return [
          ...current,
          {
            id,
            label,
            variant: (id % 6) + 1,
            top: 8 + Math.random() * 78,
            duration: 12 + Math.random() * 10,
            depth: Math.random(),
            delay: Math.random() * 0.8,
          },
        ];
      });
    };

    spawn();
    const timer = window.setInterval(spawn, SPAWN_MIN_MS + Math.floor(Math.random() * SPAWN_JITTER_MS));
    return () => window.clearInterval(timer);
  }, [labels, refillQueue]);

  const removeSwimmer = useCallback((id) => {
    setSwimmers((current) => current.filter((item) => item.id !== id));
  }, []);

  if (!labels.length) return null;

  return (
    <div className="ai3d-swim-layer" aria-hidden="true">
      {swimmers.map((fish) => (
        <span
          key={fish.id}
          className={`ai3d-swimmer ai3d-swimmer--v${fish.variant}`}
          style={{
            top: `${fish.top}%`,
            animationDuration: `${fish.duration}s`,
            animationDelay: `${fish.delay}s`,
            opacity: 0.28 + fish.depth * 0.42,
            fontSize: `${0.5 + fish.depth * 0.18}rem`,
            zIndex: 1 + Math.floor(fish.depth * 4),
            filter: `blur(${(1 - fish.depth) * 0.4}px)`,
          }}
          onAnimationEnd={() => removeSwimmer(fish.id)}
        >
          {fish.label}
        </span>
      ))}
    </div>
  );
}
