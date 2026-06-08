import LabDocumentExplorer from '@/features/documents/components/LabDocumentExplorer.jsx';
import { getSectionDocumentsConfig } from '@/lib/sectionDocumentsConfig.js';

export default function SectionDocumentsScreen({ mainId, subId, title, description }) {
  const config = getSectionDocumentsConfig(mainId, subId);
  if (!config) return null;

  return (
    <LabDocumentExplorer
      mainId={mainId}
      subId={subId}
      title={title}
      description={description}
      className={`section-documents-browser section-documents-browser--${mainId} lab-document-explorer--${mainId}`}
    />
  );
}
