# Instructions Copilot — Logo V3 “béton” (contain + align left, zéro crop)

## Objectif
Implémenter un mode unique “safe” pour les logos :

- **ratio toujours conservé**
- **zéro découpe / zéro crop** (jamais de “cover”)
- logo **collé à gauche** dans la box (avec un petit padding) et **centré verticalement**
- rendu **stable Word** : le template fixe la géométrie, le code **ne touche pas** aux positions/dimensions dans les XML Word (cx/cy/offsets/positionH/positionV…)

Principe : **le template Word définit UNE “Logo Box”** (position + taille), et le code ne fait que :
1) produire une image finale à la taille exacte de la box (canvas)
2) remplacer le média dans `word/media/...` référencé par l’Alt Text (`LOGO_HEADER` / `LOGO_FOOTER`)

---

## 1) Template Word : conditions indispensables (sinon Word peut recouper)

### 1.1 Définir une “Logo Box” (placeholder image)
Dans le header (et éventuellement le footer), insérer une image factice (placeholder) et :
- lui donner la **taille MAX** acceptée (ex : 6.25 × 2.00 cm si c’est votre box actuelle),
- la mettre en position **fixe**,
- la positionner **relativement à la page** (ou au moins de façon stable : “page” ou “marges”),
- choisir un habillage “Devant le texte” (ou “Derrière le texte”, mais constant).

### 1.2 Identifier le placeholder via le texte alternatif (alt text)
Dans Word : clic droit sur l’image → “Modifier le texte de remplacement…”
- Header : `LOGO_HEADER`
- Footer (optionnel) : `LOGO_FOOTER`

**But** : le code détecte l’image cible par ce tag (et pas par un nom de fichier ou un id instable).

### 1.3 Cas multi-sections / première page différente
Si le document utilise :
- “Première page différente”,
- “Paires/impaires différentes”,
- ou plusieurs sections,
alors Word crée plusieurs headers/footers : le code doit remplacer partout où il voit `LOGO_HEADER` / `LOGO_FOOTER`.

---

### 1.4 (CRITIQUE) Remettre le rognage à zéro sur le placeholder
Même avec un PNG “parfait”, Word peut découper si le placeholder avait un crop enregistré (srcRect) dans le XML.

Dans Word :

1) sélectionner l’image placeholder
2) **Format de l’image → Rogner → Réinitialiser le rognage**
3) utiliser **Ajuster** (pas **Remplir**)

Le placeholder doit garder **une taille fixe** (logo_max) et être positionné exactement comme souhaité.

---

## 2) Contrat de config côté app (script.ai)
Le mode est volontairement contraint (“safe”) :

- `mode = "contain"` (**hard-coded**)
- `align = "left"` (**hard-coded**)
- `valign = "center"` (**hard-coded**)
- `padding_pct = 0.08` (défaut)
- `dpi = 300` (défaut)
- `trim_transparent = true`
- `trim_near_white = true` (avec tolérance + garde-fou si trop agressif)

---

## 3) Normalisation image (Python) — Pillow recommandé

### 3.1 Dépendances
- `Pillow`
- `lxml` (déjà utilisé dans le projet)

### 3.2 Fonction “safe” : canvas + collage à gauche
Entrée : `logo_bytes` + dimensions de box (`box_w_px`, `box_h_px`).

Sortie : bytes image à la **taille exacte de la box**, avec le logo déjà **placé à gauche**.

Règles V3 :

1) `exif_transpose` (anti-rotation)
2) conversion en `RGBA`
3) trim des marges inutiles :
   - transparent
   - quasi-blanc (tolérance douce)
   - garde-fou : si trop agressif (ex: > 60% de surface “supprimée”), on réduit l’agressivité ou on désactive le trim quasi-blanc
4) padding en pixels :

   $pad = round(min(box_w, box_h) * padding\_pct)$

5) contain (ratio conservé, pas de crop) dans la zone utile $(box_w-2pad, box_h-2pad)$
6) créer une canvas finale `RGBA(box_w, box_h)`
7) coller le logo à $(x=pad, y=(box_h-new_h)//2)$

Résultat : même si Word a tendance à centrer une image dans une frame, l’image générée contient déjà le “vide” à droite → le logo reste visuellement collé à gauche.

---

## 4) Remplacement dans DOCX (OpenXML) — sans casser la mise en page

### 4.1 Règle d’or
**Ne jamais modifier** les valeurs de position/taille dans `header*.xml` (cx/cy, offsets, anchor…).
On remplace uniquement le média dans `word/media/…` ciblé par l’Alt Text.

### 4.2 Algorithme
1) Ouvrir le DOCX (zip)
2) Lister tous les fichiers :
   - `word/header*.xml`
   - `word/footer*.xml`
3) Pour chaque header/footer :
   - parser XML
   - trouver l’objet image dont `wp:docPr/@descr` (alt text) == `LOGO_HEADER` (ou `LOGO_FOOTER`)
   - récupérer le `r:embed` du `a:blip` associé (ex : `rId1`)
4) Ouvrir `word/_rels/headerX.xml.rels` (ou footerX) :
   - trouver la relation `Id=rIdN` de type image
   - récupérer `Target` (ex : `media/image1.tif`)
5) Remplacer le fichier `word/media/...` par l’image normalisée :
   - soit en gardant le même nom/extension (simple)
   - soit en changeant vers `.png` :
     - mettre à jour le `Target` dans `.rels`
     - ajouter le content-type dans `[Content_Types].xml` si nécessaire

### 4.3 Content-Types (si changement d’extension)
Si vous remplacez un `.tif` par `.png`, vérifiez `[Content_Types].xml` :
- il faut une entrée `Default Extension="png" ContentType="image/png"`
- et/ou `tif` / `tiff` selon votre template

---

## 5) Qualité & garde-fous
- Si `LOGO_HEADER` introuvable → lever une erreur claire : “placeholder LOGO_HEADER absent du template”
- Ne pas toucher aux autres images (ex : image décorative en footer)
- Logguer :
  - image détectée (header/footer, rId, target)
  - taille box (cx/cy)
  - mode contain/cover + trim/padding
- Prévoir une taille min : si le logo “utile” est trop petit après trim, avertir

---

## 6) Notes sur votre template actuel
Dans `TEMPLATE_SIMPLE_BASE1.docx`, le header contient une image référencée via une relation (ex : `media/image1.tif`) et le footer contient aussi une image (ex : `media/image2.png`). Utiliser l’alt-text `LOGO_HEADER` / `LOGO_FOOTER` est la façon la plus fiable pour distinguer “le logo à remplacer” du reste.

---

## 7) DoD (Definition of Done)
Tests (auto et/ou manuel) avec :

- logo carré (PNG transparent)
- logo rectangle large
- logo avec grosses marges blanches (JPG)

Vérifier :

- pas de découpe
- ratio respecté
- logo collé à gauche dans la box
- stable sur pages suivantes (variants de header / sections)

