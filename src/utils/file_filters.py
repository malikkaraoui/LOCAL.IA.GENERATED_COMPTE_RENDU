"""Filtrage des fichiers temporaires et systèmes."""

from __future__ import annotations
from pathlib import Path

OFFICE_TEMP_PREFIXES = ("~$", ".~")
SYSTEM_FILES = {".DS_Store", "Thumbs.db"}


def is_ignored_filename(path: str | Path) -> bool:
    """
    Vérifie si un fichier doit être ignoré (fichiers temporaires Office, fichiers système).
    
    Args:
        path: Chemin du fichier (str ou Path)
        
    Returns:
        True si le fichier doit être ignoré, False sinon
        
    Examples:
        >>> is_ignored_filename("~$Contrat de travail.docx")
        True
        >>> is_ignored_filename(".~lock.docx")
        True
        >>> is_ignored_filename(".DS_Store")
        True
        >>> is_ignored_filename("Contrat de travail.docx")
        False
    """
    p = Path(path)
    name = p.name
    
    # Fichiers système
    if name in SYSTEM_FILES:
        return True
    
    # Fichiers temporaires/lock Office
    if name.startswith(OFFICE_TEMP_PREFIXES):
        return True
    
    # Fichiers temporaires Office comme ~WRLxxxx.tmp
    if name.lower().endswith(".tmp") and (name.startswith("~") or name.startswith(".~")):
        return True
    
    return False
