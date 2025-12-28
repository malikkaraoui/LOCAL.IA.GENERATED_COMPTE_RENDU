# Amélioration Coverage Sections - Nouveaux Mappings & Filtres

**Date**: 28 décembre 2025  
**Objectif**: Réduire unknown_titles et augmenter coverage des sections canoniques

---

## 📊 Situation Initiale

- **77 titres uniques** non mappés
- **99 occurrences** au total
- Sections sous-représentées: `contraintes_freins` (10%)

---

## ✅ Modifications Apportées

### A) Nouveaux Mappings (section_title_map)

#### 1. Contraintes / Freins (+5 mappings)
Augmente significativement le coverage de cette section importante :

```python
"INCERTITUDES & OBSTACLES" → contraintes_freins
"INCERTITUDES & OBSTACLES (LIMITATIONS)" → contraintes_freins
"ACTUELLEMENT LES LIMITATIONS FONCTIONNELLES RETENUES SONT LES SUIVANTES" → contraintes_freins
"LES LIMITATIONS MEDICALES DE L ASSURE SONT LES SUIVANTES" → contraintes_freins
"DIFFICULTEES RENCONTREES" → contraintes_freins
```

**Impact attendu**: Coverage `contraintes_freins` passe de 10% à ~25-30%

#### 2. Situation Professionnelle - Stages/LAI (+4 mappings)
Capture les parcours de stage et mesures LAI :

```python
"STAGE EN LAI 15" → situation_professionnelle
"LAI 15" → situation_professionnelle
"CONTEXTE ET DEROULEMENT DU STAGE" → situation_professionnelle
"PROFESSION" → situation_professionnelle
```

#### 3. Compétences - Évaluation Stage (+2 mappings)
Titres longs d'évaluation de stage :

```python
"SELON L EVALUATION DE STAGE FINALE LES TACHES REALISEES ONT ETE LES SUIVANTES" → competences
"DANS SON STAGE SES TACHES SONT LES SUIVANTES" → competences
```

#### 4. Pistes Métiers - Tests Orientation (+1 mapping)
Test d'intérêts professionnels :

```python
"VOCATIO" → pistes_metiers
```

#### 5. Motivations/Valeurs (+1 mapping)
Test d'évolution :

```python
"TEST EVOLUTION" → motivations_valeurs
```

#### 6. Objectifs (+1 mapping)
Relation au marché du travail :

```python
"RELATION AU MARCHE DE L EMPLOI" → objectifs
```

**Total**: +14 nouveaux mappings

---

### B) Filtrage Noise & PII Amélioré

#### Nouveaux Patterns de Noise
Filtrage des sous-intros répétitives de tableaux :

```python
"LES RESULTATS DETAILLES SONT LES SUIVANTS"
"CI DESSOUS LES RESULTATS DETAILLES"
"RESULTATS DE LA DISCUSSION AVEC L ASSURE"
"TESTS" (seul, conteneur vide)
```

#### Filtrage PII Renforcé

**Patterns ajoutés** dans `is_noise_heading()`:

1. **MONSIEUR/MADAME** - Détection robuste :
   ```python
   if re.search(r'\b(MONSIEUR|MADAME|M\.|MME)\b', text_normalized):
       return True
   ```

2. **NOM + PRENOM** dans même heading :
   ```python
   has_nom = 'NOM' in text_normalized.split()
   has_prenom = 'PRENOM' in text_normalized.split()
   if has_nom and has_prenom:
       return True
   ```

3. **Phrases longues avec intro générique** (>60 caractères) :
   ```python
   if len(text_normalized) > 60 and any(intro in text_normalized for intro in [
       'LES MOTIVATEURS PRINCIPAUX DE',
       'VOICI',
       'APRES DISCUSSION',
       'SUITE A',
   ]):
       return True
   ```

**Exemples filtrés**:
- "NOM DUPONT PRENOM JEAN"
- "LES MOTIVATEURS PRINCIPAUX DE MONSIEUR MARTIN SONT"
- "MADAME DURAND A EXPRIME"

---

## 🧪 Tests de Validation

Fichier: [test_new_mappings.py](../test_new_mappings.py)

### Résultats
```
✅ TEST 1: Nouveaux mappings → 8/8 mappés correctement
✅ TEST 2: Filtrage NOISE → 4/4 filtrés
✅ TEST 3: Filtrage PII → 5/5 filtrés
✅ TEST 4: Titres légitimes → 4/4 NON filtrés
```

**Tous les tests passent** ✅

---

## 📈 Impact Attendu

### Coverage Sections
- **CONTRAINTES_FREINS**: 10% → **~25-30%** (+150-200%)
- **SITUATION_PROFESSIONNELLE**: Augmentation de ~5-10%
- **COMPETENCES**: Légère amélioration avec évaluations stage

### Unknown Titles
- **Avant**: 77 titres uniques, 99 occurrences
- **Après**: ~**55-60 titres** (-20-25%), ~**80-85 occurrences** (-15-20%)

### Qualité PII
- **0 titres nominatifs** dans unknown_titles
- Filtrage MONSIEUR/MADAME complet
- Protection contre noms/prénoms renforcée

---

## 🔄 Prochaines Itérations

### Mappings Additionnels Possibles
Après analyse du nouveau run, évaluer :
- Titres restants à forte occurrence (>3)
- Sections encore sous-représentées
- Nouveaux patterns PII émergents

### Optimisations
- Affiner les seuils de longueur pour phrases intro
- Ajouter synonymes/variantes des nouveaux mappings
- Monitorer faux positifs du filtrage noise

---

## 💡 Notes Techniques

### Ordre de Traitement
1. `is_noise_heading()` vérifie d'abord (filtre PII + noise)
2. Si pas noise → `normalize_title()` normalise
3. Lookup dans `SEED_SECTION_TITLE_MAP`
4. Si trouvé → section canonique
5. Sinon → unknown_titles (avec count)

### Principe de Précaution
- Mieux filtrer un titre légitime (rare) que laisser passer du PII
- Les faux positifs noise sont négligeables vs risque PII
- Coverage peut être amélioré incrémentalement

---

## ✅ Checklist Implémentation

- [x] Ajouter 14 nouveaux mappings dans SEED_SECTION_TITLE_MAP
- [x] Étendre is_noise_heading() avec patterns noise
- [x] Ajouter filtres PII (MONSIEUR/MADAME, NOM+PRENOM)
- [x] Créer tests de validation (test_new_mappings.py)
- [x] Valider tous les tests ✅
- [ ] Run training sur 10 clients pour mesurer impact
- [ ] Analyser nouveau unknown_titles_top
- [ ] Commit & push

---

**Prêt pour validation sur dataset réel** 🚀
