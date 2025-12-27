"""Routes pour la navigation filesystem (file browser)."""

import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import settings


router = APIRouter(prefix="/fs")


# Whitelist des racines autorisées
ALLOWED_ROOTS = [
    "/Users/malik/Documents",
    os.path.expanduser("~/Documents"),
    "/tmp",
    "./sandbox",
    "./data",
]


class FileEntry(BaseModel):
    """Entrée de fichier ou dossier."""
    name: str
    type: str  # "file" | "dir"
    size: Optional[int] = None
    mtime: Optional[str] = None
    path: str


class ListDirectoryResponse(BaseModel):
    """Réponse pour listage de dossier."""
    path: str
    parent: Optional[str]
    entries: List[FileEntry]


def is_path_allowed(path: str) -> bool:
    """
    Vérifie si un chemin est autorisé (dans la whitelist).
    
    Args:
        path: Chemin à vérifier
        
    Returns:
        True si autorisé
    """
    resolved_path = Path(path).resolve()
    
    for root in ALLOWED_ROOTS:
        allowed_root = Path(root).resolve()
        try:
            # Vérifier si le chemin est sous la racine autorisée
            resolved_path.relative_to(allowed_root)
            return True
        except ValueError:
            continue
    
    return False


def format_size(size: int) -> str:
    """
    Formate une taille en bytes vers format lisible.
    
    Args:
        size: Taille en bytes
        
    Returns:
        Taille formatée (ex: "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


@router.get("/list", response_model=ListDirectoryResponse)
async def list_directory(path: str = "/"):
    """
    Liste le contenu d'un dossier.
    
    Args:
        path: Chemin du dossier à lister
        
    Returns:
        Contenu du dossier avec métadonnées
        
    Raises:
        HTTPException 403 si le chemin n'est pas autorisé
        HTTPException 404 si le chemin n'existe pas
        HTTPException 400 si ce n'est pas un dossier
    """
    # Résoudre le chemin
    if path == "/":
        # Racine spéciale : lister les racines autorisées
        entries = []
        for root in ALLOWED_ROOTS:
            root_path = Path(root).resolve()
            if root_path.exists() and root_path.is_dir():
                entries.append(FileEntry(
                    name=root_path.name or str(root_path),
                    type="dir",
                    path=str(root_path),
                ))
        
        return ListDirectoryResponse(
            path="/",
            parent=None,
            entries=entries,
        )
    
    # Vérifier la sécurité
    if not is_path_allowed(path):
        raise HTTPException(
            status_code=403,
            detail=f"Accès refusé : le chemin n'est pas dans les dossiers autorisés"
        )
    
    dir_path = Path(path).resolve()
    
    if not dir_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Dossier introuvable : {path}"
        )
    
    if not dir_path.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Pas un dossier : {path}"
        )
    
    # Lister le contenu
    entries = []
    
    try:
        for item in sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            # Ignorer les fichiers/dossiers cachés
            if item.name.startswith('.'):
                continue
            
            try:
                stat = item.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime).isoformat()
                
                if item.is_dir():
                    entries.append(FileEntry(
                        name=item.name,
                        type="dir",
                        path=str(item),
                        mtime=mtime,
                    ))
                else:
                    entries.append(FileEntry(
                        name=item.name,
                        type="file",
                        size=stat.st_size,
                        path=str(item),
                        mtime=mtime,
                    ))
            except (PermissionError, OSError):
                # Ignorer les fichiers inaccessibles
                continue
    
    except PermissionError:
        raise HTTPException(
            status_code=403,
            detail=f"Permission refusée pour lire : {path}"
        )
    
    # Parent
    parent_path = None
    if dir_path.parent != dir_path:
        if is_path_allowed(str(dir_path.parent)):
            parent_path = str(dir_path.parent)
    
    return ListDirectoryResponse(
        path=str(dir_path),
        parent=parent_path,
        entries=entries,
    )


@router.get("/allowed-roots")
async def get_allowed_roots():
    """
    Retourne la liste des racines autorisées.
    
    Returns:
        Liste des chemins racines autorisés
    """
    roots = []
    for root in ALLOWED_ROOTS:
        root_path = Path(root).resolve()
        if root_path.exists() and root_path.is_dir():
            roots.append({
                "path": str(root_path),
                "name": root_path.name or str(root_path),
            })
    
    return {"roots": roots}


@router.post("/validate-path")
async def validate_path(path: str):
    """
    Valide qu'un chemin existe et est autorisé.
    
    Args:
        path: Chemin à valider
        
    Returns:
        Informations sur le chemin
    """
    if not is_path_allowed(path):
        raise HTTPException(
            status_code=403,
            detail="Chemin non autorisé"
        )
    
    resolved_path = Path(path).resolve()
    
    if not resolved_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Chemin introuvable"
        )
    
    stat = resolved_path.stat()
    
    return {
        "path": str(resolved_path),
        "exists": True,
        "is_dir": resolved_path.is_dir(),
        "is_file": resolved_path.is_file(),
        "size": stat.st_size if resolved_path.is_file() else None,
        "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }
