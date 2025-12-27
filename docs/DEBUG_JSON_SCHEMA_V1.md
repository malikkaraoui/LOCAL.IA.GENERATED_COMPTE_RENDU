# 📋 debug.json - Schéma v1.0

## Vue d'ensemble

Le fichier **debug.json** (par client) est généré automatiquement lors de la génération d'un rapport RH-Pro. Il contient des informations détaillées sur l'indexation RAG, les champs extraits avec leurs preuves (citations), et les warnings.

**Principe clé** : `no-evidence = no-claim`  
→ Chaque valeur de champ doit avoir des preuves traçables (citations depuis les sources).

---

## Structure Complète

```json
{
  "schema_version": "1.0",
  "artifact_type": "debug",
  "run_id": "run_20251227T194100Z_91f0aa12",
  "created_at": "2025-12-27T19:41:00Z",
  
  "conventions": {
    "language": "fr",
    "fallback_value": "Non renseigné",
    "strict_mode_default": true
  },
  
  "inputs": {
    "dataset_root": null,
    "client_root": "/path/to/AYNE Michael",
    "template_docx": "/path/to/template.docx"
  },
  
  "index": {
    "sources_count": 12,
    "documents_loaded": 12,
    "chunks_created": 220,
    "sources": [
      {
        "source_id": "CV.pdf",
        "path": "/path/to/sources/CV.pdf",
        "type": ".pdf",
        "loaded": true,
        "error": null
      }
    ]
  },
  
  "fields": {
    "nom": {
      "value": "AYNE",
      "confidence": 0.92,
      "citations": [
        {
          "source_id": "CV.pdf",
          "snippet": "...AYNE Michael, né le 15/03/1985...",
          "score": 0.81
        }
      ],
      "warnings": []
    },
    "formation": {
      "value": "Non renseigné",
      "confidence": 0.20,
      "citations": [],
      "warnings": ["no_evidence"]
    }
  }
}
```

---

## Sections Détaillées

### 1. Métadonnées

| Champ              | Type   | Description                                                       | Exemple                              |
|--------------------|--------|-------------------------------------------------------------------|--------------------------------------|
| `schema_version`   | string | Version du schéma (toujours `"1.0"`)                              | `"1.0"`                              |
| `artifact_type`    | string | Type d'artefact (toujours `"debug"`)                              | `"debug"`                            |
| `run_id`           | string | ID unique du run (format: `run_YYYYMMDDTHHMMSSZ_randomhex`)       | `"run_20251227T194100Z_91f0aa12"`    |
| `created_at`       | string | Timestamp ISO8601 de création                                     | `"2025-12-27T19:41:00Z"`             |

### 2. Conventions

| Champ                   | Type    | Description                                                   | Valeur                |
|-------------------------|---------|---------------------------------------------------------------|-----------------------|
| `language`              | string  | Langue du rapport (toujours `"fr"`)                           | `"fr"`                |
| `fallback_value`        | string  | Valeur par défaut si champ non trouvé                         | `"Non renseigné"`     |
| `strict_mode_default`   | boolean | Mode strict activé par défaut (interdire l'invention)         | `true`                |

### 3. Inputs

Informations sur les entrées du pipeline.

| Champ           | Type         | Description                                           | Exemple                              |
|-----------------|--------------|-------------------------------------------------------|--------------------------------------|
| `dataset_root`  | string/null  | Racine du dataset (null si test individuel)           | `null` ou `"/path/to/dataset"`       |
| `client_root`   | string       | Dossier racine du client                              | `"/path/to/AYNE Michael"`            |
| `template_docx` | string       | Chemin vers le template DOCX utilisé                  | `"/path/to/template.docx"`           |

### 4. Index

Statistiques d'indexation RAG.

| Champ               | Type    | Description                                           | Exemple |
|---------------------|---------|-------------------------------------------------------|---------|
| `sources_count`     | integer | Nombre de sources détectées                           | `12`    |
| `documents_loaded`  | integer | Nombre de documents chargés avec succès               | `12`    |
| `chunks_created`    | integer | Nombre de chunks créés pour l'index RAG               | `220`   |
| `sources`           | array   | Liste détaillée des sources (voir ci-dessous)         | `[...]` |

#### 4.1. Structure `sources[]`

| Champ       | Type         | Description                                | Exemple                      |
|-------------|--------------|--------------------------------------------|-----------------------------|
| `source_id` | string       | Nom du fichier (sans path)                 | `"CV.pdf"`                  |
| `path`      | string       | Chemin complet vers la source              | `"/path/to/sources/CV.pdf"` |
| `type`      | string       | Extension du fichier                       | `".pdf"`                    |
| `loaded`    | boolean      | Fichier chargé avec succès ?               | `true`                      |
| `error`     | string/null  | Message d'erreur si échec de chargement    | `null` ou `"Parse error"`   |

### 5. Fields

Informations détaillées sur chaque champ extrait.

Structure par champ :

```json
"nom_du_champ": {
  "value": "Valeur extraite ou 'Non renseigné'",
  "confidence": 0.92,
  "citations": [...],
  "warnings": []
}
```

#### 5.1. Propriétés de champ

| Propriété    | Type    | Description                                                      | Exemple                        |
|--------------|---------|------------------------------------------------------------------|--------------------------------|
| `value`      | string  | Valeur extraite (ou `fallback_value` si non trouvé)              | `"AYNE"` ou `"Non renseigné"`  |
| `confidence` | float   | Confiance de l'extraction (0.0 à 1.0)                            | `0.92`                         |
| `citations`  | array   | Liste de citations prouvant la valeur (max 3)                    | `[{...}, {...}]`               |
| `warnings`   | array   | Avertissements liés à ce champ                                   | `["no_evidence"]`              |

#### 5.2. Structure `citations[]`

| Propriété   | Type   | Description                                           | Exemple                                    |
|-------------|--------|-------------------------------------------------------|--------------------------------------------|
| `source_id` | string | Nom du fichier source                                 | `"CV.pdf"`                                 |
| `snippet`   | string | Extrait de texte prouvant la valeur (max 200 chars)   | `"...AYNE Michael, né le 15/03/1985..."`   |
| `score`     | float  | Score de pertinence RAG (0.0 à 1.0)                   | `0.81`                                     |

#### 5.3. Warnings Possibles

| Code               | Description                                                  | Quand ?                                |
|--------------------|--------------------------------------------------------------|----------------------------------------|
| `no_evidence`      | Aucune preuve trouvée dans les sources                       | `citations = []`                       |
| `low_confidence`   | Confiance faible (< 0.5)                                     | `confidence < 0.5`                     |

---

## Règles de Génération

### 1. Principe `no-evidence = no-claim`

- **Si aucune citation** → `value = "Non renseigné"` + `warnings = ["no_evidence"]`
- **Si citations présentes** → `value = valeur extraite` + `confidence` calculée
- **Si confidence < 0.5** → `warnings = ["low_confidence"]`

### 2. Citations (max 3 par champ)

- Limiter à 3 citations les plus pertinentes (score RAG le plus élevé)
- Tronquer snippet à 200 caractères max
- Inclure `source_id` + `snippet` + `score`

### 3. Strict Mode

- Si `strict_mode = true` → Interdire l'invention, retourner `"Non renseigné"` si non trouvé
- Si `strict_mode = false` → Permettre génération LLM (mais toujours tracer confidence)

---

## Exemples de Champs

### Exemple 1 : Champ bien documenté (nom)

```json
"nom": {
  "value": "AYNE",
  "confidence": 0.92,
  "citations": [
    {
      "source_id": "CV.pdf",
      "snippet": "AYNE Michael, né le 15/03/1985 à Paris",
      "score": 0.81
    }
  ],
  "warnings": []
}
```

**Interprétation** : Valeur `AYNE` extraite avec haute confiance (0.92), preuve dans `CV.pdf`.

### Exemple 2 : Champ sans preuve (formation)

```json
"formation": {
  "value": "Non renseigné",
  "confidence": 0.20,
  "citations": [],
  "warnings": ["no_evidence"]
}
```

**Interprétation** : Aucune preuve trouvée → valeur par défaut `"Non renseigné"`, warning `no_evidence`.

### Exemple 3 : Champ avec confiance faible

```json
"situation_professionnelle": {
  "value": "Au chômage depuis janvier 2024",
  "confidence": 0.45,
  "citations": [
    {
      "source_id": "Rapport_final.docx",
      "snippet": "M. AYNE est actuellement sans emploi",
      "score": 0.55
    }
  ],
  "warnings": ["low_confidence"]
}
```

**Interprétation** : Valeur extraite mais confiance faible (0.45 < 0.5) → warning `low_confidence`.

---

## Alignement avec Autres Artefacts

### metrics.json

- `debug.json` contient les détails par champ (value, confidence, citations)
- `metrics.json` contient les agrégats (coverage globale, quality_score, avg_confidence)

**Relation** :
- `metrics.avg_confidence` = moyenne des `debug.fields[*].confidence`
- `metrics.filled_fields` = nombre de champs où `value != "Non renseigné"`

### validation.json

- `validation.json` utilise `metrics.json` + `debug.json` pour calculer GO/NO_GO/DRAFT
- Validation vérifie :
  - Coverage ≥ seuil profil
  - Quality ≥ seuil profil
  - Confidence ≥ seuil profil
  - Champs critiques remplis (depuis `debug.fields`)

---

## Usage Recommandé

### Dans l'UI Streamlit

Onglet **"🧪 Test Client"** :
1. Run pipeline → génère `*_debug.json`
2. Télécharger pour analyse détaillée
3. Consulter `fields` pour voir preuves (citations)
4. Consulter `warnings` pour identifier problèmes

### Analyse Post-Génération

**Questions fréquentes** :

1. **"Pourquoi champ X = Non renseigné ?"**
   → Consulter `debug.fields.X.citations` → Si `[]`, aucune preuve trouvée

2. **"Comment améliorer confidence de Y ?"**
   → Consulter `debug.fields.Y.citations[0].snippet` → Vérifier qualité sources

3. **"Quelles sources ont été indexées ?"**
   → Consulter `debug.index.sources` → Liste complète avec status `loaded`

4. **"Combien de chunks créés ?"**
   → Consulter `debug.index.chunks_created` → Si trop faible, ajouter sources

---

## Schéma JSON Formel (JSON Schema)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["schema_version", "artifact_type", "run_id", "created_at", "conventions", "inputs", "index", "fields"],
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "1.0"
    },
    "artifact_type": {
      "type": "string",
      "const": "debug"
    },
    "run_id": {
      "type": "string",
      "pattern": "^run_[0-9]{8}T[0-9]{6}Z_[a-f0-9]+$"
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "conventions": {
      "type": "object",
      "required": ["language", "fallback_value", "strict_mode_default"],
      "properties": {
        "language": {"type": "string", "const": "fr"},
        "fallback_value": {"type": "string", "const": "Non renseigné"},
        "strict_mode_default": {"type": "boolean"}
      }
    },
    "inputs": {
      "type": "object",
      "required": ["dataset_root", "client_root", "template_docx"],
      "properties": {
        "dataset_root": {"type": ["string", "null"]},
        "client_root": {"type": "string"},
        "template_docx": {"type": "string"}
      }
    },
    "index": {
      "type": "object",
      "required": ["sources_count", "documents_loaded", "chunks_created", "sources"],
      "properties": {
        "sources_count": {"type": "integer", "minimum": 0},
        "documents_loaded": {"type": "integer", "minimum": 0},
        "chunks_created": {"type": "integer", "minimum": 0},
        "sources": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["source_id", "path", "type", "loaded", "error"],
            "properties": {
              "source_id": {"type": "string"},
              "path": {"type": "string"},
              "type": {"type": "string"},
              "loaded": {"type": "boolean"},
              "error": {"type": ["string", "null"]}
            }
          }
        }
      }
    },
    "fields": {
      "type": "object",
      "patternProperties": {
        "^[a-z_]+$": {
          "type": "object",
          "required": ["value", "confidence", "citations", "warnings"],
          "properties": {
            "value": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "citations": {
              "type": "array",
              "items": {
                "type": "object",
                "required": ["source_id", "snippet", "score"],
                "properties": {
                  "source_id": {"type": "string"},
                  "snippet": {"type": "string"},
                  "score": {"type": "number", "minimum": 0, "maximum": 1}
                }
              }
            },
            "warnings": {
              "type": "array",
              "items": {"type": "string", "enum": ["no_evidence", "low_confidence"]}
            }
          }
        }
      }
    }
  }
}
```

---

## Fichier Généré Par

**Fonction** : `RHProReportGenerator._export_debug_json()`  
**Fichier** : `src/rhpro/report_generator.py`

**Appelé depuis** :
- `RHProReportGenerator.generate_from_client()` (génération complète)
- UI Streamlit onglet "🧪 Test Client" (pipeline complet)

---

## Historique Versions

| Version | Date          | Changements                                                        |
|---------|---------------|--------------------------------------------------------------------|
| 1.0     | 27 déc 2025   | Schéma initial v1.0 conforme spec (alignment training_state.json)  |

---

## Voir Aussi

- [training_state.json](TRAINING_UI_IMPLEMENTATION.md) - Schéma v1.0 pour dataset training
- [metrics.json](PRODUCTION_GATE_SCORING_V2.md) - Métriques agrégées
- [validation.json](CRITICAL_FIELDS_IMPLEMENTATION.md) - Résultat validation GO/NO_GO/DRAFT
- [TRAINING_UI_QUICKSTART.md](TRAINING_UI_QUICKSTART.md) - Guide UI Streamlit
