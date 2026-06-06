
import TasksScreen from './TasksScreen';
import SectionDocumentsScreen from './SectionDocumentsScreen.jsx';
import WetLabProtocolsBrowser from '../components/WetLabProtocolsBrowser.jsx';

export function WetLabProtocolsPanel() {
  return (
    <WetLabProtocolsBrowser
      title="Wet-lab SOPs"
      description="Protocols grouped by workflow — sample prep, spatial assays, staining, and patient sample sheets."
    />
  );
}

export function WetLabTasksPanel(props) {
  return <TasksScreen {...props} categoryFilter="Wet_Lab" />;
}

export function WetLabInventoryPanel() {
  return (
    <SectionDocumentsScreen
      mainId="wet_lab"
      subId="files"
      title="Reagents, panels & wet-lab files"
      description="Protocols, inventories, GeoMx/Xenium notes, and wet-lab spreadsheets from WET_LAB."
    />
  );
}
