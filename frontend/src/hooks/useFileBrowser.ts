import { useState } from 'react';

interface UseFileBrowserReturn {
  isOpen: boolean;
  selectedPath: string | null;
  openBrowser: () => void;
  closeBrowser: () => void;
  handleSelect: (path: string) => void;
}

export function useFileBrowser(
  initialPath: string | null = null
): UseFileBrowserReturn {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedPath, setSelectedPath] = useState<string | null>(initialPath);

  const openBrowser = () => setIsOpen(true);
  const closeBrowser = () => setIsOpen(false);

  const handleSelect = (path: string) => {
    setSelectedPath(path);
    closeBrowser();
  };

  return {
    isOpen,
    selectedPath,
    openBrowser,
    closeBrowser,
    handleSelect,
  };
}
