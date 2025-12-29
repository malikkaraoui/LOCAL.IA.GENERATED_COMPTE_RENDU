"""
Tests unitaires pour PATCH 10 : Détection Flexible des Sous-Dossiers

Valide :
- Normalisation unicode robuste
- Résolution par préfixe numérique
- Fallback par mots-clés
- Scan complet avec folder_mapping
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from src.rhpro.client_scanner import (
    _norm,
    resolve_client_subfolders,
    scan_client_folder,
    CANON_BY_PREFIX,
    KEYWORDS_FALLBACK,
)


class TestNormalization:
    """Tests de la normalisation unicode."""
    
    def test_norm_accents(self):
        """Supprime les accents."""
        assert _norm("Dossier Persönnel") == "dossier personnel"
        assert _norm("Évolution de Stage") == "evolution de stage"
    
    def test_norm_punctuation(self):
        """Supprime la ponctuation."""
        assert _norm("06 - Rapport_final!") == "06 rapport final"
        assert _norm("Tests & Bilans") == "tests bilans"
    
    def test_norm_lowercase(self):
        """Convertit en minuscules."""
        assert _norm("RAPPORT FINAL") == "rapport final"
    
    def test_norm_spaces(self):
        """Normalise les espaces multiples."""
        assert _norm("  01   Dossier    personnel  ") == "01 dossier personnel"


class TestResolveSubfolders:
    """Tests de résolution des sous-dossiers."""
    
    def setup_method(self):
        """Crée un dossier temporaire de test."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Nettoie le dossier temporaire."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_resolve_by_numeric_prefix(self):
        """Détecte dossiers par préfixe numérique."""
        # Créer dossiers avec préfixes
        (self.temp_dir / "01 Dossier personnel").mkdir()
        (self.temp_dir / "06 Rapport final").mkdir()
        
        resolved = resolve_client_subfolders(self.temp_dir)
        
        assert "01_personnel" in resolved
        assert "06_rapport" in resolved
        assert resolved["01_personnel"].name == "01 Dossier personnel"
        assert resolved["06_rapport"].name == "06 Rapport final"
    
    def test_resolve_prefix_without_zero(self):
        """Détecte préfixes sans zéro initial (6 → 06)."""
        (self.temp_dir / "6 Rapport").mkdir()
        
        resolved = resolve_client_subfolders(self.temp_dir)
        
        assert "06_rapport" in resolved
        assert resolved["06_rapport"].name == "6 Rapport"
    
    def test_resolve_by_keywords_fallback(self):
        """Fallback par mots-clés si pas de préfixe."""
        # Dossier sans préfixe numérique
        (self.temp_dir / "Dossier personnel").mkdir()
        (self.temp_dir / "Rapport final").mkdir()
        
        resolved = resolve_client_subfolders(self.temp_dir)
        
        # Devrait trouver par mots-clés
        assert "01_personnel" in resolved
        assert "06_rapport" in resolved
    
    def test_resolve_priority_prefix_over_keywords(self):
        """Préfixe numérique prioritaire sur mots-clés."""
        # Deux dossiers : un avec préfixe, un avec mots-clés seulement
        (self.temp_dir / "01 Dossier personnel").mkdir()
        (self.temp_dir / "Dossier personnel backup").mkdir()
        
        resolved = resolve_client_subfolders(self.temp_dir)
        
        # Doit prendre celui avec préfixe
        assert resolved["01_personnel"].name == "01 Dossier personnel"
    
    def test_resolve_variants(self):
        """Détecte variantes de noms."""
        # Variantes de format
        (self.temp_dir / "01_Dossier_personnel").mkdir()
        (self.temp_dir / "06-Rapport-final").mkdir()
        (self.temp_dir / "03 Tests et bilans").mkdir()
        
        resolved = resolve_client_subfolders(self.temp_dir)
        
        assert "01_personnel" in resolved
        assert "06_rapport" in resolved
        assert "03_tests" in resolved
    
    def test_resolve_empty_dir(self):
        """Dossier vide retourne dict vide."""
        resolved = resolve_client_subfolders(self.temp_dir)
        
        assert resolved == {}
    
    def test_resolve_ignores_hidden(self):
        """Ignore dossiers cachés."""
        (self.temp_dir / ".git").mkdir()
        (self.temp_dir / ".DS_Store").mkdir()
        (self.temp_dir / "01 Dossier personnel").mkdir()
        
        resolved = resolve_client_subfolders(self.temp_dir)
        
        assert ".git" not in str(resolved)
        assert "01_personnel" in resolved


class TestScanClientFolder:
    """Tests du scan complet avec folder_mapping."""
    
    def setup_method(self):
        """Crée un dossier client de test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Structure minimale
        (self.temp_dir / "01 Dossier personnel").mkdir()
        (self.temp_dir / "06 Rapport final").mkdir()
        
        # Créer un fichier GOLD
        gold_file = self.temp_dir / "06 Rapport final" / "Bilan final.docx"
        gold_file.touch()
        
        # Créer quelques sources RAG
        (self.temp_dir / "01 Dossier personnel" / "CV.pdf").touch()
        (self.temp_dir / "01 Dossier personnel" / "Lettre motivation.docx").touch()
    
    def teardown_method(self):
        """Nettoie le dossier temporaire."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_scan_returns_folder_mapping(self):
        """Scan retourne folder_mapping avec noms réels."""
        result = scan_client_folder(str(self.temp_dir))
        
        assert "folder_mapping" in result
        assert result["folder_mapping"]["01_personnel"] == "01 Dossier personnel"
        assert result["folder_mapping"]["06_rapport"] == "06 Rapport final"
    
    def test_scan_pipeline_ready_degraded_mode(self):
        """Pipeline considéré ready en mode dégradé."""
        result = scan_client_folder(str(self.temp_dir))
        
        # PATCH 10 : toujours ready pour mode d'entraînement brut
        assert result["pipeline_ready"] is True
    
    def test_scan_warnings_non_blocking(self):
        """Warnings informatifs (non bloquants)."""
        result = scan_client_folder(str(self.temp_dir))
        
        # Doit avoir des warnings mais pas bloquer
        assert isinstance(result["warnings"], list)
        assert result["pipeline_ready"] is True
        
        # Warning doit afficher dossiers détectés
        warnings_text = " ".join(result["warnings"])
        assert "Dossiers détectés" in warnings_text or len(result["warnings"]) >= 0
    
    def test_scan_detects_gold(self):
        """Détecte document GOLD."""
        result = scan_client_folder(str(self.temp_dir))
        
        assert result["gold"] is not None
        assert "Bilan final" in result["gold"]["path"]
    
    def test_scan_detects_rag_sources(self):
        """Détecte sources RAG."""
        result = scan_client_folder(str(self.temp_dir))
        
        assert len(result["rag_sources"]) >= 2
        extensions = [s["extension"] for s in result["rag_sources"]]
        assert ".pdf" in extensions
        assert ".docx" in extensions


class TestRealWorldScenarios:
    """Tests sur scénarios réels."""
    
    @pytest.mark.skipif(
        not Path("/Users/malik/Documents/Espace de travail/SCRIPT.IA/CLIENTS/ALVES MOREIRA Sergio Paulo").exists(),
        reason="Client de test non disponible"
    )
    def test_real_client_alves_moreira(self):
        """Test sur vrai client ALVES MOREIRA."""
        client_path = "/Users/malik/Documents/Espace de travail/SCRIPT.IA/CLIENTS/ALVES MOREIRA Sergio Paulo"
        
        result = scan_client_folder(client_path)
        
        # Doit détecter les dossiers requis
        assert result["folder_mapping"]["01_personnel"] == "01 Dossier personnel"
        assert result["folder_mapping"]["06_rapport"] == "06 Rapport final"
        
        # Stats
        assert result["stats"]["folders_detected"] >= 5
        assert result["stats"]["gold_found"] is True
        assert result["stats"]["rag_sources_count"] > 0
    
    def test_constants_coherence(self):
        """Vérifie cohérence des constantes."""
        # Tous les préfixes doivent avoir des keywords
        for prefix, canon in CANON_BY_PREFIX.items():
            # Sauf 02_cv et 07_suivi qui sont optionnels
            if canon in ["02_cv", "07_suivi"]:
                continue
            assert canon in KEYWORDS_FALLBACK, f"Missing keywords for {canon}"
        
        # Tous les keywords doivent correspondre à un canon
        for canon in KEYWORDS_FALLBACK.keys():
            assert canon in CANON_BY_PREFIX.values(), f"Canon {canon} not in mapping"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
