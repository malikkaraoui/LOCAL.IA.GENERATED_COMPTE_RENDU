# Support Fichiers .msg - Configuration OFF par Défaut

## 📋 Résumé de la mise à jour

**Objectif**: Les fichiers Outlook `.msg` doivent être comptés dans les statistiques mais **NON indexés par défaut** pour éviter les fuites PII (Personally Identifiable Information).

**Date**: Mise à jour du comportement par défaut `index_msg=False`

---

## ✅ Comportement Implémenté

### Par Défaut (index_msg=False)
- ✅ Les fichiers `.msg` sont **détectés** et **comptés**
- ✅ Les fichiers `.msg` ne sont **PAS inclus** dans `rag_sources` 
- ✅ Un warning structuré `EXT_NOT_INDEXED` est généré
- ✅ `stats["msg_files_count"]` indique le nombre de `.msg` détectés
- ✅ Protection PII activée par défaut

### Avec index_msg=True (opt-in explicite)
- ✅ Les fichiers `.msg` sont inclus dans `rag_sources`
- ✅ Les fichiers `.msg` apparaissent dans `stats["extensions"]`
- ✅ Aucun warning `EXT_NOT_INDEXED` généré
- ⚠️ **L'utilisateur est responsable de la validation PII**

---

## 🎯 Interface Utilisateur

### Onglet Entraînement (Training)
```python
# Checkbox ajoutée dans pages_streamlit/training_and_test.py
st.markdown("#### 📧 Fichiers Outlook (.msg)")
index_msg = st.checkbox(
    "Indexer fichiers .msg dans le RAG",
    value=False,  # OFF par défaut
    help="OFF par défaut pour éviter PII. Activer uniquement si validation PII effectuée."
)
```

**Affichage selon l'état:**
- 🔲 Non coché: `ℹ️ Les fichiers .msg seront détectés et comptés dans les stats mais NON indexés (recommandé par défaut)`
- ☑️ Coché: `⚠️ Mode indexation .msg activé. Vérifiez que les emails ne contiennent pas de données sensibles (PII).`

### Onglet Test (Single Client)
```python
# Même checkbox avec clé distincte
index_msg_test = st.checkbox(
    "Indexer fichiers .msg dans le RAG",
    value=False,
    key="index_msg_test"
)
```

### Affichage des Warnings
Les warnings `.msg` sont affichés de manière distinctive:
```python
if warning.get("code") == "EXT_NOT_INDEXED" and warning.get("ext") == ".msg":
    st.info(f"📧 {warning['count']} fichiers .msg détectés mais NON indexés")
```

---

## 🔧 Modifications Techniques

### 1. `src/rhpro/client_scanner.py`
```python
def scan_client_folder(
    client_folder_path: str,
    index_msg: bool = False  # ✅ Changé de True à False
) -> Dict[str, Any]:
```

**Warning structuré généré:**
```python
if not index_msg and msg_files_count > 0:
    warnings.append({
        "code": "EXT_NOT_INDEXED",
        "ext": ".msg",
        "count": msg_files_count,
        "message": f".msg détectés mais non indexés par défaut"
    })
```

### 2. `src/rhpro/dataset_training.py`
```python
def analyze_dataset(
    dataset_root: str,
    out_dir: str = "output/training",
    scan_depth: int = 3,
    limit: Optional[int] = None,
    index_msg: bool = False  # ✅ Nouveau paramètre
) -> DatasetAnalysisResult:
```

**Propagation du paramètre:**
```python
scan_result = scan_client_folder(
    client_folder_path,
    index_msg=index_msg  # ✅ Transmission
)
```

### 3. `pages_streamlit/training_and_test.py`
- ✅ Checkbox ajoutée dans l'onglet Training (ligne ~185)
- ✅ Checkbox ajoutée dans l'onglet Test (ligne ~550)
- ✅ Paramètre `index_msg` passé à `analyze_dataset()`
- ✅ Paramètre `index_msg_test` passé à `scan_client_folder()`
- ✅ Affichage différencié pour warnings `.msg`

---

## 🧪 Validation

### Test Automatisé
Fichier: `test_msg_default_off.py`

**Résultats:**
```
TEST 1: Scan SANS index_msg (défaut)
✅ .msg comptés: 2
✅ .msg NON indexés dans rag_sources: 0
✅ Warning présent: EXT_NOT_INDEXED - .msg - count=2

TEST 2: Scan AVEC index_msg=True
✅ .msg indexés dans rag_sources: 2
✅ .msg présents dans stats.extensions: 2
✅ Aucun warning EXT_NOT_INDEXED
```

### Test Manuel sur Client Réel
```bash
# Dans Streamlit > Training > décocher "Indexer .msg"
# Résultat attendu:
# - Stats affichent .msg détectés
# - Warning: "X fichiers .msg détectés mais NON indexés"
# - rag_sources ne contient pas de .msg
```

---

## 📊 Structure du Warning

### Format Structuré (Dict)
```python
{
    "code": "EXT_NOT_INDEXED",
    "ext": ".msg",
    "count": 5,  # nombre de .msg détectés
    "message": ".msg détectés mais non indexés par défaut (activer 'Indexer .msg' pour les inclure)"
}
```

### Avantages
- ✅ Facilite le parsing programmatique
- ✅ Permet un affichage différencié dans l'UI
- ✅ Inclut le count pour visibilité immédiate
- ✅ Message explicite pour l'utilisateur

---

## 🔒 Sécurité PII

### Pourquoi OFF par Défaut?
1. **Emails = PII sensibles**: Noms, adresses, numéros de téléphone, etc.
2. **Conformité RGPD**: Éviter indexation accidentelle de données personnelles
3. **Principe de précaution**: Opt-in explicite requis
4. **Responsabilité utilisateur**: Doit valider que les .msg sont anonymisés

### Messages d'Avertissement
- Interface: Warning rouge si checkbox activée
- Logs: Indication claire de l'état `index_msg`
- Documentation: Recommandation explicite OFF par défaut

---

## 📝 Documentation Associée

### Fichiers à Mettre à Jour
- ✅ `docs/MSG_SUPPORT.md` - Mettre à jour avec `index_msg=False` par défaut
- ✅ `README.md` - Ajouter note sur comportement par défaut
- ⚠️ `test_msg_support.py` - Adapter les tests au nouveau comportement
- ⚠️ Tests existants utilisant `index_msg=True` - Ajouter commentaires explicites

### Guide d'Utilisation
```markdown
## Comment activer l'indexation .msg?

1. Ouvrir Streamlit > Training
2. Cocher "Indexer fichiers .msg dans le RAG"
3. ⚠️ IMPORTANT: Valider que les .msg ne contiennent pas de PII
4. Lancer l'entraînement
5. Vérifier dans les stats que .msg apparaissent dans extensions
```

---

## 🚀 Prochaines Étapes

### Priorité Haute
- [x] Changer défaut `index_msg=False`
- [x] Ajouter checkbox UI Training
- [x] Ajouter checkbox UI Test
- [x] Warning structuré
- [x] Tests validation comportement

### Priorité Moyenne
- [ ] Mettre à jour `docs/MSG_SUPPORT.md`
- [ ] Adapter `test_msg_support.py` au nouveau défaut
- [ ] Ajouter tests pour warnings dans `tests/test_correctifs_a_b.py`

### Priorité Basse
- [ ] Analytics: tracker combien d'utilisateurs activent .msg
- [ ] Option configuration globale dans `config/settings.yaml`
- [ ] Scan détaillé PII avant indexation (futur)

---

## 💡 Notes Techniques

### Comptage .msg Sans Indexation
```python
# Dans scan_client_folder():
if not index_msg:
    all_msg = find_rag_sources(client_folder, index_msg=True)
    msg_files_count = sum(1 for s in all_msg if s["extension"] == ".msg")
```

**Coût**: Double scan si `.msg` présents ET non indexés
**Optimisation future**: Cache des paths `.msg` lors du premier scan

### Compatibilité Ascendante
- ✅ Ancien code appelant sans `index_msg` → Comportement OFF par défaut
- ✅ Code existant avec `index_msg=True` → Continue de fonctionner
- ✅ Warnings: formats ancien (string) et nouveau (dict) supportés

---

## 📞 Contact & Support

Pour questions ou problèmes:
1. Vérifier les logs: `output/training/training_report.md`
2. Checker les warnings dans l'interface
3. Valider `stats["msg_files_count"]` dans résultats

**Comportement attendu**: OFF par défaut, opt-in explicite requis pour indexation .msg.
