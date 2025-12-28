"""
Page Streamlit pour Training & Test RH-Pro.

Permet de :
1. Onglet "Entraîner dataset" : analyser un dataset complet et générer training_state.json v1.0
2. Onglet "Test client" : tester un client avec le pipeline complet (normalize → index → docx → validate)
"""
import streamlit as st
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import traceback
from datetime import datetime

# Ajouter le projet au path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.rhpro.dataset_training import (
    discover_client_folders,
    analyze_dataset,
    export_training_artifacts,
    load_training_state,
)
from src.rhpro.client_scanner import scan_client_folder
from src.rhpro.client_normalizer import normalize_client_to_sandbox
from src.rhpro.validation_profiles import validate_report, ValidationProfile
from rapport_orchestrator import RapportOrchestrator, PipelineConfig


def browse_directory(label: str, help_text: str = "", key_suffix: str = "") -> Optional[str]:
    """
    Permet de sélectionner un dossier via saisie manuelle ou suggestions.
    Alternative sans tkinter pour compatibilité maximale.
    """
    key_base = f"{label}_{key_suffix}" if key_suffix else label
    
    # Suggestions de chemins communs
    suggestions = [
        "/Users/malik/Documents/RH PRO BASE DONNEE/DATASET TRAINING/BATCH 20",
        "/Users/malik/Documents/SCRIPT.IA_DATA/training_sandbox",
        "./sandbox",
        str(Path.home() / "Documents"),
    ]
    
    # Input avec autocomplete via selectbox
    col1, col2 = st.columns([4, 1])
    
    with col1:
        path_input = st.text_input(
            label,
            value=st.session_state.get(f"path_{key_base}", ""),
            help=help_text,
            key=f"input_{key_base}",
            placeholder="Ex: /Users/malik/Documents/...",
        )
    
    with col2:
        st.write("")
        st.write("")
        # Bouton pour afficher les suggestions
        if st.button("💡", key=f"suggest_{key_base}", help="Afficher les suggestions"):
            st.session_state[f"show_suggestions_{key_base}"] = not st.session_state.get(f"show_suggestions_{key_base}", False)
    
    # Afficher les suggestions si demandé
    if st.session_state.get(f"show_suggestions_{key_base}", False):
        st.markdown("**Chemins suggérés** (cliquez pour utiliser) :")
        for suggestion in suggestions:
            if Path(suggestion).exists():
                if st.button(f"✅ {suggestion}", key=f"use_{key_base}_{hash(suggestion)}"):
                    st.session_state[f"path_{key_base}"] = suggestion
                    st.session_state[f"show_suggestions_{key_base}"] = False
                    st.rerun()
            else:
                st.caption(f"⚠️ {suggestion} (n'existe pas)")
    
    return path_input if path_input else None


def show_training_tab():
    """Onglet A : Entraîner dataset."""
    st.markdown("### 🎓 Entraînement Dataset")
    st.markdown("---")
    
    st.markdown("""
    **Objectif** : Analyser un dataset de dossiers clients pour extraire des patterns agrégés 
    (statistiques de sections/champs) et produire un fichier **training_state.json v1.0** 
    exploitable par la génération RAG.
    
    ⚠️ **Aucune donnée nominative** n'est stockée dans training_state.json (uniquement stats agrégées).
    """)
    
    # Browse dataset
    dataset_root = browse_directory(
        "📁 Dataset racine",
        "Dossier contenant les clients (BATCH 20, 580 dossiers, etc.)",
        key_suffix="training"
    )
    
    if not dataset_root or not Path(dataset_root).exists():
        st.warning("⚠️ Veuillez sélectionner un dataset valide")
        return
    
    st.success(f"✅ Dataset : `{dataset_root}`")
    
    # Configuration
    col1, col2, col3 = st.columns(3)
    
    with col1:
        scan_depth = st.number_input(
            "Profondeur scan",
            min_value=1,
            max_value=5,
            value=3,
            help="Profondeur de recherche récursive pour dossiers hétérogènes"
        )
    
    with col2:
        limit = st.number_input(
            "Limite clients",
            min_value=0,
            max_value=1000,
            value=0,
            help="0 = analyser tous les clients détectés"
        )
    
    with col3:
        merge_existing = st.checkbox(
            "Merge avec existant",
            value=False,
            help="Fusionner avec training_state existant (mode incrémental)"
        )
    
    # Output directory
    out_dir = st.text_input(
        "📂 Dossier sortie",
        value="output/training",
        help="Où sauvegarder les artefacts (training_state.json, report.md, etc.)"
    )
    
    st.markdown("---")
    
    # Lancer training
    if st.button("🚀 Lancer Entraînement", type="primary", use_container_width=True):
        with st.spinner("🔍 Découverte des clients..."):
            try:
                client_folders = discover_client_folders(
                    dataset_root,
                    scan_depth=scan_depth
                )
                
                st.info(f"📁 **{len(client_folders)} clients détectés**")
                
                if limit > 0:
                    client_folders = client_folders[:limit]
                    st.info(f"🎯 Limitation appliquée : {len(client_folders)} clients seront analysés")
            
            except Exception as e:
                st.error(f"❌ Erreur découverte : {e}")
                return
        
        with st.spinner("📊 Analyse du dataset en cours..."):
            try:
                result = analyze_dataset(
                    dataset_root,
                    out_dir=out_dir,
                    scan_depth=scan_depth,
                    limit=limit if limit > 0 else None
                )
                
                st.success("✅ Analyse terminée !")
            
            except Exception as e:
                st.error(f"❌ Erreur analyse : {e}")
                st.code(traceback.format_exc())
                return
        
        with st.spinner("💾 Export des artefacts..."):
            try:
                paths = export_training_artifacts(
                    result,
                    out_dir=out_dir,
                    merge_existing=merge_existing
                )
                
                st.success("✅ Export terminé !")
                
                # Afficher résumé
                st.markdown("---")
                st.markdown("### 📊 Ce que j'ai retenu")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "Clients analysés",
                        result.stats["total_clients"]
                    )
                
                with col2:
                    st.metric(
                        "Clients utilisables",
                        result.stats["successful_scans"]
                    )
                
                with col3:
                    st.metric(
                        "GOLD détectés",
                        result.stats["gold_detected"],
                        f"{result.stats['gold_detection_rate']:.0%}"
                    )
                
                with col4:
                    st.metric(
                        "Pipeline ready",
                        result.stats["pipeline_ready"],
                        f"{result.stats['pipeline_ready_rate']:.0%}"
                    )
                
                # Types de docs
                st.markdown("#### 📄 Types de documents détectés")
                doc_types = result.stats.get("extensions_distribution", {})
                if doc_types:
                    cols = st.columns(len(doc_types))
                    for i, (ext, count) in enumerate(doc_types.items()):
                        with cols[i]:
                            st.metric(ext, count)
                
                # Sections canoniques
                if "sections_stats" in result.patterns:
                    st.markdown("#### 📑 Sections canoniques détectées")
                    
                    sections_data = []
                    for canonical, stats in result.patterns["sections_stats"].items():
                        sections_data.append({
                            "Section": canonical.upper(),
                            "Coverage %": f"{stats['coverage']*100:.0f}%",
                            "Clients": stats.get("clients", stats.get("clients_with_section", 0)),  # ✅ Utiliser le nouveau champ
                            "Avg lines": stats["avg_lines"],
                            "P50": stats["p50_lines"],
                            "P90": stats["p90_lines"],
                        })
                    
                    if sections_data:
                        st.dataframe(sections_data, use_container_width=True, hide_index=True)
                
                # Afficher training_state.json
                st.markdown("#### 🎯 Training State (v1.0)")
                training_state_path = Path(paths["training_state"])
                
                with open(training_state_path, "r") as f:
                    state = json.load(f)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Schema Version", state["schema_version"])
                    st.metric("Run ID", state["run_id"])
                    st.metric("Fallback Value", state["conventions"]["fallback_value"])
                
                with col2:
                    st.metric("Clients scannés", state["dataset"]["clients_scanned"])
                    st.metric("Clients utilisés", state["dataset"]["clients_used"])
                    st.metric("GOLD détectés", state["dataset"]["gold_stats"]["gold_detected_clients"])
                
                # Profils de validation
                st.markdown("#### ⚖️ Profils de validation")
                profiles_cols = st.columns(3)
                
                for i, (profile_name, profile_data) in enumerate(state["profiles"].items()):
                    with profiles_cols[i]:
                        st.markdown(f"**{profile_name}**")
                        st.write(f"- Coverage min: {profile_data['coverage_min']}%")
                        st.write(f"- Quality min: {profile_data['quality_min']}")
                        st.write(f"- Confidence min: {profile_data['confidence_min']}")
                
                # Warnings
                if state.get("warnings"):
                    st.markdown("#### ⚠️ Warnings")
                    for warning in state["warnings"]:
                        st.warning(f"**{warning['code']}** : {warning['message']} (count: {warning['count']})")
                
                # Boutons download
                st.markdown("---")
                st.markdown("#### 📥 Téléchargements")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Lire le fichier une seule fois
                    training_state_data = training_state_path.read_bytes()
                    st.download_button(
                        "📄 training_state.json",
                        data=training_state_data,
                        file_name=training_state_path.name,
                        mime="application/json",
                        use_container_width=True,
                        key="download_training_state"
                    )
                
                with col2:
                    report_path = Path(paths["report"])
                    if report_path.exists():
                        # Lire le fichier une seule fois
                        report_data = report_path.read_bytes()
                        st.download_button(
                            "📝 training_report.md",
                            data=report_data,
                            file_name=report_path.name,
                            mime="text/markdown",
                            use_container_width=True,
                            key="download_training_report"
                        )
                
                with col3:
                    # Afficher le chemin et permettre de copier
                    st.caption("Dossier de sortie:")
                    st.code(str(training_state_path.parent), language=None)
                    # Bouton pour ouvrir dans Finder (macOS)
                    open_folder_code = f"open '{str(training_state_path.parent)}'"
                    st.caption("Commande à exécuter:")
                    st.code(open_folder_code, language="bash")
                
                # Sauvegarder le path pour l'onglet Test
                st.session_state["last_training_state"] = str(training_state_path)
                st.session_state["last_dataset_root"] = dataset_root
            
            except Exception as e:
                st.error(f"❌ Erreur export : {e}")
                st.code(traceback.format_exc())


def show_test_tab():
    """Onglet B : Test sur un client."""
    st.markdown("### 🧪 Test Client")
    st.markdown("---")
    
    st.markdown("""
    **Objectif** : Tester le pipeline complet sur un client individuel :
    1. Normalisation (sandbox)
    2. Indexation RAG
    3. Génération DOCX
    4. Validation (GO/NO_GO/DRAFT)
    
    Utilise un **training_state.json** pour améliorer la génération.
    """)
    
    # Sélection dataset pour lister les clients
    dataset_root = browse_directory(
        "📁 Dataset racine",
        "Dossier contenant les clients (pour liste déroulante)",
        key_suffix="test"
    )
    
    selected_client_folder = None
    
    if dataset_root and Path(dataset_root).exists():
        with st.spinner("🔍 Scan des clients..."):
            try:
                client_folders = discover_client_folders(dataset_root, scan_depth=3)
                
                if client_folders:
                    st.success(f"✅ {len(client_folders)} clients trouvés")
                    
                    # Recherche par nom
                    search = st.text_input(
                        "🔎 Rechercher un client",
                        placeholder="Ex: AYNE Michael, KARAOUI, etc.",
                        help="Filtrer la liste par nom"
                    )
                    
                    # Filtrer
                    if search:
                        filtered = [
                            f for f in client_folders
                            if search.lower() in f.name.lower()
                        ]
                    else:
                        filtered = client_folders
                    
                    # Sélection
                    client_names = [f.name for f in filtered]
                    
                    if client_names:
                        selected_name = st.selectbox(
                            "Choisir un client",
                            options=client_names,
                            help=f"{len(filtered)} client(s) affiché(s)"
                        )
                        
                        if selected_name:
                            selected_client_folder = next(
                                f for f in filtered if f.name == selected_name
                            )
                            st.info(f"📁 Client sélectionné : `{selected_client_folder}`")
                    else:
                        st.warning("⚠️ Aucun client ne correspond à la recherche")
                else:
                    st.warning("⚠️ Aucun client détecté dans ce dataset")
            
            except Exception as e:
                st.error(f"❌ Erreur scan : {e}")
    
    # Training state
    st.markdown("---")
    st.markdown("#### 🎯 Training State")
    
    training_state_path = None
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        default_path = st.session_state.get("last_training_state", "")
        training_state_input = st.text_input(
            "Fichier training_state.json",
            value=default_path,
            help="Path vers training_state.json (optionnel)",
            key="training_state_input"
        )
    
    with col2:
        st.write("")
        st.write("")
        if st.button("📁 Browse", key="browse_training_state"):
            try:
                import tkinter as tk
                from tkinter import filedialog
                
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                
                file_path = filedialog.askopenfilename(
                    title="Sélectionner training_state.json",
                    filetypes=[("JSON", "*.json"), ("All files", "*.*")]
                )
                
                if file_path:
                    st.session_state["training_state_input"] = file_path
                    st.rerun()
            
            except Exception as e:
                st.error(f"Erreur browse : {e}")
    
    if training_state_input and Path(training_state_input).exists():
        training_state_path = training_state_input
        st.success(f"✅ Training state : `{Path(training_state_path).name}`")
    
    # Profil de validation
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        profile = st.selectbox(
            "Profil de validation",
            options=["STRICT", "STANDARD", "DRAFT"],
            index=1,
            help="STRICT = production RH-Pro, STANDARD = acceptable, DRAFT = brouillon"
        )
    
    with col2:
        strict_mode = st.checkbox(
            "Mode strict",
            value=True,
            help="Activer les vérifications strictes (champs critiques, etc.)"
        )
    
    # Output directory
    out_dir = st.text_input(
        "📂 Dossier sortie",
        value="output/test_client",
        help="Où sauvegarder les fichiers générés"
    )
    
    st.markdown("---")
    
    # Run pipeline
    if st.button("▶️ Run Pipeline Complet", type="primary", use_container_width=True, disabled=not selected_client_folder):
        if not selected_client_folder:
            st.error("❌ Veuillez sélectionner un client")
            return
        
        output_path = Path(out_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Timestamp pour fichiers
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        client_slug = selected_client_folder.name.replace(" ", "_").replace("/", "_")
        
        # Étape 1: Scanner
        with st.spinner("1️⃣ Scan du client..."):
            try:
                scan_result = scan_client_folder(str(selected_client_folder))
                st.success(f"✅ Scan OK : {len(scan_result['rag_sources'])} sources détectées")
                
                if scan_result.get("gold"):
                    st.info(f"🥇 GOLD détecté : {Path(scan_result['gold']['path']).name}")
            
            except Exception as e:
                st.error(f"❌ Erreur scan : {e}")
                return
        
        # Étape 2: Normaliser
        sandbox_dir = None
        with st.spinner("2️⃣ Normalisation..."):
            try:
                sandbox_dir = normalize_client_to_sandbox(
                    str(selected_client_folder),
                    sandbox_root="output/sandbox"
                )
                st.success(f"✅ Normalisé vers : {sandbox_dir}")
            
            except Exception as e:
                st.error(f"❌ Erreur normalisation : {e}")
                return
        
        # Étape 3: Générer rapport
        with st.spinner("3️⃣ Génération rapport (RAG + DOCX)..."):
            try:
                # Utiliser RapportOrchestrator
                config = PipelineConfig(
                    client_path=str(selected_client_folder),
                    output_dir=str(output_path),
                    template_path="",  # Utiliser template par défaut
                    client_id=client_slug,
                    strict_mode=strict_mode
                )
                
                orchestrator = RapportOrchestrator(config)
                result = orchestrator.run()
                
                st.success("✅ Génération terminée !")
                
                # Récupérer les fichiers générés
                docx_path = output_path / f"{client_slug}_generated.docx"
                metrics_path = output_path / f"{client_slug}_metrics.json"
                debug_path = output_path / f"{client_slug}_debug.json"
                
            except Exception as e:
                st.error(f"❌ Erreur génération : {e}")
                st.code(traceback.format_exc())
                return
        
        # Étape 4: Validation
        validation_result = None
        with st.spinner("4️⃣ Validation..."):
            try:
                if metrics_path.exists():
                    validation_result = validate_report(
                        metrics_path,
                        debug_path if debug_path.exists() else None,
                        profile=ValidationProfile(profile.lower())
                    )
                    
                    # Sauvegarder validation.json
                    validation_path = output_path / f"{client_slug}_validation.json"
                    with open(validation_path, "w") as f:
                        json.dump(validation_result.to_dict(), f, indent=2, ensure_ascii=False)
                    
                    st.success("✅ Validation terminée !")
                else:
                    st.warning("⚠️ Pas de metrics.json trouvé, validation ignorée")
            
            except Exception as e:
                st.error(f"❌ Erreur validation : {e}")
        
        # Afficher résultats
        st.markdown("---")
        st.markdown("### 📊 Résultats")
        
        if validation_result:
            # Status
            status = validation_result.status
            
            if status == "GO":
                st.success(f"✅ **Statut : {status}** - Rapport production-ready")
            elif status == "NO_GO":
                st.error(f"❌ **Statut : {status}** - Rapport non validé")
            else:
                st.warning(f"⚠️ **Statut : {status}** - Brouillon")
            
            # Scores
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Coverage",
                    f"{validation_result.scores.get('required_coverage', 0)*100:.0f}%"
                )
            
            with col2:
                st.metric(
                    "Quality",
                    f"{validation_result.scores.get('quality_score', 0):.2f}"
                )
            
            with col3:
                st.metric(
                    "Confidence",
                    f"{validation_result.scores.get('avg_confidence', 0):.2f}"
                )
            
            # Raisons
            if validation_result.reasons:
                st.markdown("#### 📋 Raisons")
                for reason in validation_result.reasons:
                    st.write(f"- {reason}")
            
            # Actions recommandées
            if validation_result.actions:
                st.markdown("#### 💡 Actions recommandées")
                for action in validation_result.actions:
                    st.write(f"- {action}")
        
        # Downloads
        st.markdown("---")
        st.markdown("#### 📥 Téléchargements")
        
        cols = st.columns(4)
        
        with cols[0]:
            if docx_path.exists():
                with open(docx_path, "rb") as f:
                    st.download_button(
                        "📄 DOCX",
                        data=f,
                        file_name=docx_path.name,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )
        
        with cols[1]:
            if metrics_path.exists():
                with open(metrics_path, "rb") as f:
                    st.download_button(
                        "📊 Metrics",
                        data=f,
                        file_name=metrics_path.name,
                        mime="application/json",
                        use_container_width=True
                    )
        
        with cols[2]:
            if debug_path.exists():
                with open(debug_path, "rb") as f:
                    st.download_button(
                        "🐛 Debug",
                        data=f,
                        file_name=debug_path.name,
                        mime="application/json",
                        use_container_width=True
                    )
        
        with cols[3]:
            validation_path = output_path / f"{client_slug}_validation.json"
            if validation_path.exists():
                with open(validation_path, "rb") as f:
                    st.download_button(
                        "✅ Validation",
                        data=f,
                        file_name=validation_path.name,
                        mime="application/json",
                        use_container_width=True
                    )


def show_training_and_test_page():
    """Page principale avec 2 onglets."""
    st.title("🎓 Training & Test")
    st.markdown("**Piloter l'entraînement dataset et tester des clients depuis le navigateur**")
    
    # Tabs
    tab1, tab2 = st.tabs([
        "📚 Entraîner Dataset",
        "🧪 Test Client"
    ])
    
    with tab1:
        show_training_tab()
    
    with tab2:
        show_test_tab()


if __name__ == "__main__":
    show_training_and_test_page()
