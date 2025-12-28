# Exemples de Structures de Données - Training UI

## 1. Résultat Scan Batch

```json
{
  "batch_name": "BATCH_20",
  "batch_path": "/path/to/BATCH_20",
  "clients": [
    {
      "folder_name": "KARAOUI Malik",
      "folder_path": "/path/to/BATCH_20/KARAOUI Malik",
      "compatibility_score": 0.87,
      "compatible": true,
      "gold_detected": true,
      "gold_score": 0.85,
      "rag_sources_count": 12,
      "rag_sources_by_type": {
        ".docx": 8,
        ".pdf": 3,
        ".txt": 1
      },
      "warnings_count": 0,
      "pipeline_ready": true,
      "scan_result": {
        "client_name": "KARAOUI Malik",
        "gold": {
          "path": "/path/to/BATCH_20/KARAOUI Malik/06 Rapport final/rapport_bilan_2024.docx",
          "score": 0.85,
          "strategy": "06_rapport_final",
          "size_bytes": 45678
        },
        "rag_sources": [
          {
            "path": "/path/to/BATCH_20/KARAOUI Malik/01 Dossier personnel/fiche_inscription.docx",
            "category": "01_personnel",
            "extension": ".docx",
            "size_bytes": 12345
          }
        ],
        "folder_structure": {
          "01_personnel": "/path/to/01 Dossier personnel",
          "06_rapport": "/path/to/06 Rapport final"
        },
        "warnings": [],
        "pipeline_ready": true,
        "stats": {
          "gold_found": true,
          "gold_score": 0.85,
          "rag_sources_count": 12,
          "extensions": {
            ".docx": 8,
            ".pdf": 3,
            ".txt": 1
          },
          "total_size_mb": 3.45,
          "folders_detected": 5,
          "folders_missing": 2
        }
      }
    }
  ],
  "summary": {
    "total": 20,
    "pipeline_ready": 15,
    "gold_detected": 18,
    "has_rag_sources": 19,
    "errors": 1,
    "warnings_total": 12
  },
  "timestamp": "2025-12-27T14:30:00"
}
```

## 2. Analyse Détaillée Client

```json
{
  "what_found": {
    "gold": {
      "name": "rapport_bilan_2024.docx",
      "path": "/path/to/rapport_bilan_2024.docx",
      "score": 0.85,
      "strategy": "06_rapport_final",
      "size_kb": 44.6
    },
    "rag_sources": [
      {
        "name": "fiche_inscription.docx",
        "category": "01_personnel",
        "extension": ".docx",
        "size_kb": 12.1
      },
      {
        "name": "test_psychotechnique.pdf",
        "category": "03_tests",
        "extension": ".pdf",
        "size_kb": 234.5
      }
    ],
    "folders": [
      {
        "key": "01_personnel",
        "path": "/path/to/01 Dossier personnel",
        "found": true
      },
      {
        "key": "06_rapport",
        "path": "/path/to/06 Rapport final",
        "found": true
      }
    ]
  },
  "what_usable": {
    "gold_usable": true,
    "rag_sources_usable": [
      {
        "name": "fiche_inscription.docx",
        "category": "01_personnel",
        "extension": ".docx",
        "size_kb": 12.1
      },
      {
        "name": "test_psychotechnique.pdf",
        "category": "03_tests",
        "extension": ".pdf",
        "size_kb": 234.5
      }
    ],
    "folders_usable": [
      {
        "key": "01_personnel",
        "path": "/path/to/01 Dossier personnel",
        "found": true
      },
      {
        "key": "03_tests",
        "path": "/path/to/03 Tests et bilans",
        "found": true
      }
    ]
  },
  "what_missing": [
    "✅ Client 100% pipeline-ready"
  ],
  "gold_choice": {
    "file": "rapport_bilan_2024.docx",
    "score": 0.85,
    "reason": "Trouvé dans '06 Rapport final' avec score 0.85"
  },
  "rag_preview": null
}
```

## 3. Résultat Génération RAG

```json
{
  "fields": {
    "nom": "Dupont",
    "prenom": "Jean",
    "date_naissance": "15/03/1985",
    "situation_professionnelle": "Demandeur d'emploi depuis 6 mois",
    "objectifs_professionnels": "Reconversion dans le secteur informatique",
    "projet_formation": "Non renseigné"
  },
  "debug": {
    "nom": {
      "value": "Dupont",
      "citations": [
        {
          "source": "dossier_personnel.docx",
          "snippet": "M. Jean Dupont, né le 15 mars 1985 à Paris...",
          "score": 0.92
        }
      ],
      "sources_used": ["dossier_personnel.docx"],
      "confidence": 0.92
    },
    "prenom": {
      "value": "Jean",
      "citations": [
        {
          "source": "dossier_personnel.docx",
          "snippet": "M. Jean Dupont, né le 15 mars 1985 à Paris...",
          "score": 0.92
        }
      ],
      "sources_used": ["dossier_personnel.docx"],
      "confidence": 0.92
    },
    "projet_formation": {
      "value": "Non renseigné",
      "citations": [],
      "sources_used": [],
      "confidence": 0.0
    }
  },
  "metrics": {
    "total_fields": 20,
    "filled_fields": 16,
    "coverage_pct": 80.0,
    "required_fields": 5,
    "required_filled": 4,
    "required_coverage_pct": 80.0,
    "avg_confidence": 0.78,
    "quality_score": 0.75
  },
  "timestamp": "2025-12-27T14:35:00"
}
```

## 4. Index RAG Build Result

```json
{
  "sources_count": 12,
  "sources": [
    {
      "file": "fiche_inscription.docx",
      "path": "/path/to/sources/fiche_inscription.docx",
      "extension": ".docx",
      "docs_count": 1
    },
    {
      "file": "test_psychotechnique.pdf",
      "path": "/path/to/sources/test_psychotechnique.pdf",
      "extension": ".pdf",
      "docs_count": 3
    }
  ],
  "documents_loaded": 15,
  "chunks_created": 156,
  "chunks_preview": [
    {
      "chunk_id": "abc123",
      "source_file": "fiche_inscription.docx",
      "text_preview": "M. Jean Dupont est demandeur d'emploi depuis 6 mois. Il souhaite effectuer une reconversion...",
      "text_length": 512
    },
    {
      "chunk_id": "def456",
      "source_file": "test_psychotechnique.pdf",
      "text_preview": "Résultats du test psychotechnique : Score global 75/100. Points forts : logique, raisonnement...",
      "text_length": 498
    }
  ],
  "index_built": true,
  "timestamp": "2025-12-27T14:33:00"
}
```

## 5. Output Final Génération

```json
{
  "success": true,
  "client_name": "KARAOUI_Malik",
  "outputs": {
    "generated_docx": "output/KARAOUI_Malik_generated.docx",
    "debug_json": "output/KARAOUI_Malik_debug.json",
    "metrics_json": "output/KARAOUI_Malik_metrics.json",
    "gold_reference": "output/KARAOUI_Malik_gold_reference.docx"
  },
  "metrics": {
    "total_fields": 20,
    "filled_fields": 16,
    "coverage_pct": 80.0,
    "required_fields": 5,
    "required_filled": 4,
    "required_coverage_pct": 80.0,
    "avg_confidence": 0.78,
    "quality_score": 0.75
  },
  "index_stats": {
    "sources_count": 12,
    "chunks_created": 156
  },
  "timestamp": "2025-12-27T14:36:00"
}
```

## 6. Metrics JSON (standalone)

```json
{
  "timestamp": "2025-12-27T14:36:00",
  "required_coverage": 80.0,
  "weighted_coverage": 80.0,
  "quality_score": 0.75,
  "avg_confidence": 0.78,
  "total_fields": 20,
  "filled_fields": 16,
  "required_fields": 5,
  "required_filled": 4
}
```

## 7. Debug JSON (standalone)

```json
{
  "timestamp": "2025-12-27T14:36:00",
  "gold_reference": "/path/to/gold/rapport_final.docx",
  "index": {
    "sources_count": 12,
    "sources": [
      {
        "file": "fiche_inscription.docx",
        "path": "/path/to/sources/fiche_inscription.docx",
        "extension": ".docx",
        "docs_count": 1
      }
    ],
    "chunks_created": 156,
    "chunks_preview": [
      {
        "chunk_id": "abc123",
        "source_file": "fiche_inscription.docx",
        "text_preview": "M. Jean Dupont est demandeur...",
        "text_length": 512
      }
    ]
  },
  "fields": {
    "nom": {
      "value": "Dupont",
      "citations": [
        {
          "source": "dossier_personnel.docx",
          "snippet": "M. Jean Dupont, né le...",
          "score": 0.92
        }
      ],
      "sources_used": ["dossier_personnel.docx"],
      "confidence": 0.92
    }
  },
  "coverage": {
    "filled_fields": 16,
    "total_fields": 20,
    "coverage_pct": 80.0
  },
  "warnings": [
    "⚠️ 4 champs sans citations",
    "⚠️ Confiance moyenne : 0.78"
  ]
}
```

## 8. Chunks Preview (debug UI)

```json
[
  {
    "chunk_id": 0,
    "source_file": "fiche_inscription.docx",
    "text": "M. Jean Dupont est demandeur d'emploi depuis 6 mois suite à un licenciement économique. Il souhaite effectuer une reconversion professionnelle dans le secteur informatique, domaine qui l'intéresse depuis plusieurs années. Lors de l'entretien initial, il a exprimé une forte motivation pour suivre une formation qualifiante.",
    "text_length": 340
  },
  {
    "chunk_id": 1,
    "source_file": "test_psychotechnique.pdf",
    "text": "Résultats du test psychotechnique administré le 12/11/2024 : Score global 75/100. Points forts identifiés : capacités de logique, raisonnement spatial, aptitude numérique. Points à développer : gestion du stress, organisation du travail. Recommandations : adapter les méthodes pédagogiques pour optimiser l'apprentissage.",
    "text_length": 335
  }
]
```

## Notes d'implémentation

### Calcul Score de Compatibilité

```python
score = 0.0

# GOLD (40% max)
if gold_score >= 0.5:
    score += 0.4
elif gold_score >= 0.3:
    score += 0.3

# Sources RAG (30% max)
if rag_count >= 3:
    score += 0.3
elif rag_count >= 1:
    score += 0.2

# Structure dossiers (20% max)
if folders_detected >= 4:
    score += 0.2
elif folders_detected >= 2:
    score += 0.1

# Bonus pipeline_ready (10%)
if pipeline_ready:
    score += 0.1
```

### Quality Score

```python
quality_score = coverage * 0.6 + confidence * 0.4
```

- 60% pondération : couverture des champs
- 40% pondération : confiance moyenne
