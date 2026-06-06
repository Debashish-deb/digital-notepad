import { CreditCard, FileText, FolderOpen, Lock, Plane, Shield, Truck } from 'lucide-react';
import LabDocumentsBrowser from './LabDocumentsBrowser.jsx';
import {
  BILLING_CATEGORY_GROUPS,
  billingDocumentTitle,
  categorizeBillingPath,
} from '../utils/ordersBillingCategories.js';

const CATEGORY_ICONS = {
  general_reference: FileText,
  hus_finance: CreditCard,
  credentials: Lock,
  fedex: Plane,
  ups: Truck,
  dna_shipments: FileText,
  us_customs: Shield,
  other_admin: FolderOpen,
};

export default function OrdersBillingBrowser() {
  return (
    <LabDocumentsBrowser
      sectionId="orders_billing"
      title="Billing & Ordering Instructions"
      description="Billing addresses, vendor accounts, shipments, and HUS billing."
      icon={CreditCard}
      categoryGroups={BILLING_CATEGORY_GROUPS}
      defaultCategory="general_reference"
      categorizePath={(path) => categorizeBillingPath(path)}
      documentTitle={billingDocumentTitle}
      categoryIcons={CATEGORY_ICONS}
      className="orders-billing-browser catalog-space-browser"
      sensitiveCategories={['credentials']}
    />
  );
}
