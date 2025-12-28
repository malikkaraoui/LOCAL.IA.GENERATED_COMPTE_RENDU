# Guide Rapide : Support .msg (Emails Outlook)

**Date** : 28 décembre 2025

---

## 🎯 C'est quoi ?

Les fichiers .msg (emails Outlook) sont maintenant indexés dans la pipeline RAG.

**Résultat** : Tu peux rechercher du contenu d'email dans les dossiers clients !

---

## ⚡ Installation (1 commande)

```bash
pip install extract-msg>=0.48.0
```

C'est tout ! Le reste est déjà codé. ✅

---

## 🔍 Ça marche comment ?

### Avant (sans support .msg)

```
Dossier client/
├── CV.pdf          ✅ Indexé
├── Email.msg       ❌ Ignoré
└── Rapport.docx    ✅ Indexé
```

**Problème** : Les emails ne sont pas recherchables.

### Après (avec support .msg)

```
Dossier client/
├── CV.pdf          ✅ Indexé
├── Email.msg       ✅ Indexé (subject + body + pièces jointes)
└── Rapport.docx    ✅ Indexé
```

**Résultat** : Tout est recherchable ! 🎉

---

## 📧 Qu'est-ce qui est extrait ?

D'un email .msg, on extrait :

```
[EMAIL_MSG]
Subject: Candidature Développeur
From: john@example.com
To: rh@company.com
Date: 2025-12-28 10:30
Attachments: CV.pdf; Lettre.docx
---
Body:
Bonjour, voici ma candidature...
```

**Bonus** : Les pièces jointes (PDF/DOCX/DOC/TXT) sont **automatiquement extraites et indexées** !

---

## 🎓 Dans l'interface Training

### Sans extract-msg

```
⚠️ MSG_EXTRACTOR_MISSING
Des fichiers .msg sont présents mais non indexés
→ pip install extract-msg>=0.48.0
```

### Avec extract-msg

```
✅ 15 sources indexées
   - 5 PDF
   - 3 DOCX
   - 4 MSG ← Nouveaux !
   - 3 TXT
```

---

## 🔍 Exemples de recherche

| Recherche | Trouve dans .msg |
|-----------|------------------|
| "candidature" | Subject de l'email |
| "CV.pdf" | Nom de la pièce jointe |
| "john@example.com" | Expéditeur |
| "contrat de travail" | Texte du body |

---

## ⚠️ Important

### ✅ Ce qui est stocké (training_state.json)

- Nombre de .msg trouvés : **5**
- Extensions présentes : **[".pdf", ".msg", ".docx"]**

### ❌ Ce qui N'EST PAS stocké

- ❌ Contenu des emails (body)
- ❌ From/To/Subject
- ❌ Aucune donnée nominative

**Pourquoi ?** Pour respecter la contrainte "pas de données nominatives".

---

## 🧪 Tester

### Test rapide

```bash
python demo_msg_support.py
```

### Tests complets

```bash
pytest tests/test_msg_extraction.py -v
```

---

## 🔧 Si ça marche pas

### Problème : "MSG_EXTRACTOR_MISSING"

**Solution** :
```bash
pip install extract-msg>=0.48.0
```

### Problème : ".msg pas indexés"

**Diagnostic** :
```python
python -c "from core.extractors.msg_extractor import MSG_SUPPORT_AVAILABLE; print(MSG_SUPPORT_AVAILABLE)"
```

Doit afficher : `True`

### Problème : "Erreur extraction .msg"

**Causes possibles** :
- Fichier .msg corrompu
- Format non supporté
- Permissions fichier

**Solution** : Vérifier logs dans terminal

---

## 📊 Performance

| Fichier | Temps extraction |
|---------|------------------|
| .msg seul | ~50-200ms |
| .msg + 2 PDF | ~150-400ms |

**Limites** :
- Body email limité à 200k caractères (éviter emails énormes)
- Pièces jointes : PDF/DOCX/DOC/TXT uniquement (pas d'images)

---

## ✅ Checklist avant utilisation

- [ ] `pip install extract-msg` exécuté
- [ ] `python demo_msg_support.py` OK
- [ ] Tests passent : `pytest tests/test_msg_extraction.py`
- [ ] Training UI ne montre plus warning `MSG_EXTRACTOR_MISSING`

Si toutes les cases sont cochées : **PRÊT ! 🚀**

---

## 📞 Si problème

1. Vérifier logs dans terminal
2. Tester avec `demo_msg_support.py`
3. Consulter doc complète : [MSG_SUPPORT_COMPLETE.md](MSG_SUPPORT_COMPLETE.md)

---

**TL;DR** : `pip install extract-msg` + c'est parti ! 🎉
