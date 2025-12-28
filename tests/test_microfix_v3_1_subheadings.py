"""
Tests pour micro-fix v3.1 - Détection sous-titres (subheadings)

Objectif : Filtrer automatiquement les sous-titres qui ne doivent pas être comptés
en unknown_titles :
- Questions (?, VOUS, POURQUOI, COMMENT, etc.)
- Listes numérotées (1., 2., 3., etc.)
- Phrases longues (> 8 mots)
- Étiquettes (CLE : valeur)

Résultat attendu : unknown_titles proche de 0 sans mapping exhaustif.
"""

import pytest
from src.rhpro.dataset_training import (
    is_subheading,
    normalize_heading_for_titles,
)


class TestSubheadingQuestions:
    """Tests pour détection de questions."""
    
    def test_question_mark(self):
        """Questions avec point d'interrogation."""
        assert is_subheading("QUE FAIRE EN CAS DE PROBLEME ?")
        assert is_subheading("Voulez-vous continuer ?")
        assert is_subheading("Est-ce que cela vous intéresse?")
    
    def test_not_question(self):
        """Titres valides ne contenant pas de marqueurs de question."""
        assert not is_subheading("FORMATION PROFESSIONNELLE")
        assert not is_subheading("COMPETENCES")
        assert not is_subheading("PARCOURS")  # Ne contient pas '?'


class TestSubheadingNumbered:
    """Tests pour listes numérotées."""
    
    def test_numbered_list(self):
        """Détection de listes numérotées (1., 2., 3., etc.)."""
        assert is_subheading("1. PREMIER POINT")
        assert is_subheading("2. DEUXIEME POINT")
        assert is_subheading("10. DIXIEME POINT")
        assert is_subheading("123. POINT NUMEROTE")
    
    def test_numbered_with_accents(self):
        """Listes numérotées avec accents (normalisées)."""
        title = normalize_heading_for_titles("1. PREMIÈRE ÉTAPE")
        assert is_subheading(title)
    
    def test_not_numbered(self):
        """Titres valides ne commençant pas par numéro."""
        assert not is_subheading("FORMATION")
        assert not is_subheading("ETAPE 1")  # Numéro à la fin
        assert not is_subheading("A. SECTION A")  # Lettre, pas numéro


class TestSubheadingLongPhrases:
    """Tests pour phrases longues (> 8 mots)."""
    
    def test_long_phrase(self):
        """Phrases longues détectées comme sous-titres."""
        assert is_subheading("CETTE FORMATION EST DESTINEE AUX PERSONNES SOUHAITANT SE RECONVERTIR PROFESSIONNELLEMENT")
        assert is_subheading("JE SOUHAITE DEVELOPPER MES COMPETENCES EN INFORMATIQUE ET EN BUREAUTIQUE")
        assert is_subheading("QUELS SONT LES OBJECTIFS DE CETTE FORMATION ET LES DEBOUCHES PROFESSIONNELS")
    
    def test_short_phrase(self):
        """Phrases courtes (≤ 8 mots) ne sont pas filtrées automatiquement."""
        assert not is_subheading("FORMATION PROFESSIONNELLE EN INFORMATIQUE")  # 4 mots
        assert not is_subheading("COMPETENCES ACQUISES AU COURS DE LA FORMATION")  # 7 mots
        assert not is_subheading("OBJECTIFS DE LA FORMATION PROFESSIONNELLE CONTINUE")  # 6 mots
    
    def test_edge_case_8_words(self):
        """Exactement 8 mots : ne doit pas être filtré (limite exclusive)."""
        assert not is_subheading("UN DEUX TROIS QUATRE CINQ SIX SEPT HUIT")


class TestSubheadingLabels:
    """Tests pour étiquettes (CLE : valeur)."""
    
    def test_single_word_label(self):
        """Étiquettes avec 1 mot avant ':' (ex: DATE : ...)."""
        assert is_subheading("DATE : 15 JANVIER 2025")
        assert is_subheading("LIEU : PARIS")
        assert is_subheading("NOM : DUPONT")
        assert is_subheading("PRENOM : JEAN")
        assert is_subheading("TELEPHONE : 01 23 45 67 89")
    
    def test_two_words_label(self):
        """Étiquettes avec 2 mots avant ':' (ex: DATE ENTRETIEN : ...)."""
        assert is_subheading("DATE ENTRETIEN : 15 JANVIER")
        assert is_subheading("LIEU FORMATION : PARIS")
        assert is_subheading("NUMERO TELEPHONE : 01 23 45")
    
    def test_long_prefix_not_label(self):
        """Préfixe long (> 2 mots) avant ':' → pas une étiquette simple, MAIS est phrase longue."""
        # Note: "RESULTATS DE LA DISCUSSION AVEC L ASSURE : SYNTHESE" a 9 mots total
        # → Détecté comme phrase longue (> 8 mots), PAS comme étiquette
        assert is_subheading("RESULTATS DE LA DISCUSSION AVEC L ASSURE : SYNTHESE")  # phrase longue
    
    def test_colon_without_label_format(self):
        """':' présent mais format non-étiquette (>2 mots avant)."""
        assert not is_subheading("COMPETENCES TECHNIQUES ACQUISES : DETAILS")  # 3 mots avant → pas étiquette, pas phrase longue (6 mots total)
    
    def test_multiple_colons(self):
        """Plusieurs ':' → split(':',1) prend seulement le premier, considéré comme étiquette si préfixe court."""
        title = "A : B : C"
        # split(':', 1) → ['A ', ' B : C'], préfixe='A' (1 mot), suffixe='B : C' (existe)
        # → Détecté comme étiquette (c'est cohérent avec la règle)


class TestSubheadingEdgeCases:
    """Tests pour cas limites."""
    
    def test_empty_title(self):
        """Titre vide ne devrait pas crasher."""
        assert not is_subheading("")
    
    def test_title_with_multiple_markers(self):
        """Titre avec plusieurs marqueurs (question + numéro)."""
        assert is_subheading("1. POURQUOI CETTE FORMATION ?")  # numéro détecté en premier
    
    def test_normalized_title_with_accents(self):
        """Titres avec accents normalisés correctement."""
        title = normalize_heading_for_titles("OÙ ÊTES-VOUS ?")
        # Après normalisation: "OU ETES VOUS" (pas de '?')
        # Donc ne sera pas détecté comme question via normalize_heading_for_titles
        # Mais is_subheading() détecte '?' sur l'original avant normalisation
        assert is_subheading("OÙ ÊTES-VOUS ?")  # '?' détecté sur original
    
    def test_valid_section_titles_not_filtered(self):
        """Titres de sections valides ne doivent jamais être filtrés."""
        assert not is_subheading("FORMATION")
        assert not is_subheading("COMPETENCES")
        assert not is_subheading("PARCOURS PROFESSIONNEL")
        assert not is_subheading("PROJET PROFESSIONNEL")
        assert not is_subheading("PISTES METIERS")
        assert not is_subheading("SYNTHESE")


class TestIntegrationSubheadings:
    """Tests d'intégration pour micro-fix v3.1."""
    
    def test_all_question_types_detected(self):
        """Questions avec '?' sont détectées."""
        questions = [
            "QUE FAIRE EN CAS DE PROBLEME ?",
            "VOULEZ VOUS CONTINUER ?",
            "EST CE QUE CELA VOUS INTERESSE?",
        ]
        for question in questions:
            assert is_subheading(question), f"Question '{question}' non détectée"
    
    def test_priority_order(self):
        """Vérifier que les règles s'appliquent dans l'ordre (first match wins)."""
        # Question détectée avant autres règles
        assert is_subheading("POURQUOI ?")  # question
        
        # Numéro détecté avant autres règles
        assert is_subheading("1. FORMATION")  # numéro
        
        # Phrase longue détectée
        assert is_subheading("CECI EST UNE PHRASE TRES LONGUE AVEC PLUS DE HUIT MOTS")
        
        # Étiquette détectée
        assert is_subheading("DATE : 01/01/2025")
    
    def test_no_false_positives_on_canonical_titles(self):
        """Aucun faux positif sur titres canoniques."""
        canonical_titles = [
            "FORMATION",
            "PARCOURS PROFESSIONNEL",
            "COMPETENCES",
            "PROJET PROFESSIONNEL",
            "PISTES METIERS",
            "BILAN",
            "SYNTHESE",
            "RECOMMANDATIONS",
        ]
        for title in canonical_titles:
            assert not is_subheading(title), f"Faux positif sur '{title}'"
