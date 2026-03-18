# tests/test_generate_v3.py
"""Test that generate_fields uses V3 specs when report_type is provided."""
from unittest.mock import patch, MagicMock
from core.generate import generate_fields


class TestGenerateV3:
    def test_v3_generates_only_report_type_sections(self):
        """When report_type='rapport_initial', only 7 sections are generated."""
        payload = {
            "documents": [
                {
                    "path": "/fake/journal.docx",
                    "text": "M. Dupont était technicien en arrêt maladie depuis 2022. "
                            "Il a un CFC de mécanicien obtenu en 2010 à Genève. "
                            "Obstacle principal : douleurs dorsales limitant le port de charges. "
                            "Piste retenue : reconversion en contrôle qualité. "
                            "Formation ECDL prévue durant la mesure RH Pro. "
                            "Stage effectué comme aide-comptable, évaluation positive. "
                            "La cible est validée, les limitations ont été respectées.",
                    "ext": ".docx",
                    "hash": "abc",
                    "pages": None,
                    "mtime": "2026-01-01",
                    "extractor": "docx",
                    "size_bytes": 1000,
                }
            ]
        }

        with patch("core.generate.ollama_generate") as mock_llm:
            mock_llm.return_value = MagicMock(
                success=True, value="Texte généré par le LLM."
            )

            answers = generate_fields(
                payload,
                model="test",
                host="http://localhost:11434",
                topk=3,
                temperature=0.2,
                top_p=0.9,
                report_type="rapport_initial",
            )

        # Should have exactly the 7 V3 sections
        expected_keys = {
            "PROFESSION", "FORMATION", "INCERTITUDE_ET_OBSTACLE",
            "ORIENTATION", "FORMATION_DURANT_MESURE", "STAGE", "CONCLUSION",
        }
        assert set(answers.keys()) == expected_keys

    def test_v3_without_report_type_uses_legacy(self):
        """Without report_type, falls back to V2/legacy behavior."""
        payload = {"documents": [{"path": "/f", "text": "texte", "ext": ".txt",
                                   "hash": "x", "pages": None, "mtime": "2026-01-01",
                                   "extractor": "txt", "size_bytes": 10}]}

        with patch("core.generate.ollama_generate") as mock_llm:
            mock_llm.return_value = MagicMock(
                success=True, value="Réponse."
            )

            answers = generate_fields(
                payload,
                model="test",
                host="http://localhost:11434",
                topk=3,
                temperature=0.2,
                top_p=0.9,
                # No report_type → legacy
            )

        # Should use DEFAULT_FIELDS (2 fields: PROFESSION, FORMATION)
        assert "PROFESSION" in answers
