import LabDocumentExplorer from './LabDocumentExplorer.jsx';

export default function OrdersArchiveBrowser() {
  return (
    <LabDocumentExplorer
      mainId="orders"
      subId="archive"
      title="Orders Archive"
      description="Historical purchase orders, procurement registers, equipment confirmations, and IT orders."
      className="orders-archive-browser lab-document-explorer--orders"
    />
  );
}
