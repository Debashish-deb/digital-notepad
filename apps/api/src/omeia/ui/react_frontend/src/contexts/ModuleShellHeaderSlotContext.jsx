import { createContext, useContext } from 'react';

/** @type {import('react').Context<((node: import('react').ReactNode) => void) | null>} */
export const ModuleShellHeaderSlotContext = createContext(null);

export function useModuleShellHeaderSlot() {
  return useContext(ModuleShellHeaderSlotContext);
}
