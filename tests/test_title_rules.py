"""
Tests unitaires pour les règles regex de classification de titres (title_rules.py)

Tests pour PATCH "Priorité 2 — Règles regex famille tests"
"""
import pytest
from src.rhpro.title_rules import match_title_rule, compile_title_rules, TITLE_RULES


class TestFrancaisRules:
    """Tests pour les règles FRANÇAIS"""
    
    def test_francais_positionnement_simple(self):
        """'FRANCAIS POSITIONNEMENT' doit matcher"""
        normalized = "FRANCAIS POSITIONNEMENT"
        result = match_title_rule(normalized)
        assert result == 'tests'
    
    def test_francais_positionnement_variante(self):
        """'Français – positionnement de niveau' doit matcher (après normalisation)"""
        # Note: Le titre sera normalisé en amont par le mapper
        normalized = "FRANCAIS POSITIONNEMENT DE NIVEAU"
        result = match_title_rule(normalized)
        assert result == 'tests'
    
    def test_francais_test_positionnement_niveau(self):
        """'FRANCAIS TEST POSITIONNEMENT NIVEAU' doit matcher"""
        normalized = "FRANCAIS TEST POSITIONNEMENT NIVEAU"
        result = match_title_rule(normalized)
        assert result == 'tests'
    
    def test_francais_niveau_only(self):
        """'FRANCAIS NIVEAU' sans POSITIONNEMENT doit matcher aussi"""
        normalized = "FRANCAIS NIVEAU"
        result = match_title_rule(normalized)
        assert result == 'tests'


class TestCalculRules:
    """Tests pour les règles CALCUL"""
    
    def test_calcul_niveau_1(self):
        """'CALCUL NIVEAU 1' doit matcher"""
        normalized = "CALCUL NIVEAU 1"
        result = match_title_rule(normalized)
        assert result == 'tests'
    
    def test_calcul_niveau2(self):
        """'CALCUL NIVEAU2' (sans espace) doit matcher"""
        normalized = "CALCUL NIVEAU2"
        result = match_title_rule(normalized)
        assert result == 'tests'
    
    def test_calcul_niveau_sans_chiffre(self):
        """'CALCUL NIVEAU' sans chiffre NE doit PAS matcher"""
        normalized = "CALCUL NIVEAU"
        result = match_title_rule(normalized)
        assert result is None  # Pas de match attendu


class TestAnglaisAllemandRules:
    """Tests pour ANGLAIS et ALLEMAND"""
    
    def test_anglais_positionnement(self):
        """'ANGLAIS POSITIONNEMENT' doit matcher"""
        normalized = "ANGLAIS POSITIONNEMENT"
        result = match_title_rule(normalized)
        assert result == 'tests'
    
    def test_allemand_positionnement(self):
        """'ALLEMAND POSITIONNEMENT' doit matcher"""
        normalized = "ALLEMAND POSITIONNEMENT"
        result = match_title_rule(normalized)
        assert result == 'tests'


class TestAutresRules:
    """Tests pour TRI, SAISIE, DIMENSIONS"""
    
    def test_tri_classement(self):
        """'TRI CLASSEMENT' doit matcher"""
        normalized = "TRI CLASSEMENT"
        result = match_title_rule(normalized)
        assert result == 'tests'
    
    def test_saisie_commandes(self):
        """'SAISIE COMMANDES' doit matcher"""
        normalized = "SAISIE COMMANDES"
        result = match_title_rule(normalized)
        assert result == 'tests'
    
    def test_dimensions_volumes(self):
        """'DIMENSIONS VOLUMES' doit matcher"""
        normalized = "DIMENSIONS VOLUMES"
        result = match_title_rule(normalized)
        assert result == 'tests'
    
    def test_dimensions_mesures(self):
        """'DIMENSIONS MESURES' doit matcher"""
        normalized = "DIMENSIONS MESURES"
        result = match_title_rule(normalized)
        assert result == 'tests'


class TestNonRegression:
    """Tests de non-régression : les règles ne doivent pas être trop larges"""
    
    def test_formation_ne_match_pas(self):
        """Un titre 'FORMATION' ne doit pas matcher les règles tests"""
        normalized = "FORMATION"
        result = match_title_rule(normalized)
        assert result is None
    
    def test_situation_professionnelle_ne_match_pas(self):
        """Un titre 'SITUATION PROFESSIONNELLE' ne doit pas matcher"""
        normalized = "SITUATION PROFESSIONNELLE"
        result = match_title_rule(normalized)
        assert result is None
    
    def test_francais_sans_keywords_ne_match_pas(self):
        """'FRANCAIS' seul ne doit pas matcher (pas de POSITIONNEMENT/NIVEAU)"""
        normalized = "FRANCAIS"
        result = match_title_rule(normalized)
        assert result is None


class TestRulesCompilation:
    """Tests pour la compilation des règles"""
    
    def test_rules_compiled_once(self):
        """Les règles doivent être compilées une seule fois"""
        rules1 = compile_title_rules()
        rules2 = compile_title_rules()
        # Même objet en mémoire (cache global)
        assert rules1 is rules2
    
    def test_all_rules_compile(self):
        """Toutes les règles doivent compiler sans erreur"""
        rules = compile_title_rules()
        assert len(rules) == len(TITLE_RULES)
    
    def test_rules_have_correct_structure(self):
        """Chaque règle doit avoir pattern, section_id, description"""
        rules = compile_title_rules()
        for pattern, section_id, description in rules:
            assert hasattr(pattern, 'search')  # Compiled regex
            assert isinstance(section_id, str)
            assert isinstance(description, str)


class TestIntegrationAvecMapper:
    """Tests d'intégration conceptuelle (le mapper doit d'abord tester le mapping exact)"""
    
    def test_ordre_resolution_mapping_exact_prioritaire(self):
        """
        Si un titre est déjà dans section_title_map, le mapping exact
        doit avoir la priorité sur les règles regex.
        
        Note: Ce test vérifie la logique, l'implémentation est dans mapper.py
        """
        # Titre qui pourrait matcher une règle regex
        normalized = "FRANCAIS POSITIONNEMENT"
        
        # Si ce titre était dans section_title_map → exact match prioritaire
        # Si pas dans map → règle regex s'applique
        result = match_title_rule(normalized)
        assert result == 'tests'
        
        # L'ordre de résolution dans mapper.py doit être :
        # 1. exact/contains/regex (du ruleset)
        # 2. title_rules (fallback) <-- ce module
        # 3. unknown


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
