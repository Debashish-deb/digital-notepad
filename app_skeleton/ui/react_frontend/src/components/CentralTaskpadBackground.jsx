import { useTaskpadWorkerRegistration } from '../contexts/TaskpadContext.jsx';
import { CENTRAL_WORKER_ID, TASKPAD_SCOPES } from '../utils/taskpadRegistry.js';

/**
 * Headless central taskpad — registers the manager worker without any dock UI.
 * Section, project, and hub taskpads remain visible; central orchestrates in the background.
 */
export default function CentralTaskpadBackground() {
  useTaskpadWorkerRegistration({
    workerId: CENTRAL_WORKER_ID,
    scope: TASKPAD_SCOPES.CENTRAL,
    label: 'Central Taskpad',
  });

  return null;
}
