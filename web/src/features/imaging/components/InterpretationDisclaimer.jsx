import { AlertTriangle } from 'lucide-react';

export default function InterpretationDisclaimer({ compact = false }) {
  const text = (
    <>
      AI interpretations cite sources when available and disclose uncertainty.
      They do not override raw pixel probe or ROI measurements from the instrument.
      Validate findings against Napari, QuPath, or OMERO on the same source file.
    </>
  );

  if (compact) {
    return (
      <p className="text-footnote muted image-panel__disclaimer">
        <AlertTriangle size={12} aria-hidden /> {text}
      </p>
    );
  }

  return (
    <aside className="image-panel image-panel--disclaimer" role="note">
      <AlertTriangle size={14} aria-hidden />
      <div>
        <strong>Scientific interpretation notice</strong>
        <p className="text-footnote">{text}</p>
      </div>
    </aside>
  );
}
