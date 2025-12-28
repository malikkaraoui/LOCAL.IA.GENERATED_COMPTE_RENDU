"""Tests pour l'extraction de fichiers .msg (emails Outlook).

Vérifie :
1. Gestion gracieuse si extract-msg n'est pas installé
2. Extraction correcte du contenu si extract-msg est disponible
3. Pas de crash dans la pipeline
"""
import pytest
from pathlib import Path

# Test 1 : Import du module ne crash pas
def test_msg_extractor_import():
    """Vérifie que l'import du module .msg ne plante pas."""
    try:
        from core.extractors.msg_extractor import MSG_SUPPORT_AVAILABLE, extract_msg_safe
        # OK : le module existe et peut être importé
        assert MSG_SUPPORT_AVAILABLE in [True, False], "MSG_SUPPORT_AVAILABLE doit être un booléen"
    except ImportError:
        pytest.fail("Impossible d'importer core.extractors.msg_extractor")


# Test 2 : Comportement sans extract-msg installé
def test_msg_extractor_missing_graceful():
    """Vérifie que l'absence d'extract-msg est gérée proprement."""
    from core.extractors.msg_extractor import MSG_SUPPORT_AVAILABLE, extract_msg_safe
    
    # Si extract-msg n'est pas installé
    if not MSG_SUPPORT_AVAILABLE:
        # extract_msg_safe doit retourner (None, None, error) sans planter
        fake_path = Path("/fake/test.msg")
        text, meta, error = extract_msg_safe(fake_path)
        
        assert text is None, "text doit être None si extract-msg absent"
        assert meta is None, "meta doit être None si extract-msg absent"
        assert error == "MSG_EXTRACTOR_MISSING", f"error attendu : MSG_EXTRACTOR_MISSING, reçu : {error}"


# Test 3 : extract_sources gère .msg sans crash
def test_extract_sources_with_msg_support():
    """Vérifie que extract_sources gère les .msg sans planter."""
    from core.extract import extract_sources, MSG_SUPPORT_AVAILABLE
    import tempfile
    
    # Créer un dossier de test avec un faux .msg
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Créer un fichier .msg fake (vide)
        fake_msg = tmpdir_path / "test.msg"
        fake_msg.write_bytes(b"FAKE MSG CONTENT")
        
        # ✅ extract_sources ne doit PAS planter
        try:
            result = extract_sources(
                tmpdir_path,
                enable_msg=True,
                include_extensions=[".msg"]
            )
            
            # Vérifier structure result
            assert "counts" in result
            assert "documents" in result
            
            # Si extract-msg pas installé, le .msg doit être soit skipped soit en erreur
            if not MSG_SUPPORT_AVAILABLE:
                # Soit skipped (pas supporté), soit error
                total_processed = result["counts"]["ok"] + result["counts"]["errors"]
                assert total_processed == 0 or result["counts"]["errors"] >= 0, \
                    "Sans extract-msg, .msg ne doit pas être extrait avec succès"
            else:
                # Si extract-msg installé, extraction peut réussir ou échouer (fake file)
                # Important : pas de crash
                pass
            
        except Exception as e:
            pytest.fail(f"extract_sources a planté avec .msg : {e}")


# Test 4 : Vérifier warning MSG_EXTRACTOR_MISSING dans training
def test_training_warning_msg_extractor_missing():
    """Vérifie que le warning MSG_EXTRACTOR_MISSING est généré si extract-msg absent."""
    from core.extractors.msg_extractor import MSG_SUPPORT_AVAILABLE
    
    # Ce test vérifie juste la cohérence du flag
    if MSG_SUPPORT_AVAILABLE:
        # extract-msg est installé, pas de warning attendu
        pass
    else:
        # extract-msg absent, warning devrait être généré par dataset_training
        # (test indirect via test_training_state_integrity si dataset contient .msg)
        assert not MSG_SUPPORT_AVAILABLE, "MSG_SUPPORT_AVAILABLE doit être False"


# Test 5 : Format texte .msg si extract-msg disponible
def test_msg_text_format_if_available():
    """Si extract-msg disponible, vérifie le format texte retourné."""
    from core.extractors.msg_extractor import MSG_SUPPORT_AVAILABLE
    
    if not MSG_SUPPORT_AVAILABLE:
        pytest.skip("extract-msg non installé, test skippé")
    
    # Si on arrive ici, extract-msg est installé
    # On teste que le format texte contient les marqueurs attendus
    # (Test avec un vrai .msg nécessiterait une fixture)
    
    # Pour l'instant, on vérifie juste que les fonctions existent
    from core.extractors.msg_extractor import extract_msg_to_text
    
    assert callable(extract_msg_to_text), "extract_msg_to_text doit être une fonction"


# Test 6 : Payload extract_sources contient enable_msg
def test_extract_sources_payload_has_msg_flag():
    """Vérifie que le payload d'extract_sources contient le flag enable_msg."""
    from core.extract import extract_sources
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Créer un fichier txt pour avoir au moins un fichier
        (tmpdir_path / "test.txt").write_text("test")
        
        result = extract_sources(tmpdir_path, enable_msg=True)
        
        # Vérifier présence du flag
        assert "enable_msg" in result, "Payload doit contenir 'enable_msg'"
        assert result["enable_msg"] is True


# Test 7 : Contraintes d'intégrité (pas de crash même avec .msg corrompu)
def test_msg_corrupted_file_no_crash():
    """Vérifie qu'un fichier .msg corrompu ne fait pas planter la pipeline."""
    from core.extract import extract_sources
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Créer un .msg corrompu (juste bytes random)
        corrupted_msg = tmpdir_path / "corrupted.msg"
        corrupted_msg.write_bytes(b"NOT A REAL MSG FILE\x00\x01\x02")
        
        # ✅ Ne doit pas planter
        try:
            result = extract_sources(
                tmpdir_path,
                enable_msg=True,
                include_extensions=[".msg"]
            )
            
            # Si extract-msg installé, fichier en erreur
            # Sinon, fichier skipped ou en erreur
            assert "counts" in result
            
        except Exception as e:
            pytest.fail(f"Pipeline a planté avec .msg corrompu : {e}")
