import LabDocumentExplorer from '@/features/documents/components/LabDocumentExplorer.jsx';

export default function DocumentLibraryScreen({ title, description }) {
  return (
    <div className="document-library-screen">
      <LabDocumentExplorer
        mainId="data_storage"
        subId="all_files"
        title={title || 'All Files'}
        description={description || 'Search and browse every file in the lab document library.'}
        className="lab-document-explorer--all-files"
      />
    </div>
  );
}
