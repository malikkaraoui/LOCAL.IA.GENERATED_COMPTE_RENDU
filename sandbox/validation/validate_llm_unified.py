#!/usr/bin/env python3
"""
Validation complète de l'intégration LLM unifiée
Vérifie que tous les composants sont correctement configurés
"""

def validate_imports():
    """Valide que tous les imports nécessaires fonctionnent"""
    print("\n🔍 Validation des imports...")
    try:
        from core.llm_router import LLMConfig, call_llm, LLMResponse, LLMError, check_ollama_health
        from backend.api.models import LLMConfigRequest, ReportCreateRequest
        from backend.workers.orchestrator import ReportGenerationParams
        from core.generate import generate_fields, ollama_generate, check_llm_status
        print("✅ Tous les imports réussis")
        return True
    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        return False

def validate_llm_config_model():
    """Valide le modèle LLMConfig"""
    print("\n🔍 Validation du modèle LLMConfig...")
    try:
        from core.llm_router import LLMConfig
        
        # Test 1: Config minimale
        config1 = LLMConfig(model="test-model")
        assert config1.provider == "ollama"
        assert config1.temperature == 0.2
        assert config1.timeout == 900.0
        print("✅ Config minimale OK")
        
        # Test 2: Config complète
        config2 = LLMConfig(
            provider="ollama",
            base_url="http://localhost:11434",
            model="qwen3-next:latest",
            temperature=0.5,
            max_tokens=2048,
            top_p=0.95,
            timeout=600.0
        )
        assert config2.base_url == "http://localhost:11434"
        assert config2.temperature == 0.5
        print("✅ Config complète OK")
        
        # Test 3: Conversion dict
        config_dict = config2.model_dump()
        assert "provider" in config_dict
        assert "model" in config_dict
        print("✅ Conversion dict OK")
        
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def validate_error_handling():
    """Valide la gestion d'erreur"""
    print("\n🔍 Validation de la gestion d'erreur...")
    try:
        from core.llm_router import _handle_ollama_error, LLMError
        import requests
        
        # Test 1: Erreur 404
        error404 = requests.exceptions.HTTPError()
        error404.response = type('obj', (), {'status_code': 404, 'text': '{"error":"model not found"}'})()
        llm_error = _handle_ollama_error(error404, "http://localhost:11434", "test-model", 10.0)
        assert llm_error.error_type in ["model_404", "endpoint_404"]
        print("✅ Erreur 404 OK")
        
        # Test 2: Timeout
        timeout_err = requests.exceptions.Timeout()
        llm_error = _handle_ollama_error(timeout_err, "http://localhost:11434", "test-model", 10.0)
        assert llm_error.error_type == "timeout"
        assert "10.0" in llm_error.message
        print("✅ Timeout OK")
        
        # Test 3: Connection refused
        conn_err = requests.exceptions.ConnectionError()
        llm_error = _handle_ollama_error(conn_err, "http://localhost:11434", "test-model", 10.0)
        assert llm_error.error_type == "connection_refused"
        print("✅ Connection refused OK")
        
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def validate_api_models():
    """Valide les modèles Pydantic de l'API"""
    print("\n🔍 Validation des modèles API...")
    try:
        from backend.api.models import LLMConfigRequest, ReportCreateRequest
        
        # Test 1: LLMConfigRequest
        llm_req = LLMConfigRequest(
            provider="ollama",
            model="qwen3-next:latest",
            temperature=0.3
        )
        assert llm_req.provider == "ollama"
        assert llm_req.max_tokens == 4096  # default
        print("✅ LLMConfigRequest OK")
        
        # Test 2: ReportCreateRequest avec llm
        report_req = ReportCreateRequest(
            client_name="Test Client",
            llm=llm_req
        )
        assert report_req.llm.model == "qwen3-next:latest"
        print("✅ ReportCreateRequest avec llm OK")
        
        # Test 3: ReportCreateRequest sans llm (rétrocompatibilité)
        report_req2 = ReportCreateRequest(
            client_name="Test Client 2"
        )
        assert report_req2.llm is None
        print("✅ Rétrocompatibilité OK")
        
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def validate_orchestrator():
    """Valide l'orchestrateur"""
    print("\n🔍 Validation de l'orchestrateur...")
    try:
        from backend.workers.orchestrator import ReportGenerationParams
        from core.llm_router import LLMConfig
        
        # Test 1: Params avec llm_config
        llm_config = LLMConfig(model="test-model")
        params = ReportGenerationParams(
            client_name="Test",
            template_path="/path/to/template",
            output_dir="/output",
            llm_config=llm_config
        )
        assert params.llm_config.model == "test-model"
        print("✅ ReportGenerationParams avec llm_config OK")
        
        # Test 2: Params sans llm_config (legacy)
        params2 = ReportGenerationParams(
            client_name="Test2",
            template_path="/path/to/template",
            output_dir="/output"
        )
        assert params2.llm_config is None
        print("✅ Params legacy OK")
        
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def validate_generate_integration():
    """Valide l'intégration dans core/generate.py"""
    print("\n🔍 Validation de core/generate.py...")
    try:
        from core.generate import generate_fields, ollama_generate
        from core.llm_router import LLMConfig
        
        # Vérifier que les fonctions acceptent llm_config
        import inspect
        
        # Test 1: generate_fields
        sig = inspect.signature(generate_fields)
        assert 'llm_config' in sig.parameters
        print("✅ generate_fields accepte llm_config")
        
        # Test 2: ollama_generate
        sig = inspect.signature(ollama_generate)
        assert 'llm_config' in sig.parameters
        print("✅ ollama_generate accepte llm_config")
        
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def validate_worker():
    """Valide le worker"""
    print("\n🔍 Validation du worker...")
    try:
        from backend.workers.report_worker import process_report_job
        import inspect
        
        # Vérifier que process_report_job accepte llm
        sig = inspect.signature(process_report_job)
        assert 'llm' in sig.parameters
        print("✅ process_report_job accepte paramètre llm")
        
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def main():
    print("=" * 70)
    print("🧪 VALIDATION INTÉGRATION LLM UNIFIÉE")
    print("=" * 70)
    
    results = []
    
    # Exécuter toutes les validations
    results.append(("Imports", validate_imports()))
    results.append(("LLMConfig Model", validate_llm_config_model()))
    results.append(("Error Handling", validate_error_handling()))
    results.append(("API Models", validate_api_models()))
    results.append(("Orchestrator", validate_orchestrator()))
    results.append(("Generate Integration", validate_generate_integration()))
    results.append(("Worker", validate_worker()))
    
    # Résumé
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ DES VALIDATIONS")
    print("=" * 70)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
    
    total = len(results)
    passed = sum(1 for _, s in results if s)
    
    print(f"\n🎯 Score: {passed}/{total} validations réussies")
    
    if passed == total:
        print("\n🎉 Toutes les validations sont passées!")
        print("✅ L'intégration LLM unifiée est production-ready")
        return 0
    else:
        print(f"\n⚠️  {total - passed} validation(s) ont échoué")
        print("❌ Corriger les erreurs avant déploiement")
        return 1

if __name__ == "__main__":
    exit(main())
