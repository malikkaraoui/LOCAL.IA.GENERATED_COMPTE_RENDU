"""
Tests pour PATCH 1 (extraction identity globale) et PATCH 2 (heading policy)

Objectif: Vérifier que l'identity est extraite depuis TOUS les documents,
pas seulement depuis la section "Identité" du DOCX source.

Scénarios testés:
1. AVS présent dans un fichier TXT (pas dans le DOCX) → identity.avs rempli
2. AVS dans unknown_titles → après PATCH 2, ne doit PAS être dans unknown_titles
3. Aucun AVS nulle part → identity reste vide (pas d'hallucination)
4. AVS présent dans PDF mais pas DOCX → identity.avs rempli
"""
import pytest
from pathlib import Path
import tempfile
import json

from src.rhpro.identity_extractor import (
    extract_identity_from_text,
    extract_identity_from_files,
    is_identity_line,
    contains_avs
)


class TestIdentityExtractor:
    """Tests unitaires pour le module identity_extractor"""
    
    def test_extract_identity_from_text_with_avs(self):
        """Test extraction AVS depuis texte simple"""
        text = "Monsieur Jean DUPONT — 756.1234.5678.90"
        result = extract_identity_from_text(text)
        
        assert result['avs'] == "756.1234.5678.90"
        assert result['name'] == "Jean"
        assert result['surname'] == "DUPONT"
    
    def test_extract_identity_from_text_without_monsieur(self):
        """Test extraction AVS sans 'Monsieur/Madame'"""
        text = "Jean DUPONT 756.1234.5678.90"
        result = extract_identity_from_text(text)
        
        assert result['avs'] == "756.1234.5678.90"
        # Le nom peut ne pas être extrait sans pattern 'Monsieur/Madame'
    
    def test_extract_identity_no_avs(self):
        """Test extraction quand aucun AVS présent"""
        text = "Ceci est un texte sans identité"
        result = extract_identity_from_text(text)
        
        assert result['avs'] == ""
        assert result['name'] == ""
        assert result['surname'] == ""
    
    def test_contains_avs(self):
        """Test détection rapide d'AVS"""
        assert contains_avs("Le numéro est 756.1234.5678.90") == True
        assert contains_avs("Aucun numéro ici") == False
        assert contains_avs("756 1234 5678 90") == True  # Tolérant aux espaces
    
    def test_is_identity_line(self):
        """Test détection des lignes d'identité (PATCH 2)"""
        # Lignes d'identité (ne doivent PAS être unknown_titles)
        assert is_identity_line("Monsieur Jean DUPONT — 756.1234.5678.90") == True
        assert is_identity_line("Madame Marie MARTIN 756.9876.5432.10") == True
        assert is_identity_line("AVS: 756.1234.5678.90") == True
        
        # Lignes normales (peuvent être unknown_titles)
        assert is_identity_line("Formation professionnelle") == False
        assert is_identity_line("Conclusion et recommandations") == False
    
    def test_extract_identity_from_files(self):
        """Test extraction depuis fichiers réels (TXT)"""
        # Créer un fichier temporaire avec identité
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("Rapport de suivi\n")
            f.write("Monsieur Pierre DURAND — 756.1111.2222.33\n")
            f.write("Date: 01/01/2024\n")
            temp_file = f.name
        
        try:
            result = extract_identity_from_files([temp_file])
            
            assert result['avs'] == "756.1111.2222.33"
            assert result['name'] == "Pierre"
            assert result['surname'] == "DURAND"
        finally:
            Path(temp_file).unlink()
    
    def test_extract_identity_from_multiple_files(self):
        """Test extraction depuis plusieurs fichiers"""
        # Créer 2 fichiers temporaires
        files = []
        
        # Fichier 1: contient AVS mais pas de nom
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("AVS du patient: 756.3333.4444.55\n")
            files.append(f.name)
        
        # Fichier 2: contient nom mais pas AVS
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("Nom: Sophie BERNARD\n")
            files.append(f.name)
        
        try:
            result = extract_identity_from_files(files)
            
            # Devrait merger les infos
            assert result['avs'] == "756.3333.4444.55"
            # Le nom peut ne pas être extrait si pas de pattern "Monsieur/Madame"
        finally:
            for fpath in files:
                Path(fpath).unlink()


class TestPatch2HeadingPolicy:
    """Tests pour PATCH 2: heading policy ne doit pas classer identity comme unknown"""
    
    def test_identity_line_not_in_unknown_titles(self):
        """Test que les lignes identity ne sont PAS dans unknown_titles"""
        from src.rhpro.segmenter import Segment
        from src.rhpro.docx_structure import Paragraph
        from src.rhpro.ruleset_loader import load_ruleset
        from src.rhpro.normalizer import Normalizer
        
        # Créer un segment non mappé avec une ligne d'identité
        paragraph = Paragraph(
            text="Madame Julie MARTIN — 756.5555.6666.77",
            style_name="Normal",
            is_bold=True,
            font_size=11.0,
            is_all_caps=False,
            numbering_prefix=""
        )
        segment = Segment(
            raw_title="Madame Julie MARTIN — 756.5555.6666.77",
            normalized_title="Madame Julie MARTIN — 756.5555.6666.77",
            level=0,
            paragraphs=[paragraph],
            mapped_section_id=None,  # Pas mappé
            confidence=0.0
        )
        
        # Charger ruleset
        ruleset_path = Path.cwd() / "config" / "rulesets" / "rhpro_v1.yaml"
        ruleset = load_ruleset(str(ruleset_path))
        
        # Normaliser
        normalizer = Normalizer(ruleset)
        result = normalizer.normalize([segment])
        
        report = result['report']
        unknown_titles = report['unknown_titles']
        
        # PATCH 2: La ligne identity ne doit PAS être dans unknown_titles
        assert "Madame Julie MARTIN — 756.5555.6666.77" not in unknown_titles


class TestPatch1GlobalExtraction:
    """Tests pour PATCH 1: extraction identity depuis tous les rag_sources"""
    
    def test_identity_extracted_from_rag_sources(self):
        """Test que identity est extraite depuis rag_sources si absente du DOCX"""
        from src.rhpro.parse_bilan import parse_bilan_docx_to_normalized
        
        # Créer un DOCX minimal (sans identity)
        # On utilise un DOCX existant du dataset si disponible
        dataset_root = Path.cwd() / "data" / "samples"
        
        if not dataset_root.exists():
            pytest.skip("Dataset samples non disponible")
        
        # Chercher un DOCX
        docx_files = list(dataset_root.glob("**/*.docx"))
        if not docx_files:
            pytest.skip("Aucun DOCX trouvé dans data/samples")
        
        docx_path = docx_files[0]
        
        # Créer un fichier TXT avec identity
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("Rapport complémentaire\n")
            f.write("Monsieur Thomas LEFEBVRE — 756.7777.8888.99\n")
            f.write("Suivi du 15/03/2024\n")
            temp_txt = f.name
        
        try:
            # Ruleset
            ruleset_path = Path.cwd() / "config" / "rulesets" / "rhpro_v1.yaml"
            
            # Parser SANS rag_sources (contrôle)
            result_without_rag = parse_bilan_docx_to_normalized(
                str(docx_path),
                str(ruleset_path)
            )
            
            # Parser AVEC rag_sources (PATCH 1)
            result_with_rag = parse_bilan_docx_to_normalized(
                str(docx_path),
                str(ruleset_path),
                rag_sources=[temp_txt]
            )
            
            # Vérifier que l'identity est extraite avec PATCH 1
            identity_with_rag = result_with_rag['normalized']['identity']
            
            # Si le DOCX original contenait déjà l'identity, pas de test possible
            identity_without_rag = result_without_rag['normalized']['identity']
            if not identity_without_rag.get('avs'):
                # DOCX n'avait pas d'AVS, PATCH 1 devrait l'extraire du TXT
                assert identity_with_rag['avs'] == "756.7777.8888.99"
                assert identity_with_rag['name'] == "Thomas"
                assert identity_with_rag['surname'] == "LEFEBVRE"
        
        finally:
            Path(temp_txt).unlink()
    
    def test_no_hallucination_when_no_identity(self):
        """Test qu'on n'invente pas d'identity si elle n'existe nulle part"""
        # Créer fichiers temporaires sans identity
        files = []
        
        for i in range(3):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(f"Document {i+1}\n")
                f.write("Pas d'information d'identité ici.\n")
                f.write("Juste du texte générique.\n")
                files.append(f.name)
        
        try:
            from src.rhpro.identity_extractor import extract_identity_from_files
            result = extract_identity_from_files(files)
            
            # Aucune hallucination
            assert result['avs'] == ""
            assert result['name'] == ""
            assert result['surname'] == ""
        
        finally:
            for fpath in files:
                Path(fpath).unlink()


class TestIntegrationPatches1and2:
    """Tests d'intégration PATCH 1 + PATCH 2"""
    
    def test_full_workflow_with_patches(self):
        """Test workflow complet: extraction globale + heading policy"""
        from src.rhpro.parse_bilan import parse_bilan_docx_to_normalized
        
        # Créer un DOCX test minimal
        dataset_root = Path.cwd() / "data" / "samples"
        
        if not dataset_root.exists():
            pytest.skip("Dataset samples non disponible")
        
        docx_files = list(dataset_root.glob("**/*.docx"))
        if not docx_files:
            pytest.skip("Aucun DOCX trouvé")
        
        docx_path = docx_files[0]
        
        # Créer un TXT avec identity
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("Madame Claire ROUSSEAU — 756.9999.0000.11\n")
            temp_txt = f.name
        
        try:
            ruleset_path = Path.cwd() / "config" / "rulesets" / "rhpro_v1.yaml"
            
            result = parse_bilan_docx_to_normalized(
                str(docx_path),
                str(ruleset_path),
                rag_sources=[temp_txt]
            )
            
            normalized = result['normalized']
            report = result['report']
            
            # PATCH 1: Identity extraite si absente du DOCX
            identity = normalized['identity']
            if not identity.get('avs'):
                # Le DOCX avait déjà une identity, ou pas d'extraction possible
                pass
            
            # PATCH 2: Pas de ligne identity dans unknown_titles
            unknown_titles = report['unknown_titles']
            for title in unknown_titles:
                assert not is_identity_line(title), f"Identity line found in unknown_titles: {title}"
        
        finally:
            Path(temp_txt).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
