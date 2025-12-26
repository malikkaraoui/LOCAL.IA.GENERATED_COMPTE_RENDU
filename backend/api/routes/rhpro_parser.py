"""
Exemple d'endpoint FastAPI pour le parsing RH-Pro
À intégrer dans backend/api/routes/
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
from typing import Dict, Any
import tempfile
import os

from src.rhpro.parse_bilan import parse_bilan_from_paths


router = APIRouter(prefix="/rhpro", tags=["RH-Pro"])


@router.post("/parse-bilan")
async def parse_bilan(
    file: UploadFile = File(..., description="Fichier DOCX du bilan RH-Pro")
) -> JSONResponse:
    """
    Parse un bilan RH-Pro (DOCX) et retourne le JSON normalisé + rapport
    
    Returns:
        {
            "normalized": {...},  # Dict normalisé selon schema
            "report": {...}       # Métadonnées du parsing
        }
    """
    # Validation du type de fichier
    if not file.filename.endswith('.docx'):
        raise HTTPException(
            status_code=400,
            detail="Le fichier doit être au format DOCX"
        )
    
    # Sauvegarder temporairement le fichier uploadé
    with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    try:
        # Parser le document
        result = parse_bilan_from_paths(tmp_path)
        
        # Enrichir avec metadata
        result['metadata'] = {
            'filename': file.filename,
            'size_bytes': len(content),
            'coverage': result['report']['coverage_ratio']
        }
        
        return JSONResponse(content=result)
    
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du parsing: {str(e)}"
        )
    
    finally:
        # Nettoyer le fichier temporaire
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.get("/ruleset/version")
async def get_ruleset_version() -> Dict[str, Any]:
    """Retourne la version du ruleset utilisé"""
    from src.rhpro.ruleset_loader import load_ruleset
    
    project_root = Path(__file__).parent.parent.parent
    ruleset_path = project_root / 'config' / 'rulesets' / 'rhpro_v1.yaml'
    
    ruleset = load_ruleset(str(ruleset_path))
    
    return {
        "version": ruleset.version,
        "language": ruleset.language,
        "doc_type": ruleset.doc_type,
        "total_sections": len(ruleset.get_all_section_ids()),
        "top_level_sections": len(ruleset.sections)
    }


# ==========================================
# Pour intégrer au backend, ajouter dans backend/api/main.py:
# 
# from .routes import rhpro_parser
# app.include_router(rhpro_parser.router)
# ==========================================


"""
Exemple d'utilisation avec curl:

# Upload et parse un bilan
curl -X POST "http://localhost:8000/rhpro/parse-bilan" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/bilan.docx"

# Obtenir la version du ruleset
curl "http://localhost:8000/rhpro/ruleset/version"

Exemple de réponse:
{
  "normalized": {
    "identity": {"name": "", "surname": "", "avs": ""},
    "profession_formation": {...},
    ...
  },
  "report": {
    "found_sections": [...],
    "missing_required_sections": [...],
    "coverage_ratio": 0.85
  },
  "metadata": {
    "filename": "bilan.docx",
    "size_bytes": 45123,
    "coverage": 0.85
  }
}
"""
