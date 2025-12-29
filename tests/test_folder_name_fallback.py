"""
Tests pour le fallback identity depuis folder name (QUICK WIN)

Objectif: Réduire les NO-GO en inférant name/surname depuis le nom du dossier
quand aucune autre source n'est disponible.
"""
import pytest
from pathlib import Path

from src.rhpro.identity_extractor import extract_identity_from_folder_name


class TestFolderNameIdentityExtraction:
    """Tests pour extract_identity_from_folder_name()"""
    
    def test_pattern_surname_firstname_uppercase(self):
        """Test pattern 'SCHMIDT Mélanie' (nom en majuscules)"""
        result = extract_identity_from_folder_name("SCHMIDT Mélanie")
        
        assert result['surname'] == "SCHMIDT"
        assert result['name'] == "Mélanie"
        assert result['full_name'] == "SCHMIDT Mélanie"
        assert result['avs'] == ""  # Pas d'AVS dans folder name
    
    def test_pattern_multi_word_surname(self):
        """Test pattern 'CAMPOS DA COSTA Paula' (nom multi-mots en majuscules)"""
        result = extract_identity_from_folder_name("CAMPOS DA COSTA Paula")
        
        assert result['surname'] == "CAMPOS DA COSTA"
        assert result['name'] == "Paula"
        assert result['full_name'] == "CAMPOS DA COSTA Paula"
    
    def test_pattern_firstname_surname_mixed_case(self):
        """Test pattern 'Jean Dupont' (pas de majuscules claires)"""
        result = extract_identity_from_folder_name("Jean Dupont")
        
        # Convention: dernier mot = nom
        assert result['surname'] == "Dupont"
        assert result['name'] == "Jean"
    
    def test_pattern_hyphenated_surname(self):
        """Test pattern 'Dupont-Martin Sophie' (nom composé)"""
        result = extract_identity_from_folder_name("Dupont-Martin Sophie")
        
        # Le tiret est remplacé par espace, donc "Dupont Martin" puis dernier mot
        assert result['surname'] == "Sophie"
        assert result['name'] == "Dupont Martin"
    
    def test_with_numeric_prefix(self):
        """Test avec préfixe numérique '001_SCHMIDT Mélanie'"""
        result = extract_identity_from_folder_name("001_SCHMIDT Mélanie")
        
        assert result['surname'] == "SCHMIDT"
        assert result['name'] == "Mélanie"
    
    def test_with_underscores(self):
        """Test avec underscores 'MARTIN_Sophie'"""
        result = extract_identity_from_folder_name("MARTIN_Sophie")
        
        assert result['surname'] == "MARTIN"
        assert result['name'] == "Sophie"
    
    def test_single_word(self):
        """Test avec un seul mot 'DUPONT'"""
        result = extract_identity_from_folder_name("DUPONT")
        
        assert result['surname'] == "DUPONT"
        assert result['name'] == ""
    
    def test_empty_string(self):
        """Test avec string vide"""
        result = extract_identity_from_folder_name("")
        
        assert result['surname'] == ""
        assert result['name'] == ""
        assert result['full_name'] == ""
    
    def test_real_world_examples(self):
        """Test avec exemples réels du dataset"""
        examples = [
            ("KARAOUI Malik", {"surname": "KARAOUI", "name": "Malik"}),
            ("DA SILVA Maria", {"surname": "DA SILVA", "name": "Maria"}),
            ("VAN DEN BERG Jan", {"surname": "VAN DEN BERG", "name": "Jan"}),
            ("O'CONNOR Patrick", {"surname": "O'CONNOR", "name": "Patrick"}),  # Apostrophe gardée
        ]
        
        for folder_name, expected in examples:
            result = extract_identity_from_folder_name(folder_name)
            assert result['surname'] == expected['surname'], f"Failed for {folder_name}"
            assert result['name'] == expected['name'], f"Failed for {folder_name}"


class TestFolderNameFallbackIntegration:
    """Tests d'intégration du fallback dans le normalizer"""
    
    def test_fallback_when_no_identity_in_document(self):
        """Test que le fallback s'active quand aucune identity dans le document"""
        from src.rhpro.segmenter import Segment
        from src.rhpro.docx_structure import Paragraph
        from src.rhpro.ruleset_loader import load_ruleset
        from src.rhpro.normalizer import Normalizer
        
        ruleset_path = Path.cwd() / "config" / "rulesets" / "rhpro_v1.yaml"
        ruleset = load_ruleset(str(ruleset_path))
        normalizer = Normalizer(ruleset)
        
        # Créer un segment minimal sans identity
        paragraph = Paragraph(
            text="Ceci est un document test sans identité",
            style_name="Normal",
            is_bold=False,
            font_size=11.0,
            is_all_caps=False,
            numbering_prefix=""
        )
        
        segment = Segment(
            raw_title="Test",
            normalized_title="test",
            level=0,
            paragraphs=[paragraph],
            mapped_section_id=None,
            confidence=0.0
        )
        
        # Normaliser AVEC client_name
        result = normalizer.normalize(
            [segment],
            client_name="SCHMIDT Mélanie"
        )
        
        identity = result['normalized']['identity']
        
        # Identity devrait être inférée depuis folder name
        assert identity['surname'] == "SCHMIDT"
        assert identity['name'] == "Mélanie"
        
        # Vérifier warning
        warnings = result['report']['warnings']
        assert any("folder name" in w.lower() for w in warnings)
    
    def test_no_fallback_when_identity_already_present(self):
        """Test que le fallback ne s'active PAS si identity déjà présente"""
        from src.rhpro.segmenter import Segment
        from src.rhpro.docx_structure import Paragraph
        from src.rhpro.ruleset_loader import load_ruleset
        from src.rhpro.normalizer import Normalizer
        
        ruleset_path = Path.cwd() / "config" / "rulesets" / "rhpro_v1.yaml"
        ruleset = load_ruleset(str(ruleset_path))
        normalizer = Normalizer(ruleset)
        
        # Créer un segment identity avec données
        paragraph = Paragraph(
            text="Monsieur Jean DUPONT — 756.1234.5678.90",
            style_name="Normal",
            is_bold=True,
            font_size=11.0,
            is_all_caps=False,
            numbering_prefix=""
        )
        
        segment = Segment(
            raw_title="Identité",
            normalized_title="identite",
            level=0,
            paragraphs=[paragraph],
            mapped_section_id="identity",
            confidence=0.95
        )
        
        # Normaliser avec client_name DIFFÉRENT
        result = normalizer.normalize(
            [segment],
            client_name="MARTIN Sophie"  # Différent de DUPONT
        )
        
        identity = result['normalized']['identity']
        
        # Identity devrait venir du document, PAS du folder name
        assert identity['surname'] == "DUPONT"
        assert identity['name'] == "Jean"
        assert identity['avs'] == "756.1234.5678.90"
        
        # Pas de warning folder name
        warnings = result['report']['warnings']
        assert not any("folder name" in w.lower() for w in warnings)
    
    def test_fallback_priority_rag_before_folder(self):
        """Test que RAG sources ont priorité sur folder name"""
        from src.rhpro.segmenter import Segment
        from src.rhpro.docx_structure import Paragraph
        from src.rhpro.ruleset_loader import load_ruleset
        from src.rhpro.normalizer import Normalizer
        import tempfile
        
        ruleset_path = Path.cwd() / "config" / "rulesets" / "rhpro_v1.yaml"
        ruleset = load_ruleset(str(ruleset_path))
        normalizer = Normalizer(ruleset)
        
        # Créer un segment vide
        paragraph = Paragraph(
            text="Test",
            style_name="Normal",
            is_bold=False,
            font_size=11.0,
            is_all_caps=False,
            numbering_prefix=""
        )
        
        segment = Segment(
            raw_title="Test",
            normalized_title="test",
            level=0,
            paragraphs=[paragraph],
            mapped_section_id=None,
            confidence=0.0
        )
        
        # Créer un fichier RAG avec identity
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("Madame Claire ROUSSEAU — 756.9999.8888.77\n")
            rag_file = f.name
        
        try:
            # Normaliser avec RAG + client_name différent
            result = normalizer.normalize(
                [segment],
                rag_sources=[rag_file],
                client_name="MARTIN Sophie"  # Différent
            )
            
            identity = result['normalized']['identity']
            
            # Identity devrait venir de RAG, pas du folder name
            assert identity['surname'] == "ROUSSEAU"
            assert identity['name'] == "Claire"
            
            # Warning RAG, pas folder name
            warnings = result['report']['warnings']
            assert any("RAG sources" in w for w in warnings)
            assert not any("folder name" in w.lower() for w in warnings)
        
        finally:
            Path(rag_file).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
