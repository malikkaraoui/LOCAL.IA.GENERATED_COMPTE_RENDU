import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Folder,
  File,
  ChevronRight,
  Home,
  ArrowUp,
  Loader2,
  FolderOpen,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface FileEntry {
  name: string;
  type: 'file' | 'dir';
  size?: number;
  mtime?: string;
  path: string;
}

interface FileBrowserProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (path: string) => void;
  title?: string;
  description?: string;
  initialPath?: string;
  selectMode?: 'file' | 'folder';
}

export function FileBrowser({
  open,
  onOpenChange,
  onSelect,
  title = 'Sélectionner un dossier',
  description = 'Naviguez dans le système de fichiers pour sélectionner un dossier',
  initialPath = '/',
  selectMode = 'folder',
}: FileBrowserProps) {
  const [currentPath, setCurrentPath] = useState<string>(initialPath);
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const [parentPath, setParentPath] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);

  // Charger le contenu d'un dossier
  const loadDirectory = async (path: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await axios.get(`${API_BASE}/api/fs/list`, {
        params: { path },
      });

      setCurrentPath(response.data.path);
      setParentPath(response.data.parent);
      setEntries(response.data.entries);
      setSelectedPath(path);
    } catch (err: any) {
      console.error('Error loading directory:', err);
      setError(
        err.response?.data?.detail ||
          'Erreur lors du chargement du dossier'
      );
    } finally {
      setLoading(false);
    }
  };

  // Charger au montage
  useEffect(() => {
    if (open) {
      loadDirectory(initialPath);
    }
  }, [open, initialPath]);

  // Navigation vers un dossier
  const handleNavigate = (path: string) => {
    loadDirectory(path);
  };

  // Sélection d'une entrée
  const handleEntryClick = (entry: FileEntry) => {
    if (entry.type === 'dir') {
      handleNavigate(entry.path);
    } else if (selectMode === 'file') {
      setSelectedPath(entry.path);
    }
  };

  // Double-clic sur dossier
  const handleEntryDoubleClick = (entry: FileEntry) => {
    if (entry.type === 'dir') {
      handleNavigate(entry.path);
    }
  };

  // Validation de la sélection
  const handleConfirm = () => {
    if (selectedPath) {
      onSelect(selectedPath);
      onOpenChange(false);
    }
  };

  // Naviguer vers le parent
  const handleGoUp = () => {
    if (parentPath) {
      handleNavigate(parentPath);
    }
  };

  // Formater la taille
  const formatSize = (bytes?: number): string => {
    if (!bytes) return '-';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }

    return `${size.toFixed(1)} ${units[unitIndex]}`;
  };

  // Formater la date
  const formatDate = (isoDate?: string): string => {
    if (!isoDate) return '-';
    const date = new Date(isoDate);
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Barre de navigation */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="icon"
              onClick={() => handleNavigate('/')}
              disabled={loading || currentPath === '/'}
            >
              <Home className="h-4 w-4" />
            </Button>

            <Button
              variant="outline"
              size="icon"
              onClick={handleGoUp}
              disabled={loading || !parentPath}
            >
              <ArrowUp className="h-4 w-4" />
            </Button>

            <Input
              value={currentPath}
              readOnly
              className="flex-1 font-mono text-sm"
            />
          </div>

          {/* Liste des fichiers/dossiers */}
          <ScrollArea className="h-[400px] border rounded-md">
            {loading ? (
              <div className="flex items-center justify-center h-full">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : error ? (
              <div className="flex items-center justify-center h-full text-destructive">
                <p>{error}</p>
              </div>
            ) : entries.length === 0 ? (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                <p>Dossier vide</p>
              </div>
            ) : (
              <div className="divide-y">
                {entries.map((entry) => (
                  <div
                    key={entry.path}
                    className={cn(
                      'flex items-center gap-3 px-4 py-3 hover:bg-accent cursor-pointer transition-colors',
                      selectedPath === entry.path && 'bg-accent'
                    )}
                    onClick={() => handleEntryClick(entry)}
                    onDoubleClick={() => handleEntryDoubleClick(entry)}
                  >
                    {/* Icône */}
                    <div className="flex-shrink-0">
                      {entry.type === 'dir' ? (
                        selectedPath === entry.path ? (
                          <FolderOpen className="h-5 w-5 text-blue-500" />
                        ) : (
                          <Folder className="h-5 w-5 text-blue-500" />
                        )
                      ) : (
                        <File className="h-5 w-5 text-gray-500" />
                      )}
                    </div>

                    {/* Nom */}
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{entry.name}</p>
                      {entry.type === 'file' && (
                        <p className="text-xs text-muted-foreground">
                          {formatSize(entry.size)} • {formatDate(entry.mtime)}
                        </p>
                      )}
                    </div>

                    {/* Flèche pour dossiers */}
                    {entry.type === 'dir' && (
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>

          {/* Chemin sélectionné */}
          {selectedPath && (
            <div className="bg-muted p-3 rounded-md">
              <p className="text-sm font-medium mb-1">Sélectionné :</p>
              <p className="text-sm font-mono text-muted-foreground break-all">
                {selectedPath}
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Annuler
          </Button>
          <Button onClick={handleConfirm} disabled={!selectedPath}>
            Sélectionner
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default FileBrowser;
