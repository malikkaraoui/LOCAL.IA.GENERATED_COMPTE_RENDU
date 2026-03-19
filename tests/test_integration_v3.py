# tests/test_integration_v3.py
"""End-to-end test: report_type=rapport_initial generates 7 sections with evaluations."""
from unittest.mock import patch, MagicMock
from core.generate import generate_fields
from core.section_evaluator import evaluate_report
from core.field_specs_v3 import get_specs_for_report_type


class TestIntegrationV3:
    def test_full_pipeline_rapport_initial(self):
        payload = {
            "documents": [{
                "path": "/test/journal.docx",
                "text": (
                    "M. Dupont, ancien technicien de maintenance, est en arrêt maladie "
                    "depuis mars 2024 suite à un accident du travail (chute sur chantier). "
                    "Il occupait un poste de technicien chez ABB SA à plein temps. "
                    "Ses missions comprenaient la maintenance préventive, le diagnostic "
                    "de pannes et la coordination avec les sous-traitants. "
                    "Il travaillait en équipe de 6 sur le terrain. "
                    "Ses compétences techniques sont transférables. "
                    "Il possède un CFC de mécanicien industriel obtenu en 2008 à Genève "
                    "et une formation continue en automatisation (2015, CEFCO). "
                    "Obstacles : douleurs dorsales chroniques limitant le port de charges, "
                    "pas de permis de conduire. Nécessite un aménagement de poste. "
                    "Piste retenue : contrôle qualité (compatible physiquement). "
                    "Piste non retenue : retour en maintenance (contre-indiqué par limitations). "
                    "Formation ECDL avancé prévue durant la mesure RH Pro. "
                    "Stage de 4 semaines comme aide au contrôle qualité chez Rolex. "
                    "Évaluation positive, le stage a validé l'orientation. "
                    "Conclusion : la cible professionnelle est confirmée par le stage. "
                    "Les limitations physiques ont été respectées."
                ),
                "ext": ".docx", "hash": "test", "pages": None,
                "mtime": "2026-01-01", "extractor": "docx", "size_bytes": 2000,
            }]
        }

        with patch("core.generate.ollama_generate") as mock_llm:
            # Return different text per section
            mock_llm.return_value = MagicMock(
                success=True,
                value=(
                    "M. Dupont était en arrêt maladie. Il occupait un poste de technicien "
                    "de maintenance chez ABB. Ses missions comprenaient la maintenance "
                    "préventive et le diagnostic. Il travaillait en équipe sur le terrain. "
                    "Suite à un accident, il a dû cesser. Ses compétences sont transférables."
                ),
            )

            answers = generate_fields(
                payload,
                model="test", host="http://localhost:11434",
                topk=3, temperature=0.2, top_p=0.9,
                report_type="rapport_initial",
            )

        assert len(answers) == 7

        # Evaluate all sections
        specs = get_specs_for_report_type("rapport_initial")
        flat_answers = {k: v.get("value", "") for k, v in answers.items()}
        evaluations = evaluate_report(specs, flat_answers)

        assert len(evaluations) == 7
        for key, ev in evaluations.items():
            assert ev.status in ("BON", "A_REVOIR", "VIDE"), f"{key}: {ev.status}"
