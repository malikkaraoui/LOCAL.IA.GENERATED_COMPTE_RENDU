# Résumé : Mise à jour des prompts LLM pour tous les champs

## 📅 Date
Janvier 2025

## 🎯 Objectif
Mise à jour complète des instructions envoyées au LLM pour chaque section du rapport avec des spécifications détaillées et précises.

## 📊 Bilan des modifications

### Statistiques
- **27 champs** au total (au lieu de 24)
- **12 champs narratifs** (au lieu de 11) → +1 nouveau champ
- **7 champs listes** (inchangé)
- **3 champs enum** (valeurs modifiées pour bureautique)
- **5 champs déterministes** (inchangés)

## 🆕 Nouveau champ ajouté

### RELATION_A_LA_CARRIERE (Narratif)
**But** : Décrire la relation de la personne à sa carrière/son projet professionnel.

**Attendu** :
- Rapport au travail : stabilité recherchée, envie de changement, rapport au statut
- Perception de son parcours : linéaire, éclaté, en construction, satisfait/insatisfait
- Niveau d'engagement dans le projet : actif, en réflexion, contraint, volontaire
- Rapport au temps : urgence, patience, projection court/moyen/long terme

**Contraintes** :
- Ne pas psychologiser
- Basé uniquement sur ce qui est dit ou observable dans les sources

**Position** : Après FORMATION, avant DISCUSSION_ASSURE

## 📝 Champs narratifs mis à jour (12 champs)

Tous les prompts ont été réécrits avec la structure :
- **But** : Objectif du champ
- **Attendu** : Ce qui doit être présent
- **Contraintes** : Règles strictes
- **Format** : Longueur et présentation conseillées

### Liste complète
1. **PROFESSION** : Situation pro actuelle (6-10 lignes)
2. **FORMATION** : Acquis académiques et certifs (6-12 lignes)
3. **RELATION_A_LA_CARRIERE** : ⭐ NOUVEAU - Relation à la carrière (6-10 lignes)
4. **DISCUSSION_ASSURE** : Motivations, freins, points d'appui (3 mini-paragraphes)
5. **COMPETENCES_SOCIALES** : Compétences sociales observées (6-10 lignes)
6. **COMPETENCES_PRO** : Compétences professionnelles clés (5-8 puces)
7. **OBSTACLES** : Obstacles identifiés (5-10 lignes)
8. **ORIENTATION** : Pistes cohérentes et crédibles (2-4 puces)
9. **STAGE** : Synthèse stage si présent (8-12 lignes)
10. **LETTRE_DE_MOTIVATION** : Synthèse lettre si présente (6-10 lignes)
11. **CV** : Synthèse CV si présent (10-15 lignes)
12. **CONCLUSION** : Conclusion et prochaines étapes (3 parties courtes)

## 📋 Champs listes mis à jour (7 champs)

Structure uniforme avec :
- **But** : Objectif du champ
- **Attendu** : Types d'éléments attendus
- **Exemples** : 2-3 exemples concrets
- **Contraintes** : Règles strictes
- **Format** : 3-6 puces courtes

### Liste complète
1. **RESSOURCES_MOTIVATIONNELLES** : Intérêts, motivations, valeurs
2. **RELATION_AU_MARCHE_DE_LEMPLOI** : Postures face au marché (orthographe corrigée)
3. **STRATEGIES_COMPORTEMENTALES** : Stratégies d'adaptation
4. **CONTEXTE_ORGANISATION_ET_ROLE_PRIVILEGIE** : Environnements privilégiés
5. **SECTEURS_PRIVILEGIES** : Secteurs d'activité (pas métiers)
6. **METIERS_PRIVILEGIES_ENVISAGEABLES** : Métiers précis (pas secteurs)
7. **FORMATIONS_HAUTES_ECOLES** : Formations supérieures envisagées

## 🔢 Champs enum modifiés (3 champs)

### Langues (CECRL - Inchangé)
- **FRANCAIS_POSITIONNEMENT_DE_NIVEAU** : A1, A2, B1, B2, C1, C2, Non évalué
- **ANGLAIS_POSITIONNEMENT_DE_NIVEAU** : A1, A2, B1, B2, C1, C2, Non évalué

### Bureautique (Valeurs spécifiques - MODIFIÉ) ⚠️
- **WORD_EXCEL_POWERPOINT_OUTLOOK_POSITIONNEMENT_DE_NIVEAU**
  - ❌ Anciennement : A1, A2, B1, B2, C1, C2, Non évalué (CECRL)
  - ✅ Maintenant : **Faible, Moyen, Bon, Très bon, Non évalué**

## 🎨 Améliorations apportées

### 1. Structure unifiée
Tous les prompts suivent maintenant une structure claire et cohérente :
- But explicite
- Attendus précis
- Exemples concrets pour les listes
- Contraintes strictes
- Format recommandé

### 2. Anti-hallucination renforcée
- Répétition systématique : "Ne pas inventer"
- Instructions claires : "Basé uniquement sur sources"
- Fallback défini : "Non renseigné" si absent

### 3. Formats précis
- Longueur en lignes (ex : "6-10 lignes")
- Nombre d'éléments (ex : "3-6 puces")
- Structure (ex : "2 paragraphes", "3 mini-paragraphes")

### 4. Exemples concrets
Pour tous les champs listes, ajout de 2-3 exemples concrets pour guider le LLM.

### 5. Séparation claire secteurs/métiers
- **SECTEURS_PRIVILEGIES** : Domaines d'activité (santé, industrie, logistique...)
- **METIERS_PRIVILEGIES_ENVISAGEABLES** : Métiers précis (agent administratif, aide-soignant...)

## 📁 Fichiers modifiés

### core/field_specs_v2.py
- **Lignes 18-19** : Ajout de `BUREAUTIQUE_LEVELS`
- **Lignes 42-182** : Réécriture complète de `_build_narrative_instructions()`
- **Lignes 184-346** : Réécriture complète de `_build_list_instructions()`
- **Lignes 421** : Ajout de RELATION_A_LA_CARRIERE dans la liste narrative
- **Lignes 473-511** : Séparation langues/bureautique avec valeurs spécifiques

## ✅ Validation

```bash
✅ Nombre de champs: 27
✅ Champs narratifs: 12 (dont 1 nouveau)
✅ Champs listes: 7
✅ Champs enum: 3 (avec valeurs bureautique modifiées)
✅ Champs déterministes: 5
✅ Import Python réussi sans erreurs
```

## 🚀 Impact attendu

1. **Qualité des rapports** : Prompts beaucoup plus détaillés et précis
2. **Cohérence** : Structure uniforme pour tous les champs
3. **Anti-hallucination** : Instructions répétées et claires
4. **Longueur contrôlée** : Formats précis (lignes, puces)
5. **Différenciation secteurs/métiers** : Plus de confusion possible

## 📚 Ordre des champs dans le rapport

### Bloc 1 : Informations personnelles (5 déterministes)
- MONSIEUR_OU_MADAME
- NAME
- SURNAME
- LIEU_ET_DATE
- NUMERO_AVS

### Bloc 2 : Valeurs contraintes (3 enum)
- FRANCAIS_POSITIONNEMENT_DE_NIVEAU
- ANGLAIS_POSITIONNEMENT_DE_NIVEAU
- WORD_EXCEL_POWERPOINT_OUTLOOK_POSITIONNEMENT_DE_NIVEAU

### Bloc 3 : Narratif bloc 1 (7 champs)
- PROFESSION
- FORMATION
- RELATION_A_LA_CARRIERE ⭐
- DISCUSSION_ASSURE
- COMPETENCES_SOCIALES
- COMPETENCES_PRO
- OBSTACLES

### Bloc 4 : Narratif bloc 2 (5 champs)
- ORIENTATION
- STAGE
- LETTRE_DE_MOTIVATION
- CV
- CONCLUSION

### Bloc 5 : Listes (7 champs)
- RESSOURCES_MOTIVATIONNELLES
- RELATION_AU_MARCHE_DE_LEMPLOI
- STRATEGIES_COMPORTEMENTALES
- CONTEXTE_ORGANISATION_ET_ROLE_PRIVILEGIE
- SECTEURS_PRIVILEGIES
- METIERS_PRIVILEGIES_ENVISAGEABLES
- FORMATIONS_HAUTES_ECOLES

## 🔄 Prochaines étapes

1. ✅ Mise à jour des prompts : **TERMINÉ**
2. ⏳ Tester la génération de rapports avec les nouveaux prompts
3. ⏳ Vérifier la qualité des sorties
4. ⏳ Ajuster si nécessaire selon les retours

## 📝 Notes importantes

- Le champ **RELATION_A_LA_CARRIERE** doit être positionné entre FORMATION et DISCUSSION_ASSURE
- Les valeurs bureautique ne sont **plus CECRL** mais des niveaux descriptifs
- Tous les prompts insistent sur "Ne pas inventer" et "Basé sur sources uniquement"
- Les formats sont **recommandés** (pas strictement imposés) pour guider le LLM
