import { createContext, useContext } from 'react';

export const ModuleShellCoverContext = createContext(null);

export function useModuleShellCover() {
  return useContext(ModuleShellCoverContext);
}
