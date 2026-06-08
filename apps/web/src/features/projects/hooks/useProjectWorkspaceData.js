import { useCallback, useEffect, useState } from 'react';
import { resolveProject, fetchWithTimeout } from '@/lib/projectUtils.js';

export default function useProjectWorkspaceData(projectCode, dbProjects, API_URL) {
  const [projectData, setProjectData] = useState(() => resolveProject(projectCode, dbProjects));
  const [projectFolders, setProjectFolders] = useState([]);
  const [loadError, setLoadError] = useState(null);

  const fetchProjectFolders = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/documents/${projectCode}`);
      if (res.ok) {
        const docs = await res.json();
        const folders = new Set();
        docs.forEach((d) => {
          if (d.folder_path && d.folder_path !== '.') {
            folders.add(d.folder_path.split('/')[0]);
          }
        });
        setProjectFolders(Array.from(folders).sort());
      }
    } catch (e) {
      console.error(e);
    }
  }, [API_URL, projectCode]);

  const fetchProjectDetails = useCallback(async () => {
    setLoadError(null);
    const localProject = resolveProject(projectCode, dbProjects);
    if (localProject) setProjectData(localProject);

    try {
      const res = await fetchWithTimeout(`${API_URL}/projects`);
      if (res.ok) {
        const data = await res.json();
        const resolved = resolveProject(projectCode, data);
        if (resolved) {
          setProjectData(resolved);
          return;
        }
      }
    } catch (e) {
      console.error(e);
    }

    if (!localProject) {
      setLoadError(`Project "${projectCode}" was not found in the catalog or API.`);
    }
  }, [projectCode, dbProjects, API_URL]);

  useEffect(() => {
    setProjectData(resolveProject(projectCode, dbProjects));
    fetchProjectDetails();
    fetchProjectFolders();
  }, [projectCode, dbProjects, fetchProjectDetails, fetchProjectFolders]);

  return {
    projectData,
    projectFolders,
    loadError,
    fetchProjectDetails,
    fetchProjectFolders,
  };
}
