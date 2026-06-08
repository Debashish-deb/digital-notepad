import LabDocumentExplorer from '@/features/documents/components/LabDocumentExplorer.jsx';

export default function DocumentLibraryScreen({
  title,
  description,
  mainId = 'library',
  subId = 'all_files',
}) {
  return (
    <div className="document-library-screen">
      <LabDocumentExplorer
        mainId={mainId}
        subId={subId}
        title={title || 'Document Library'}
        description={
          description || 'Search and browse lab documents with audit-backed status and previews.'
        }
        className="lab-document-explorer--all-files"
      />
    </div>
  );
}
