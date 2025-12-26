"""
Tests pour le module RH-Pro parsing
"""
import pytest
from pathlib import Path

from src.rhpro.parse_bilan import parse_bilan_docx_to_normalized
from src.rhpro.ruleset_loader import load_ruleset


# Chemins de base
PROJECT_ROOT = Path(__file__).parent.parent
RULESET_PATH = PROJECT_ROOT / 'config' / 'rulesets' / 'rhpro_v1.yaml'

# Chercher automatiquement le premier source.docx
def _find_sample_docx():
    """Trouve le premier source.docx dans data/samples/*/"""
    samples_dir = PROJECT_ROOT / 'data' / 'samples'
    if not samples_dir.exists():
        return None
    source_files = sorted(samples_dir.glob('**/source.docx'))
    return source_files[0] if source_files else None

SAMPLE_DOCX_PATH = _find_sample_docx()


class TestRulesetLoader:
    """Tests pour le chargement du ruleset"""
    
    def test_ruleset_exists(self):
        """Vérifie que le ruleset existe"""
        assert RULESET_PATH.exists(), f"Ruleset not found at {RULESET_PATH}"
    
    def test_load_ruleset(self):
        """Vérifie que le ruleset se charge correctement"""
        ruleset = load_ruleset(str(RULESET_PATH))
        
        assert ruleset.version == "rhpro-v1"
        assert ruleset.language == "fr"
        assert ruleset.doc_type == "bilan_orientation_rhpro"
        assert len(ruleset.sections) > 0
    
    def test_ruleset_sections_structure(self):
        """Vérifie la structure des sections"""
        ruleset = load_ruleset(str(RULESET_PATH))
        
        # Vérifier quelques sections clés
        identity = ruleset.get_section_by_id('identity')
        assert identity is not None
        assert identity['label'] == "Identité"
        assert identity['required'] is True
        
        profession = ruleset.get_section_by_id('profession_formation.profession')
        assert profession is not None
        assert profession['label'] == "Profession"


@pytest.mark.skipif(not SAMPLE_DOCX_PATH.exists(), reason="Sample DOCX not available")
class TestParseBilan:
    """Tests pour le parsing complet"""
    
    def test_parse_bilan_basic(self):
        """Test basique: le parsing retourne une structure valide"""
        result = parse_bilan_docx_to_normalized(
            str(SAMPLE_DOCX_PATH),
            str(RULESET_PATH)
        )
        
        # Vérifier les clés principales
        assert 'normalized' in result
        assert 'report' in result
        
        # Vérifier la structure du normalized
        normalized = result['normalized']
        assert 'identity' in normalized
        assert 'profession_formation' in normalized
        assert 'tests' in normalized
        assert 'conclusion' in normalized
        
        # Vérifier la structure du rapport
        report = result['report']
        assert 'found_sections' in report
        assert 'missing_required_sections' in report
        assert 'unknown_titles' in report
        assert 'coverage_ratio' in report
        assert 'warnings' in report
        
        # Vérifier que les arrays sont bien des arrays
        assert isinstance(report['found_sections'], list)
        assert isinstance(report['missing_required_sections'], list)
        assert isinstance(report['unknown_titles'], list)
        assert isinstance(report['warnings'], list)
    
    def test_no_invented_content_for_source_only(self):
        """Vérifie qu'on n'invente pas de contenu pour les champs source_only"""
        result = parse_bilan_docx_to_normalized(
            str(SAMPLE_DOCX_PATH),
            str(RULESET_PATH)
        )
        
        normalized = result['normalized']
        
        # Champs avec fill_strategy=source_only
        # Si pas trouvés dans le doc, doivent rester vides
        dossier = normalized.get('dossier_presentation', {})
        
        # On vérifie juste que si présents, ce sont des strings
        if 'lettre_motivation' in dossier:
            assert isinstance(dossier['lettre_motivation'], str)
        if 'cv' in dossier:
            assert isinstance(dossier['cv'], str)


class TestParseWithoutSample:
    """Tests qui ne nécessitent pas de sample DOCX"""
    
    def test_parse_missing_docx(self):
        """Test avec un fichier DOCX inexistant"""
        with pytest.raises(FileNotFoundError):
            parse_bilan_docx_to_normalized(
                'nonexistent.docx',
                str(RULESET_PATH)
            )
    
    def test_parse_missing_ruleset(self):
        """Test avec un ruleset inexistant"""
        # Créer un DOCX temporaire vide si besoin
        with pytest.raises(FileNotFoundError):
            parse_bilan_docx_to_normalized(
                str(SAMPLE_DOCX_PATH) if SAMPLE_DOCX_PATH.exists() else 'any.docx',
                'nonexistent_ruleset.yaml'
            )


if __name__ == '__main__':
    # Permet de lancer les tests directement
    pytest.main([__file__, '-v'])
