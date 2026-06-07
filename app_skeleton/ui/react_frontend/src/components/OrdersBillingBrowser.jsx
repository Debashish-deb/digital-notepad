import LabDocumentExplorer from './LabDocumentExplorer.jsx';

export default function OrdersBillingBrowser() {
  return (
    <LabDocumentExplorer
      mainId="orders"
      subId="billing"
      title="Billing & Ordering Instructions"
      description="Billing addresses, vendor accounts, shipments, and HUS billing."
      className="orders-billing-browser lab-document-explorer--orders"
    />
  );
}
