import { lazy, Suspense } from 'react';
import { Loader2 } from 'lucide-react';

const DataPadEditor = lazy(() => import('./DataPadEditor.jsx'));

export default function LazyDataPadEditor(props) {
  return (
    <Suspense
      fallback={(
        <div className="media-viewer-loading" style={{ minHeight: '8rem' }}>
          <Loader2 size={20} className="spin" aria-hidden />
          <span>Loading editor…</span>
        </div>
      )}
    >
      <DataPadEditor {...props} />
    </Suspense>
  );
}
