import LabDocumentExplorer from './LabDocumentExplorer.jsx';

export default function WetLabProtocolsBrowser({ title, description }) {
  return (
    <LabDocumentExplorer
      mainId="wet_lab"
      subId="protocols"
      title={title || 'Wet-lab Protocols'}
      description={description || 'SOPs for sample prep, staining prep, and QC.'}
      className="wet-lab-protocols-browser lab-document-explorer--wet-lab"
    />
  );
}
