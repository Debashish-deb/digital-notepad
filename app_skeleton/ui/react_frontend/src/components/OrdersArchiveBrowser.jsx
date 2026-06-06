import {
  Archive,
  CreditCard,
  FileSpreadsheet,
  FlaskConical,
  FolderOpen,
  Handshake,
  Monitor,
} from 'lucide-react';
import LabDocumentsBrowser from './LabDocumentsBrowser.jsx';
import {
  ARCHIVE_CATEGORY_GROUPS,
  archiveDocumentTitle,
  categorizeArchivePath,
} from '../utils/ordersArchiveCategories.js';

const CATEGORY_ICONS = {
  hus_purchases: CreditCard,
  fican_funding: FileSpreadsheet,
  lab_transfers: Handshake,
  equipment_orders: FlaskConical,
  collaboration_orders: Handshake,
  purchase_registers: FolderOpen,
  computer_orders: Monitor,
};

export default function OrdersArchiveBrowser() {
  return (
    <LabDocumentsBrowser
      sectionId="orders_archive"
      title="Orders Archive"
      description="Historical purchase orders, procurement registers, equipment confirmations, and IT orders."
      icon={Archive}
      categoryGroups={ARCHIVE_CATEGORY_GROUPS}
      defaultCategory="hus_purchases"
      categorizePath={(path) => categorizeArchivePath(path)}
      documentTitle={archiveDocumentTitle}
      categoryIcons={CATEGORY_ICONS}
      className="orders-archive-browser catalog-space-browser"
    />
  );
}
