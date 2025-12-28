# File Browser API & UI

## 🎯 Objectif

Remplacer les saisies manuelles de chemins et les `tkinter.filedialog` par un **file browser web natif** côté backend, compatible avec tous les navigateurs (y compris Safari qui limite `showDirectoryPicker`).

## 🏗️ Architecture

### Backend : Navigation Filesystem Sécurisée

**Whitelist de sécurité** : Seuls les dossiers autorisés sont accessibles
- `/Users/malik/Documents`
- `~/Documents` (résolu)
- `/tmp`
- `./sandbox`
- `./data`

**Endpoints API** :

#### `GET /api/fs/list?path=/path/to/folder`

Liste le contenu d'un dossier.

**Response** :
```json
{
  "path": "/Users/malik/Documents",
  "parent": "/Users/malik",
  "entries": [
    {
      "name": "Project",
      "type": "dir",
      "path": "/Users/malik/Documents/Project",
      "mtime": "2025-12-27T14:30:00"
    },
    {
      "name": "file.pdf",
      "type": "file",
      "size": 1048576,
      "path": "/Users/malik/Documents/file.pdf",
      "mtime": "2025-12-27T14:30:00"
    }
  ]
}
```

**Errors** :
- `403 Forbidden` : Chemin hors whitelist
- `404 Not Found` : Dossier introuvable
- `400 Bad Request` : Pas un dossier

#### `GET /api/fs/allowed-roots`

Retourne les racines autorisées.

**Response** :
```json
{
  "roots": [
    {
      "path": "/Users/malik/Documents",
      "name": "Documents"
    },
    {
      "path": "/tmp",
      "name": "tmp"
    }
  ]
}
```

#### `POST /api/fs/validate-path`

Valide qu'un chemin existe et est autorisé.

**Request** :
```json
{
  "path": "/Users/malik/Documents/test"
}
```

**Response** :
```json
{
  "path": "/Users/malik/Documents/test",
  "exists": true,
  "is_dir": true,
  "is_file": false,
  "size": null,
  "mtime": "2025-12-27T14:30:00"
}
```

### Training : Endpoints Enrichis

#### `POST /api/training/scan-batch`

Scanne un dataset pour découvrir et évaluer tous les clients.

**Request** :
```json
{
  "dataset_root": "/path/to/RH PRO BASE DONNEE/3. TERMINER",
  "batch_name": "BATCH_20",
  "min_pipeline_score": 0.3
}
```

**Response** :
```json
{
  "success": true,
  "dataset_root": "/path/to/dataset",
  "batch_name": "BATCH_20",
  "clients": [
    {
      "client_name": "ARIFI Zejadin",
      "client_path": "/path/to/ARIFI Zejadin",
      "pipeline_ready": true,
      "gold_score": 0.60,
      "rag_sources_count": 10,
      "total_size_mb": 12.5,
      "warnings": []
    }
  ],
  "summary": {
    "total": 20,
    "pipeline_ready": 14,
    "not_ready": 6,
    "ready_rate": 70.0
  }
}
```

#### `POST /api/training/analyze-client` (Enrichi)

Analyse un client avec enrichissements :
- `detected_folders` : structure 01/03/04/05/06 avec found/path
- `gold_candidates` : liste des GOLD possibles avec scores
- `files_by_type` : comptage par extension (.pdf, .docx, etc.)
- `identity_candidates` : extraction nom/prénom/AVS
- `exploitable_summary` : résumé pour RAG (quality, missing_critical)

**Request** :
```json
{
  "client_folder_path": "/path/to/ARIFI Zejadin"
}
```

**Response** :
```json
{
  "success": true,
  "scan_result": { /* résultat complet du scanner */ },
  "detected_folders": {
    "01_personnel": { "found": false, "path": null },
    "03_tests": { "found": true, "path": "/path/03 Tests" },
    "06_rapport": { "found": false, "path": null }
  },
  "gold_candidates": [
    {
      "path": "/path/Bilan orientation.docx",
      "score": 0.60,
      "strategy": "recursive_scan",
      "selected": true
    }
  ],
  "files_by_type": {
    ".pdf": 8,
    ".docx": 1,
    ".msg": 1
  },
  "identity_candidates": {
    "nom_prenom_raw": "ARIFI Zejadin",
    "nom": "ARIFI",
    "prenom": "Zejadin",
    "avs_candidates": ["756.1234.5678.90"]
  },
  "exploitable_summary": {
    "can_process": true,
    "gold_available": true,
    "gold_confidence": 0.60,
    "rag_sources_count": 10,
    "rag_sources_types": [".pdf", ".docx", ".msg"],
    "total_data_mb": 12.5,
    "missing_critical": [],
    "expected_quality": "high"
  }
}
```

**Quality Levels** :
- `high` : ≥5 sources + GOLD score ≥0.6
- `medium` : ≥2 sources + GOLD score ≥0.4
- `low` : moins de sources ou GOLD faible

### Frontend : Composants React

#### `<FileBrowser />`

Modal de navigation filesystem avec :
- Barre de navigation (Home, Up, Path)
- Liste interactive dossiers/fichiers
- Tri automatique (dossiers en premier)
- Affichage taille + date de modification
- Sélection avec highlight
- Double-clic pour naviguer dans dossier

**Props** :
```tsx
interface FileBrowserProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (path: string) => void;
  title?: string;
  description?: string;
  initialPath?: string;
  selectMode?: 'file' | 'folder';
}
```

**Usage** :
```tsx
import { FileBrowser } from '@/components/FileBrowser';

function MyComponent() {
  const [open, setOpen] = useState(false);
  
  return (
    <>
      <Button onClick={() => setOpen(true)}>Browse</Button>
      
      <FileBrowser
        open={open}
        onOpenChange={setOpen}
        onSelect={(path) => {
          console.log('Selected:', path);
          setOpen(false);
        }}
        title="Sélectionner un dossier"
        initialPath="/"
      />
    </>
  );
}
```

#### `useFileBrowser()` Hook

Hook pour gérer l'état du file browser.

```tsx
import { useFileBrowser } from '@/hooks/useFileBrowser';

function MyComponent() {
  const browser = useFileBrowser('./initial/path');
  
  return (
    <>
      <Input value={browser.selectedPath || ''} readOnly />
      <Button onClick={browser.openBrowser}>Browse</Button>
      
      <FileBrowser
        open={browser.isOpen}
        onOpenChange={browser.closeBrowser}
        onSelect={browser.handleSelect}
      />
    </>
  );
}
```

**Returns** :
```tsx
{
  isOpen: boolean;
  selectedPath: string | null;
  openBrowser: () => void;
  closeBrowser: () => void;
  handleSelect: (path: string) => void;
}
```

## 🛠️ Utilisation

### 1. Backend

Les endpoints sont automatiquement disponibles :

```bash
# Lister un dossier
curl "http://localhost:8000/api/fs/list?path=/Users/malik/Documents"

# Scanner un batch
curl -X POST "http://localhost:8000/api/training/scan-batch" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_root": "/path/to/dataset",
    "batch_name": "BATCH_20"
  }'

# Analyser un client
curl -X POST "http://localhost:8000/api/training/analyze-client" \
  -H "Content-Type: application/json" \
  -d '{
    "client_folder_path": "/path/to/client"
  }'
```

### 2. Frontend React

Dans une page React (ex: Training) :

```tsx
import { FileBrowser } from '@/components/FileBrowser';
import { useFileBrowser } from '@/hooks/useFileBrowser';

export function TrainingPage() {
  const datasetBrowser = useFileBrowser();
  const sandboxBrowser = useFileBrowser('./sandbox');
  
  return (
    <div>
      {/* Dataset Root */}
      <div className="flex gap-2">
        <Input value={datasetBrowser.selectedPath || ''} readOnly />
        <Button onClick={datasetBrowser.openBrowser}>
          <FolderOpen className="h-4 w-4 mr-2" />
          Browse
        </Button>
      </div>
      
      {/* Sandbox Root */}
      <div className="flex gap-2">
        <Input value={sandboxBrowser.selectedPath || ''} readOnly />
        <Button onClick={sandboxBrowser.openBrowser}>
          <FolderOpen className="h-4 w-4 mr-2" />
          Browse
        </Button>
      </div>
      
      {/* Browsers */}
      <FileBrowser
        open={datasetBrowser.isOpen}
        onOpenChange={datasetBrowser.closeBrowser}
        onSelect={datasetBrowser.handleSelect}
        title="Sélectionner le Dataset"
      />
      
      <FileBrowser
        open={sandboxBrowser.isOpen}
        onOpenChange={sandboxBrowser.closeBrowser}
        onSelect={sandboxBrowser.handleSelect}
        title="Sélectionner la Sandbox"
      />
    </div>
  );
}
```

### 3. Streamlit (Existant)

Le système Streamlit continue d'utiliser `tkinter.filedialog` :

```python
import tkinter as tk
from tkinter import filedialog

root = tk.Tk()
root.withdraw()
folder_path = filedialog.askdirectory(title="Sélectionner un dossier")
```

## 🔒 Sécurité

### Whitelist Stricte

Seuls les chemins sous ces racines sont autorisés :
- `/Users/malik/Documents`
- `/tmp`
- `./sandbox`
- `./data`

**Validation** :
```python
def is_path_allowed(path: str) -> bool:
    resolved_path = Path(path).resolve()
    
    for root in ALLOWED_ROOTS:
        allowed_root = Path(root).resolve()
        try:
            resolved_path.relative_to(allowed_root)
            return True
        except ValueError:
            continue
    
    return False
```

### Path Traversal Protection

- Utilisation de `Path.resolve()` pour résoudre les symlinks et `..`
- Vérification que le chemin résolu est sous une racine autorisée
- Refus automatique des chemins hors whitelist

### Fichiers Cachés

Les fichiers/dossiers commençant par `.` sont automatiquement filtrés :
```python
if item.name.startswith('.'):
    continue
```

## 📊 Tests

Script de test complet :

```bash
python test_api_filebrowser.py
```

**Tests inclus** :
1. ✅ Whitelist sécurité (autoriser/refuser)
2. ✅ Scanner enrichi (identity, folders, quality)
3. ✅ Scan batch (découverte clients)

**Résultats attendus** :
```
📁 Racines autorisées : 5
🔒 Tests de sécurité :
  ✅ Autorisé : /Users/malik/Documents/test
  ❌ Refusé : /etc/passwd
  ✅ Autorisé : ./sandbox
  ✅ Autorisé : /tmp/test

📂 Dossiers détectés : 0/7
📊 Fichiers par type : .docx (1)
👤 Identité : client_01
📋 Qualité attendue : LOW

✅ Pipeline-ready : 2/5
```

## 🎨 UI/UX

### FileBrowser Modal

**Design** :
- Header avec titre + description
- Barre de navigation (Home / Up / Path courante)
- Liste scrollable avec tri (dossiers > fichiers)
- Icônes distinctes (Folder 📁 / File 📄)
- Highlight sur sélection
- Footer avec chemin sélectionné + actions

**Interactions** :
- **Click** : Sélectionner
- **Double-click** : Naviguer (dossiers uniquement)
- **Home** : Retour aux racines
- **Up** : Dossier parent
- **Select** : Valider la sélection

## 📁 Fichiers Créés

### Backend
- `backend/api/routes/filesystem.py` (250 lignes)
  - Routes : `/api/fs/list`, `/api/fs/allowed-roots`, `/api/fs/validate-path`
  - Sécurité : whitelist + path validation
  
- `backend/api/routes/training.py` (enrichissements)
  - Route `/api/training/scan-batch` (90 lignes)
  - Route `/api/training/analyze-client` enrichie (120 lignes)

- `backend/main.py` (modification)
  - Import + registration du router `filesystem`

### Frontend
- `frontend/src/components/FileBrowser.tsx` (280 lignes)
  - Composant modal complet
  - Navigation + sélection + affichage
  
- `frontend/src/hooks/useFileBrowser.ts` (30 lignes)
  - Hook pour gestion état
  
- `frontend/src/pages/TrainingPage.tsx` (exemple 280 lignes)
  - Intégration complète avec 2 browsers
  - Scan batch + analyze client
  - Affichage résultats enrichis

### Tests & Docs
- `test_api_filebrowser.py` (200 lignes)
  - Tests filesystem sécurité
  - Tests scanner enrichi
  - Tests scan batch

- `docs/FILE_BROWSER_API.md` (ce fichier)

## 🔄 Migration

### Avant (Streamlit + tkinter)

```python
import tkinter as tk
from tkinter import filedialog

# Limité au client local
# Nécessite tkinter installé
# Pas compatible web pur
root = tk.Tk()
root.withdraw()
path = filedialog.askdirectory()
```

### Après (React + API)

```tsx
import { FileBrowser } from '@/components/FileBrowser';

// Compatible tout navigateur
// Sécurisé côté backend
// Expérience web native
<FileBrowser
  open={open}
  onSelect={(path) => setPath(path)}
/>
```

## 🚀 Prochaines Étapes

### V1 (Actuel) ✅
- ✅ Endpoints filesystem sécurisés
- ✅ Composant React FileBrowser
- ✅ Hook useFileBrowser
- ✅ Enrichissements analyze-client
- ✅ Endpoint scan-batch
- ✅ Tests validation

### V2 (À venir)
- 🔄 Favoris utilisateur (persist localStorage)
- 🔄 Historique navigation (back/forward)
- 🔄 Recherche dans dossier courant
- 🔄 Multi-sélection (batch files)
- 🔄 Preview fichiers (txt, images)
- 🔄 Upload fichiers
- 🔄 Créer dossier

### V3 (Future)
- 📅 Permissions par utilisateur
- 📅 Partage de chemins favoris
- 📅 Bookmarks d'équipe
- 📅 Intégration cloud storage
