import { lazy } from 'react';

/** Lazy-loaded route screens and feature panels (code-split per nav target). */
export const GlobalSearchOverlay = lazy(() =>
  import('@/features/search/components/GlobalSearchOverlay'),
);
export const ProjectsScreen = lazy(() => import('@/pages/ProjectsScreen'));
export const BioinformaticsHubScreen = lazy(() => import('@/pages/BioinformaticsHubScreen'));
export const AiLabAssistantScreen = lazy(() => import('@/pages/AiLabAssistantScreen'));
export const FeatureClinicalScreen = lazy(() => import('@/pages/FeatureClinicalScreen'));
export const LabKnowledgeScreen = lazy(() => import('@/pages/LabKnowledgeScreen'));
export const DataStorageScreen = lazy(() => import('@/pages/DataStorageScreen'));
export const AdministrationScreen = lazy(() => import('@/pages/AdministrationScreen'));
export const UserProfileScreen = lazy(() => import('@/pages/UserProfileScreen'));
export const MeetingScreen = lazy(() => import('@/pages/MeetingScreen'));
export const IngestionDashboard = lazy(() => import('@/pages/IngestionDashboard'));
export const DigitalizationDashboard = lazy(() => import('@/pages/DigitalizationDashboard'));
export const KnowledgeSearchScreen = lazy(() => import('@/pages/KnowledgeSearchScreen'));
export const ResearchKnowledgeAdminScreen = lazy(() =>
  import('@/pages/ResearchKnowledgeAdminScreen'),
);
export const LabCorpusBrowser = lazy(() =>
  import('@/features/lab/components/LabCorpusBrowser.jsx'),
);
export const CycifScreen = lazy(() => import('@/pages/CycifScreen'));
export const OverviewDocumentsScreen = lazy(() =>
  import('@/pages/OverviewDocumentsScreen.jsx'),
);
export const SectionDocumentsScreen = lazy(() =>
  import('@/pages/SectionDocumentsScreen.jsx'),
);
export const DocumentLibraryScreen = lazy(() =>
  import('@/pages/DocumentLibraryScreen.jsx'),
);
export const ImageViewerPlaceholderScreen = lazy(() =>
  import('@/pages/ImageViewerPlaceholderScreen.jsx'),
);
export const ImageStreamingAdminScreen = lazy(() =>
  import('@/pages/ImageStreamingAdminScreen.jsx'),
);

export const OrdersTasksPanel = lazy(() =>
  import('@/pages/OrdersHubScreen').then((m) => ({ default: m.OrdersTasksPanel })),
);
export const OrdersRegisterPanel = lazy(() =>
  import('@/pages/OrdersHubScreen').then((m) => ({ default: m.OrdersRegisterPanel })),
);
export const OrdersRelatedPanel = lazy(() =>
  import('@/pages/OrdersHubScreen').then((m) => ({ default: m.OrdersRelatedPanel })),
);
export const OrdersBillingPanel = lazy(() =>
  import('@/pages/OrdersHubScreen').then((m) => ({ default: m.OrdersBillingPanel })),
);
export const OrdersArchivePanel = lazy(() =>
  import('@/pages/OrdersHubScreen').then((m) => ({ default: m.OrdersArchivePanel })),
);

export const WetLabProtocolsPanel = lazy(() =>
  import('@/pages/WetLabScreen').then((m) => ({ default: m.WetLabProtocolsPanel })),
);
export const WetLabTasksPanel = lazy(() =>
  import('@/pages/WetLabScreen').then((m) => ({ default: m.WetLabTasksPanel })),
);
export const WetLabInventoryPanel = lazy(() =>
  import('@/pages/WetLabScreen').then((m) => ({ default: m.WetLabInventoryPanel })),
);
