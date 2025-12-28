# Guide Utilisateur : Entraînement Dataset avec Merge Safe

Date : 28 décembre 2025

---

## 🎯 Nouveautés

### 1. Presets rapides (Mode Test / Mode Batch)

Plus besoin de choisir manuellement les paramètres ! Utilisez les boutons presets :

#### 🧪 Mode Test
- **Utilisation** : Tester la pipeline rapidement
- **Configuration** : 5 clients, profondeur 3, merge OFF
- **Durée** : ~30 secondes
- **Quand l'utiliser** : Valider que tout fonctionne avant un gros batch

#### 🚀 Mode Batch
- **Utilisation** : Analyser tous les clients (production)
- **Configuration** : Tous clients, profondeur 4, merge ON
- **Durée** : Variable selon nombre de clients
- **Quand l'utiliser** : Générer le training_state.json final

### 2. Aide contextuelle

Un expander "📖 Aide" explique chaque paramètre :
- **scan_depth** : Profondeur pour trouver les dossiers clients
- **limit** : 0 = tous, sinon N premiers (test rapide)
- **merge** : Fusionne avec training_state.json existant

### 3. Merge sécurisé

Le merge fonctionne maintenant de manière robuste :
- ✅ Ne plante jamais (même avec schémas incompatibles)
- ✅ Fusionne uniquement les patterns agrégés
- ✅ Garde les données du nouveau run (clients_used, metadata)
- ✅ Prend le meilleur de chaque run (max p90, max coverage)

---

## 📖 Mode d'emploi

### Scénario 1 : Première analyse (Mode Test)

1. Ouvrir Streamlit (`streamlit run streamlit_app.py`)
2. Aller dans l'onglet "📚 Entraîner Dataset"
3. Cliquer sur "🧪 Mode Test (5 clients)"
4. Sélectionner votre dataset racine
5. Cliquer sur "🚀 Lancer Entraînement"
6. Vérifier les résultats (stats, sections, warnings)

**Résultat** : `output/training/training_state.json` créé

### Scénario 2 : Analyse complète (Mode Batch)

1. Ouvrir Streamlit
2. Aller dans l'onglet "📚 Entraîner Dataset"
3. Cliquer sur "🚀 Mode Batch (tous)"
4. Sélectionner votre dataset racine
5. Cliquer sur "🚀 Lancer Entraînement"
6. Attendre la fin (peut prendre plusieurs minutes)
7. Consulter les artefacts générés

**Résultats** :
- `training_state.json` : État complet avec patterns
- `training_report.md` : Rapport lisible
- `training_warnings.json` : Warnings détectés

### Scénario 3 : Mise à jour incrémentale (Merge)

**Cas d'usage** : Vous avez déjà un training_state.json et voulez l'enrichir avec de nouveaux clients.

1. Ouvrir Streamlit
2. Aller dans l'onglet "📚 Entraîner Dataset"
3. Cliquer sur "🚀 Mode Batch (tous)" (merge=ON activé)
4. Sélectionner votre nouveau dataset
5. Vérifier que le dossier sortie contient déjà `training_state.json`
6. Cliquer sur "🚀 Lancer Entraînement"

**Résultat** : 
- `training_state.json` mis à jour avec :
  - Metadata du nouveau run (clients_used, timestamp)
  - Patterns fusionnés (max p90, max coverage)
  - Warnings combinés (union)
  - Historique des runs (traçabilité)

---

## ⚠️ Important à savoir

### Ce qui EST fusionné (merge=ON)
- ✅ `field_max_lines` : max par champ
- ✅ `section_stats.lines.p90` : max par section
- ✅ `section_stats.coverage_pct` : max par section
- ✅ `warnings` : union (pas de doublons)
- ✅ `history` : append (traçabilité)

### Ce qui N'EST PAS fusionné (merge=ON)
- ❌ `dataset.clients_used` : toujours celui du nouveau run
- ❌ `training_state_id` : toujours celui du nouveau run
- ❌ `created_at` : toujours celle du nouveau run
- ❌ `dataset.root_path` : toujours celui du nouveau run

**Pourquoi ?** Pour éviter toute fusion de données nominatives. Le merge ne concerne que les **patterns agrégés** (statistiques générales).

---

## 🛡️ Garanties de qualité

Le système vérifie automatiquement :
- ✅ `coverage_pct` toujours dans [0..100]
- ✅ `clients_with_section` ≤ `clients_used`
- ✅ Si section présente (coverage > 0), alors `p90 >= 1`
- ✅ Merge ne plante jamais (défensif)

Ces contraintes sont testées en continu (7 tests anti-régression).

---

## 🔧 Dépannage

### Le merge ne fonctionne pas
**Symptôme** : Erreur lors du merge  
**Solution** : Le nouveau code est défensif, il ne devrait jamais planter. Si ça arrive, vérifier les logs et partager l'erreur.

### Les presets ne s'appliquent pas
**Symptôme** : Les valeurs ne changent pas après clic  
**Solution** : Rafraîchir la page ou cliquer à nouveau (st.rerun() intégré).

### Merge trop lent
**Symptôme** : Le merge prend beaucoup de temps  
**Solution** : Normal si training_state.json est très gros (>10MB). Considérer archiver les anciens training_state.

### Coverage_pct > 100
**Symptôme** : Une section a un coverage > 100%  
**Solution** : Ne devrait plus arriver (fix V4.1). Si ça arrive, relancer l'analyse.

---

## 📊 Exemple concret

**Situation** :
- J'ai analysé BATCH_A (10 clients) → training_state_v1.json
- Je veux analyser BATCH_B (15 clients) et fusionner les patterns

**Étapes** :
1. Mode Batch (merge=ON)
2. Sélectionner BATCH_B
3. Lancer l'entraînement
4. Vérifier le résultat

**Résultat attendu** :
- `clients_used = 15` (nouveau batch)
- `field_max_lines` : max entre BATCH_A et BATCH_B
- `section_stats` : meilleurs p90 et coverage entre les deux
- `warnings` : union des warnings des deux batchs
- `history` : 2 entrées (BATCH_A + BATCH_B)

---

## ✅ Checklist avant production

- [ ] Tester avec Mode Test (5 clients) → OK
- [ ] Vérifier training_state.json généré → OK
- [ ] Vérifier training_report.md lisible → OK
- [ ] Tester Mode Batch (tous clients) → OK
- [ ] Tester merge (analyser 2x le même dataset) → OK
- [ ] Vérifier que coverage_pct ∈ [0..100] → OK
- [ ] Vérifier que merge ne plante pas → OK

Si toutes les cases sont cochées, vous pouvez utiliser en production ! 🚀

---

## 📞 Support

Si problème :
1. Vérifier les logs dans terminal Streamlit
2. Consulter `training_warnings.json`
3. Relancer avec Mode Test pour isoler le problème
4. Consulter la doc technique : [FIX_5_6_7_SUMMARY.md](FIX_5_6_7_SUMMARY.md)

---

**Version** : V4.1 (28 décembre 2025)  
**Status** : ✅ Production Ready
