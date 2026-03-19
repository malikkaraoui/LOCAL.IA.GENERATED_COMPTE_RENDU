# Configuration des regles de redaction LLM

> Document de travail a valider avec RH PRO.
> Chaque choix impacte directement la qualite et la coherence des rapports generes.
> Une fois valide, chaque regle est injectee automatiquement dans le moteur — aucune intervention manuelle.

---

## 1. Ton et registre

Le ton definit l'impression generale que donne le rapport au lecteur (employeur, AI, assureur).

| Option | Exemple | Usage type |
|--------|---------|------------|
| **Factuel neutre** | "M. X a occupe le poste de magasinier pendant 8 ans." | Rapport administratif, PV |
| **Professionnel valorisant** | "Le parcours de M. X temoigne d'une solide experience dans la logistique." | Bilan de competences |
| **Administratif strict** | "L'assure exerce la fonction de magasinier." | Document assurance/AI |

**Choix actuel :** Non defini (le LLM choisit seul).

**Choix RH PRO :** _________________________________

> Le ton peut etre different selon la section. Par exemple : factuel pour PROFESSION, valorisant pour ORIENTATION.

---

## 2. Personne grammaticale

Comment parle-t-on de la personne dans le rapport ?

| Option | Exemple |
|--------|---------|
| **3e personne nommee** | "Mme Chanut a suivi une formation en secretariat." |
| **3e personne generique** | "L'assuree a suivi une formation en secretariat." |
| **Impersonnel** | "Le parcours comprend une formation en secretariat." |
| **1re personne** | "J'ai suivi une formation en secretariat." |

**Choix RH PRO :** _________________________________

> Question complementaire : faut-il genrer systematiquement (M. / Mme) ou rester neutre ?

---

## 3. Style de redaction par section

Chaque section peut avoir son propre style. Tirets pour les listes factuelles, paragraphes fluides pour les syntheses.

| Section | Tirets (- item) | Paragraphes fluides | Mix (intro + tirets) |
|---------|:-:|:-:|:-:|
| PROFESSION | ☐ | ☐ | ☐ |
| FORMATION | ☐ | ☐ | ☐ |
| INCERTITUDE ET OBSTACLE | ☐ | ☐ | ☐ |
| ORIENTATION | ☐ | ☐ | ☐ |
| FORMATION DURANT MESURE | ☐ | ☐ | ☐ |
| STAGE | ☐ | ☐ | ☐ |
| CONCLUSION | ☐ | ☐ | ☐ |

**Choix actuel :** Le LLM decide seul — resultat incoherent d'une section a l'autre.

**Impact :** Un choix clair rend tous les rapports visuellement homogenes.

---

## 4. Longueur par section

Fourchette precise de longueur pour chaque section. Le LLM respecte mieux une fourchette qu'un maximum seul.

| Section | Min lignes | Max lignes | Ou en nombre de mots |
|---------|:----------:|:----------:|:--------------------:|
| PROFESSION | 15 | 30 | ______ mots |
| FORMATION | 6 | 15 | ______ mots |
| INCERTITUDE ET OBSTACLE | 5 | 15 | ______ mots |
| ORIENTATION | 15 | 20 | ______ mots |
| FORMATION DURANT MESURE | 2 | 10 | ______ mots |
| STAGE | 8 | 15 | ______ mots |
| CONCLUSION | 3 | 5 | ______ mots |

> Les valeurs ci-dessus sont les reglages actuels. A ajuster si necessaire.

---

## 5. Lexique et glossaire

### 5a. Termes obligatoires

Mots que le LLM doit utiliser. Garantit un vocabulaire professionnel RH PRO.

| A utiliser | A la place de |
|-----------|---------------|
| assure(e) | client, patient, personne, individu |
| mesure | programme, dispositif |
| _________________ | _________________ |
| _________________ | _________________ |
| _________________ | _________________ |
| _________________ | _________________ |

### 5b. Termes interdits

Mots que le LLM ne doit jamais utiliser dans un rapport.

| Terme interdit | Raison | Remplacement |
|---------------|--------|--------------|
| patient | Contexte RH, pas medical | assure(e) |
| handicape | Formulation non appropriee | limitation fonctionnelle |
| probleme | Trop negatif | difficulte, enjeu |
| malheureusement | Jugement de valeur | (supprimer) |
| _________________ | _________________ | _________________ |
| _________________ | _________________ | _________________ |
| _________________ | _________________ | _________________ |

### 5c. Sigles et abreviations

| Sigle | Developper au 1er usage ? | Format souhaite |
|-------|:-------------------------:|-----------------|
| CFC | ☐ oui  ☐ non | CFC (Certificat Federal de Capacite) |
| AFP | ☐ oui  ☐ non | _________________ |
| LAI | ☐ oui  ☐ non | _________________ |
| OAI | ☐ oui  ☐ non | _________________ |
| CECRL | ☐ oui  ☐ non | _________________ |
| _________________ | | _________________ |

> **Impact :** Le lexique est le levier #1 pour la qualite percue du rapport. Un vocabulaire coherent donne immediatement un aspect professionnel.

---

## 6. Gestion du manque d'information

Que fait le LLM quand une information attendue n'est pas dans les sources ?

| Option | Exemple | Risque |
|--------|---------|--------|
| **Mentionner explicitement** | "Cette information n'est pas disponible dans les documents fournis." | Aucun |
| **Formule standard** | "Non renseigne a ce jour." | Aucun |
| **Omettre silencieusement** | Ne rien ecrire, passer au point suivant | Peut sembler incomplet |
| **Deduire prudemment** | "Les elements disponibles suggerent que..." | Risque d'interpretation |
| **Inventer** | Generer du contenu plausible | **Interdit** (hallucination) |

**Choix actuel :** Le LLM ecrit VIDE si rien n'est trouve, ou tente de deduire sans cadre.

**Choix RH PRO :** _________________________________

> **Impact :** C'est le levier anti-hallucination principal. Une regle claire elimine les inventions.

---

## 7. Structure interne des sections

Pour chaque section, dans quel ordre presenter les informations ?

### Exemples de choix possibles

| Section | Ordre chronologique | Ordre thematique | Par priorite |
|---------|:---:|:---:|:---:|
| PROFESSION | ☐ ancien → recent | ☐ par type | ☐ |
| FORMATION | ☐ ancien → recent | ☐ diplomes/certifs/tests | ☐ |
| ORIENTATION | ☐ | ☐ | ☐ principale → secondaires |
| CONCLUSION | ☐ | ☐ | ☐ bilan → perspectives |

### Structure detaillee souhaitee

Decrire l'enchainement attendu pour chaque section :

**PROFESSION :**
```
(ex: "Statut actuel → parcours chronologique → missions cles → raison de l'arret → competences transferables")
```

**FORMATION :**
```
(ex: "Diplomes du plus ancien au plus recent → certifications → tests de positionnement")
```

**INCERTITUDE ET OBSTACLE :**
```
_________________________________
```

**ORIENTATION :**
```
(ex: "Piste principale justifiee → piste secondaire → pistes ecartees et pourquoi")
```

**FORMATION DURANT MESURE :**
```
_________________________________
```

**STAGE :**
```
(ex: "Lieu et poste → deroulement → evaluation → lien avec l'orientation")
```

**CONCLUSION :**
```
(ex: "Bilan stage → validation/invalidation cible → respect limitations → prochaines etapes")
```

---

## 8. Anti-patterns et phrases interdites

Phrases ou formulations que le LLM ne doit jamais produire. Cocher celles a interdire.

### 8a. Phrases generiques (remplissage sans valeur)

- ☐ "Ce parcours riche et varie..."
- ☐ "Fort de son experience..."
- ☐ "Dans un souci de..."
- ☐ "Il est important de noter que..."
- ☐ "Il convient de souligner que..."
- ☐ Autre : _________________________________

### 8b. Formules de politesse

- ☐ "N'hesitez pas a..."
- ☐ "Nous restons a disposition..."
- ☐ "Cordialement"
- ☐ Autre : _________________________________

### 8c. Introductions meta

- ☐ "Voici la section FORMATION :"
- ☐ "En resume :"
- ☐ "Comme demande, voici..."
- ☐ "Sur la base des documents fournis..."
- ☐ Autre : _________________________________

### 8d. Jugements de valeur

- ☐ "Excellent parcours"
- ☐ "Brillante carriere"
- ☐ "Malheureusement"
- ☐ "Remarquable"
- ☐ "Impressionnant"
- ☐ Autre : _________________________________

> Chaque case cochee sera injectee automatiquement dans les regles du LLM.

---

## 9. Formatage typographique

Conventions d'ecriture pour l'homogeneite visuelle des rapports.

| Element | Option A | Option B | Option C | Choix |
|---------|---------|---------|---------|:-----:|
| **Dates** | 09.04.2024 | 9 avril 2024 | avril 2024 | _____ |
| **Noms propres** | CHANUT | Chanut | chanut | _____ |
| **Civilite** | M. / Mme | Monsieur / Madame | (rien) | _____ |
| **Separateur de liste** | virgule (,) | point-virgule (;) | tiret (-) | _____ |
| **Pourcentages** | 85% | 85 % | (ecrire en lettres) | _____ |

---

## 10. Connecteurs et transitions

Mots de liaison entre les phrases et les idees.

### Connecteurs autorises (style naturel)

- Par ailleurs
- Concernant
- En ce qui concerne
- De plus
- Egalement
- Autres : _________________________________

### Connecteurs interdits (style artificiel/litteraire)

- ☐ Neanmoins
- ☐ Toutefois
- ☐ Cependant
- ☐ Force est de constater
- ☐ Il convient de souligner
- ☐ En definitive
- ☐ Autres : _________________________________

> **Impact :** Les petits modeles LLM abusent de "Cependant" et "Neanmoins". Interdire ces mots force un style plus naturel et direct.

---

## 11. Exemples de reference (few-shot)

Fournir un exemple de "bonne reponse" pour chaque section est le levier **le plus puissant**.
Le modele imite le style, la longueur et le ton de l'exemple fourni.

> Pour chaque section, coller un extrait de rapport valide (anonymise) que vous considerez comme reference.

### PROFESSION — Exemple de reference
```
(coller ici un exemple de section PROFESSION validee par RH PRO)
```

### FORMATION — Exemple de reference
```
(coller ici un exemple de section FORMATION validee par RH PRO)
```

### INCERTITUDE ET OBSTACLE — Exemple de reference
```
(coller ici un exemple)
```

### ORIENTATION — Exemple de reference
```
(coller ici un exemple)
```

### FORMATION DURANT MESURE — Exemple de reference
```
(coller ici un exemple)
```

### STAGE — Exemple de reference
```
(coller ici un exemple)
```

### CONCLUSION — Exemple de reference
```
(coller ici un exemple)
```

> Un exemple de 5 lignes vaut mieux que 20 lignes d'instructions. C'est le moyen le plus efficace d'obtenir le style exact souhaite.

---

## 12. Coherence inter-sections

Regles de coherence entre les differentes sections du rapport.

| Regle | Activer ? |
|-------|:---------:|
| La CONCLUSION doit reprendre les elements cles de STAGE et ORIENTATION | ☐ oui  ☐ non |
| Ne pas repeter une information deja mentionnee dans une section precedente | ☐ oui  ☐ non |
| ORIENTATION doit etre coherente avec INCERTITUDE ET OBSTACLE | ☐ oui  ☐ non |
| Autoriser les references croisees ("Comme mentionne dans la section...") | ☐ oui  ☐ non |

---

## Resume : impact par levier

| # | Levier | Impact qualite | Effort config |
|:-:|--------|:--------------:|:-------------:|
| 1 | **Lexique / glossaire** | ★★★ | Moyen |
| 2 | **Gestion du manque d'info** | ★★★ | Faible |
| 3 | **Exemples de reference** | ★★★ | Fort (besoin d'exemples reels) |
| 4 | **Style par section** | ★★☆ | Faible |
| 5 | **Structure interne** | ★★☆ | Moyen |
| 6 | **Anti-patterns** | ★★☆ | Faible |
| 7 | **Ton / registre** | ★☆☆ | Faible |
| 8 | **Personne grammaticale** | ★☆☆ | Faible |
| 9 | **Longueur precise** | ★☆☆ | Faible |
| 10 | **Formatage typo** | ★☆☆ | Faible |
| 11 | **Connecteurs** | ★☆☆ | Faible |
| 12 | **Coherence inter-sections** | ★★☆ | Deja en place |

---

## Prochaines etapes

1. **RH PRO remplit ce document** — cases a cocher, choix, exemples
2. **Integration dans le moteur** — chaque regle est injectee automatiquement dans les prompts LLM
3. **Test sur 2-3 dossiers** — validation du resultat avec le nouveau cadrage
4. **Ajustements** — iteration sur les choix si necessaire
5. **Deploiement** — application sur tous les types de rapports

> Aucune intervention manuelle apres configuration. Le systeme applique les regles a chaque generation.
