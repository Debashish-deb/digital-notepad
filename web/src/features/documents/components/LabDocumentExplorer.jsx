import ScientificFileExplorer from './ScientificFileExplorer.jsx';
import { getExplorerPreset } from '@/lib/documentExplorerPresets.js';

/**
 * Drop-in replacement for LabDocumentsBrowser — same nav context, new explorer UI.
 */
export default function LabDocumentExplorer({
  mainId = 'data_storage',
  subId = 'documents',
  title,
  description,
  topPanel = null,
  className = '',
}) {
  const preset = getExplorerPreset(mainId, subId);
  const layoutMode = mainId === 'overview' ? 'reading' : 'split';

  return (
    <div className={`lab-document-explorer ${className}`.trim()}>
      {topPanel}
      <ScientificFileExplorer
        key={`${mainId}-${subId}`}
        title={title}
        subtitle={description}
        scopeLabel={preset.scopeLabel}
        initialDomainTab={preset.domainTab}
        taxonomyTab={preset.taxonomyTab || preset.domainTab}
        initialFilters={preset.filters}
        initialQuery={preset.initialQuery || ''}
        showDomainTabs={preset.showDomainTabs}
        hideScopeFilters={preset.hideScopeFilters ?? Boolean(preset.filters?.section)}
        scopeChipIds={preset.scopeChipIds}
        layoutMode={layoutMode}
        folderTreeRoot={preset.folderTreeRoot ?? null}
      />
    </div>
  );
}
