"""
Tests pour les améliorations Step 6
"""
import pytest
from pathlib import Path

from src.rhpro.parse_bilan import parse_bilan_from_paths
from src.rhpro.inline_extractor import InlineExtractor
from src.rhpro.mapper import IGNORE_PATTERNS
import re


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


class TestIgnoreTitles:
    """Tests pour l'ignore list des titres génériques"""
    
    def test_bilan_orientation_ignored(self):
        """Vérifie que 'BILAN D'ORIENTATION...' est ignoré"""
        titles_to_ignore = [
            "BILAN D'ORIENTATION PROFESSIONNELLE",
            "BILAN D'ORIENTATION",
            "Bilan d'orientation",
        ]
        
        for title in titles_to_ignore:
            should_ignore = any(
                re.search(pattern, title, re.IGNORECASE)
                for pattern in IGNORE_PATTERNS
            )
            assert should_ignore, f"'{title}' devrait être ignoré"
    
    def test_valid_titles_not_ignored(self):
        """Vérifie que les vrais titres ne sont pas ignorés"""
        valid_titles = [
            "Orientation & Formation",
            "Profession & Formation",
            "Conclusion",
            "Tests"
        ]
        
        for title in valid_titles:
            should_ignore = any(
                re.search(pattern, title, re.IGNORECASE)
                for pattern in IGNORE_PATTERNS
            )
            assert not should_ignore, f"'{title}' ne devrait PAS être ignoré"


class TestInlineExtractor:
    """Tests pour l'extraction inline de sous-sections"""
    
    def test_extract_profession_formation(self):
        """Test extraction de profession et formation"""
        content = """Profession
Le bénéficiaire a travaillé pendant 15 ans en informatique.

Formation
CFC obtenu en 2005. Formation continue en 2018."""
        
        extractor = InlineExtractor()
        result = extractor.extract_subsections('profession_formation', content)
        
        assert result is not None
        assert 'profession' in result
        assert 'formation' in result
        assert '15 ans' in result['profession']
        assert 'CFC' in result['formation']
    
    def test_extract_orientation_formation(self):
        """Test extraction de orientation et stage"""
        content = """Orientation
Orientation vers la cybersécurité.

Stage
Stage de 3 mois recommandé."""
        
        extractor = InlineExtractor()
        result = extractor.extract_subsections('orientation_formation', content)
        
        assert result is not None
        assert 'orientation' in result
        assert 'stage' in result
        assert 'cybersécurité' in result['orientation']
        assert '3 mois' in result['stage']
    
    def test_extract_competences(self):
        """Test extraction de compétences sociales et professionnelles"""
        content = """Sociales
Bonnes capacités de communication.

Professionnelles
Expertise technique en systèmes."""
        
        extractor = InlineExtractor()
        result = extractor.extract_subsections('competences', content)
        
        assert result is not None
        assert 'sociales' in result
        assert 'professionnelles' in result


@pytest.mark.skipif(not SAMPLE_DOCX_PATH.exists(), reason="Sample DOCX not available")
class TestStep6Improvements:
    """Tests pour les améliorations Step 6 sur le document complet"""
    
    def test_bilan_not_mapped_to_orientation(self):
        """Vérifie que 'BILAN D'ORIENTATION...' n'est plus mappé à orientation_formation"""
        result = parse_bilan_from_paths(
            str(SAMPLE_DOCX_PATH),
            str(RULESET_PATH)
        )
        
        report = result['report']
        
        # Vérifier que BILAN D'ORIENTATION est dans unknown_titles
        assert any(
            'BILAN' in title.upper() and 'ORIENTATION' in title.upper()
            for title in report['unknown_titles']
        ), "BILAN D'ORIENTATION devrait être dans unknown_titles"
        
        # Vérifier qu'aucune section ne mappe ce titre
        for section in report['found_sections']:
            title = section['title']
            if 'BILAN' in title.upper() and 'ORIENTATION' in title.upper():
                pytest.fail(f"Le titre '{title}' ne devrait pas être mappé")
    
    def test_profession_formation_as_object(self):
        """Vérifie que profession_formation est un objet avec sous-sections"""
        result = parse_bilan_from_paths(
            str(SAMPLE_DOCX_PATH),
            str(RULESET_PATH)
        )
        
        normalized = result['normalized']
        profession_formation = normalized['profession_formation']
        
        # Doit être un dict, pas une string
        assert isinstance(profession_formation, dict), \
            "profession_formation doit être un objet"
        
        # Doit contenir profession et formation
        assert 'profession' in profession_formation
        assert 'formation' in profession_formation
        
        # Les sous-sections doivent être remplies
        assert profession_formation['profession'], \
            "profession devrait être remplie"
        assert profession_formation['formation'], \
            "formation devrait être remplie"
    
    def test_orientation_formation_as_object(self):
        """Vérifie que orientation_formation est un objet avec sous-sections"""
        result = parse_bilan_from_paths(
            str(SAMPLE_DOCX_PATH),
            str(RULESET_PATH)
        )
        
        normalized = result['normalized']
        orientation_formation = normalized['orientation_formation']
        
        # Doit être un dict
        assert isinstance(orientation_formation, dict)
        
        # Doit contenir orientation et stage
        assert 'orientation' in orientation_formation
        assert 'stage' in orientation_formation
        
        # Au moins orientation devrait être remplie
        assert orientation_formation['orientation']
    
    def test_competences_as_object(self):
        """Vérifie que competences est un objet avec sous-sections"""
        result = parse_bilan_from_paths(
            str(SAMPLE_DOCX_PATH),
            str(RULESET_PATH)
        )
        
        normalized = result['normalized']
        competences = normalized['competences']
        
        assert isinstance(competences, dict)
        assert 'sociales' in competences
        assert 'professionnelles' in competences
    
    def test_missing_required_sections_empty(self):
        """Vérifie qu'il n'y a plus de sections requises manquantes"""
        result = parse_bilan_from_paths(
            str(SAMPLE_DOCX_PATH),
            str(RULESET_PATH)
        )
        
        report = result['report']
        
        # Avec l'extraction inline, toutes les sections requises devraient être présentes
        assert len(report['missing_required_sections']) == 0, \
            f"Sections manquantes: {report['missing_required_sections']}"
    
    def test_required_coverage_ratio_100(self):
        """Vérifie que le required_coverage_ratio est à 100%"""
        result = parse_bilan_from_paths(
            str(SAMPLE_DOCX_PATH),
            str(RULESET_PATH)
        )
        
        report = result['report']
        
        assert 'required_coverage_ratio' in report
        assert report['required_coverage_ratio'] == 1.0, \
            f"Required coverage devrait être 1.0, got {report['required_coverage_ratio']}"
    
    def test_weighted_coverage_better_than_global(self):
        """Vérifie que weighted_coverage est meilleur que coverage_ratio"""
        result = parse_bilan_from_paths(
            str(SAMPLE_DOCX_PATH),
            str(RULESET_PATH)
        )
        
        report = result['report']
        
        assert 'weighted_coverage' in report
        assert 'coverage_ratio' in report
        
        # La couverture pondérée devrait être meilleure car les sections clés sont remplies
        assert report['weighted_coverage'] >= report['coverage_ratio'], \
            "weighted_coverage devrait être >= coverage_ratio"
        
        # Devrait être > 70% avec les sections clés remplies
        assert report['weighted_coverage'] > 0.7, \
            f"weighted_coverage trop faible: {report['weighted_coverage']}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
