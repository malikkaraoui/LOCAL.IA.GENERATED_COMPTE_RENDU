"""
Page Streamlit pour génération de rapport individuel par nom de client
"""
import streamlit as st
from pathlib import Path
import sys

# Ajouter src/ au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rhpro.client_finder import (
    find_client_folders,
    find_client_folder,
    format_search_results,
    discover_client_documents,
    discover_client_documents_recursive,
    select_best_source_docx
)


def show_client_report_generator_page():
    """Page de génération de rapport pour un client spécifique"""
    st.title("📝 Générateur de rapport individuel")
    st.markdown("Rechercher un client par nom et générer son rapport")
    
    # Initialiser session state
    if "client_search_results" not in st.session_state:
        st.session_state.client_search_results = []
    if "selected_client_path" not in st.session_state:
        st.session_state.selected_client_path = None
    if "client_documents" not in st.session_state:
        st.session_state.client_documents = None
    if "scan_max_files" not in st.session_state:
        st.session_state.scan_max_files = 5000
    if "exclude_devis_dirs" not in st.session_state:
        st.session_state.exclude_devis_dirs = True
    if "exclude_devis_files" not in st.session_state:
        st.session_state.exclude_devis_files = True
    if "auto_select_docx" not in st.session_state:
        st.session_state.auto_select_docx = True
    
    # Configuration
    st.subheader("1. Dataset RH-Pro")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Root directory
        default_root = st.text_input(
            "Dossier racine du dataset",
            value="",
            placeholder="/Users/malik/Documents/RH PRO BASE DONNEE/3. TERMINER/",
            help="Dossier contenant tous les dossiers clients (1 dossier = 1 client nom/prénom)"
        )
        
        # Browse button
        if st.button("📁 Browse", key="browse_dataset"):
            try:
                import tkinter as tk
                from tkinter import filedialog
                
                root = tk.Tk()
                root.withdraw()
                root.wm_attributes('-topmost', 1)
                
                selected = filedialog.askdirectory(
                    title="Sélectionner le dossier dataset RH-Pro",
                    initialdir=default_root or str(Path.home())
                )
                
                if selected:
                    st.session_state.dataset_root = selected
                    st.rerun()
            except ImportError:
                st.warning("tkinter non disponible. Saisissez le chemin manuellement.")
        
        # Utiliser le dossier sélectionné si disponible
        if "dataset_root" in st.session_state:
            dataset_root = st.session_state.dataset_root
        else:
            dataset_root = default_root
    
    with col2:
        # Report type
        report_type = st.selectbox(
            "Type de rapport",
            options=["orientation", "final"],
            help="Type de rapport à générer"
        )
    
    # Recherche client
    if dataset_root and Path(dataset_root).exists():
        st.divider()
        st.subheader("2. Recherche client")
        
        col_search1, col_search2 = st.columns([3, 1])
        
        with col_search1:
            search_query = st.text_input(
                "Nom du client",
                placeholder="ex: ARIFI, arifi elodie, KARAOUI",
                help="Recherche tolérante (accents, majuscules)"
            )
        
        with col_search2:
            search_clicked = st.button("🔍 Rechercher", type="primary", key="search_client")
        
        # Exécuter la recherche
        if search_clicked and search_query:
            with st.spinner("Recherche en cours..."):
                try:
                    results = find_client_folders(dataset_root, search_query, min_score=0.2)
                    st.session_state.client_search_results = results
                    
                    if results:
                        st.success(f"✅ {len(results)} résultat(s) trouvé(s)")
                    else:
                        st.warning("⚠️ Aucun résultat")
                except Exception as e:
                    st.error(f"❌ Erreur: {e}")
        
        # Afficher les résultats
        if st.session_state.client_search_results:
            st.subheader("Résultats de recherche")
            
            # Préparer les options pour selectbox
            options_dict = {}
            for i, result in enumerate(st.session_state.client_search_results[:20], 1):
                score = result.get('score', 0.0)
                name = result['name']
                
                # Indicateurs
                indicators = []
                if result.get('has_docx'):
                    indicators.append('📄')
                if result.get('has_pdf'):
                    indicators.append('📕')
                if result.get('has_audio'):
                    indicators.append('🎤')
                
                indicators_str = ''.join(indicators) if indicators else '📁'
                
                display_name = f"{indicators_str} [{score:.2f}] {name}"
                options_dict[display_name] = result['path']
            
            # Selectbox
            selected_display = st.selectbox(
                "Sélectionner un client",
                options=list(options_dict.keys()),
                help="Choisir le dossier client pour générer le rapport"
            )
            
            if selected_display:
                selected_path = options_dict[selected_display]
                st.session_state.selected_client_path = selected_path
                
                # === Section Scan Documents avec contrôles ===
                with st.expander("📂 Documents trouvés dans ce dossier", expanded=True):
                    # Contrôles de scan simplifiés (scan récursif complet automatique)
                    col_ctrl1, col_ctrl2 = st.columns([3, 1])
                    
                    with col_ctrl1:
                        max_files = st.number_input(
                            "Max fichiers scannés",
                            min_value=100,
                            max_value=20000,
                            value=st.session_state.scan_max_files,
                            step=500,
                            key="input_max_files",
                            help="Limite pour éviter de freezer l'UI sur gros dossiers"
                        )
                        st.session_state.scan_max_files = max_files
                    
                    with col_ctrl2:
                        st.write("")  # Spacer
                        st.write("")  # Spacer
                        rescan_clicked = st.button("🔄 Rescanner", help="Forcer un nouveau scan (clear cache)")
                    
                    # Info: Scan automatique complet
                    st.info("🔍 Scan récursif complet automatique : tout le dossier client est scanné (sauf exclusions ci-dessous)")
                    
                    # Options d'exclusion
                    col_excl1, col_excl2 = st.columns(2)
                    
                    with col_excl1:
                        exclude_devis_dirs = st.checkbox(
                            "🚫 Exclure dossier 'Devis'",
                            value=st.session_state.exclude_devis_dirs,
                            key="checkbox_exclude_devis_dirs",
                            help="Exclure automatiquement les dossiers contenant 'devis' (ex: 02 Devis, Devis RH-Pro, etc.)"
                        )
                        st.session_state.exclude_devis_dirs = exclude_devis_dirs
                    
                    with col_excl2:
                        exclude_devis_files = st.checkbox(
                            "🚫 Exclure fichiers 'Devis'",
                            value=st.session_state.exclude_devis_files,
                            key="checkbox_exclude_devis_files",
                            help="Exclure automatiquement les fichiers contenant 'devis' dans le nom"
                        )
                        st.session_state.exclude_devis_files = exclude_devis_files
                    
                    # Cache avec fonction dédiée (scan récursif complet automatique)
                    @st.cache_data(show_spinner="Scan récursif complet en cours...", ttl=300)
                    def _cached_scan(path_str: str, max_f: int, excl_dirs: bool, excl_files: bool):
                        """Scan récursif complet avec cache Streamlit (profondeur illimitée)"""
                        exclude_dir_kw = ['devis'] if excl_dirs else []
                        exclude_file_kw = ['devis'] if excl_files else []
                        return discover_client_documents_recursive(
                            Path(path_str),
                            max_depth=10,  # Profondeur élevée pour scan complet
                            include_subfolders=True,  # Toujours récursif
                            max_files=max_f,
                            exclude_dir_keywords=exclude_dir_kw,
                            exclude_file_keywords=exclude_file_kw
                        )
                    
                    # Clear cache si rescan demandé
                    if rescan_clicked:
                        _cached_scan.clear()
                        st.rerun()
                    
                    # Découvrir les documents avec nouveau scan
                    try:
                        result = _cached_scan(
                            str(selected_path),
                            max_files,
                            exclude_devis_dirs,
                            exclude_devis_files
                        )
                        
                        docs = result['files']
                        stats_by_type = result['stats_by_type']
                        stats_by_subfolder = result['stats_by_subfolder']
                        total_files = result['total_files']
                        truncated = result['truncated']
                        excluded_dirs = result.get('excluded_dirs', [])
                        excluded_files_count = result.get('excluded_files_count', 0)
                        
                        st.session_state.client_documents = docs
                        
                        # Info sur les exclusions
                        if excluded_dirs or excluded_files_count > 0:
                            excl_info = []
                            if excluded_dirs:
                                excl_info.append(f"{len(excluded_dirs)} dossier(s) exclu(s)")
                            if excluded_files_count > 0:
                                excl_info.append(f"{excluded_files_count} fichier(s) exclu(s)")
                            st.info(f"🚫 Exclusions: {', '.join(excl_info)}")
                        
                        # Warning si truncated
                        if truncated:
                            st.warning(f"⚠️ Scan limité à {max_files} fichiers. Augmenter 'Max fichiers' ou réduire profondeur.")
                        
                        # Métriques globales
                        st.caption(f"**Total : {total_files} fichier(s) trouvé(s)**")
                        
                        # Affichage par type de fichier
                        col_doc1, col_doc2, col_doc3, col_doc4, col_doc5 = st.columns(5)
                        
                        with col_doc1:
                            st.metric("DOCX", len(docs['docx']))
                            if docs['docx']:
                                for docx in docs['docx'][:3]:
                                    st.text(f"• {docx.name}")
                                if len(docs['docx']) > 3:
                                    st.caption(f"  ... +{len(docs['docx']) - 3}")
                        
                        with col_doc2:
                            st.metric("PDF", len(docs['pdf']))
                            if docs['pdf']:
                                for pdf in docs['pdf'][:3]:
                                    st.text(f"• {pdf.name}")
                                if len(docs['pdf']) > 3:
                                    st.caption(f"  ... +{len(docs['pdf']) - 3}")
                        
                        with col_doc3:
                            st.metric("TXT", len(docs['txt']))
                            if docs['txt']:
                                for txt in docs['txt'][:3]:
                                    st.text(f"• {txt.name}")
                                if len(docs['txt']) > 3:
                                    st.caption(f"  ... +{len(docs['txt']) - 3}")
                        
                        with col_doc4:
                            st.metric("MSG", len(docs.get('msg', [])))
                            if docs.get('msg'):
                                for msg in docs['msg'][:3]:
                                    st.text(f"• {msg.name}")
                                if len(docs['msg']) > 3:
                                    st.caption(f"  ... +{len(docs['msg']) - 3}")
                        
                        with col_doc5:
                            st.metric("Audio", len(docs['audio']))
                            if docs['audio']:
                                for audio in docs['audio'][:3]:
                                    st.text(f"• {audio.name}")
                                if len(docs['audio']) > 3:
                                    st.caption(f"  ... +{len(docs['audio']) - 3}")
                        
                        # Stats par sous-dossier (affichage automatique)
                        if stats_by_subfolder and len(stats_by_subfolder) > 1:
                            st.divider()
                            st.caption("**Répartition par sous-dossier (top 5) :**")
                            
                            for i, (subfolder, type_counts) in enumerate(list(stats_by_subfolder.items())[:5], 1):
                                total_in_folder = sum(type_counts.values())
                                types_str = ", ".join([f"{count} {ftype}" for ftype, count in type_counts.items()])
                                st.text(f"{i}. {subfolder}: {total_in_folder} fichier(s) ({types_str})")
                    
                    except Exception as e:
                        st.error(f"Erreur lors de la découverte des documents: {e}")
                        import traceback
                        st.code(traceback.format_exc())
    
    elif dataset_root:
        st.warning(f"⚠️ Le dossier n'existe pas: {dataset_root}")
    
    # Génération du rapport
    if st.session_state.selected_client_path and st.session_state.client_documents:
        st.divider()
        st.subheader("3. Génération du rapport")
        
        client_path = st.session_state.selected_client_path
        docs = st.session_state.client_documents
        
        st.info(f"📁 Client sélectionné : **{client_path.name}**")
        
        # Sélection du document source
        selected_docx = None
        auto_select_mode = "NONE"
        
        if len(docs['docx']) == 0:
            st.error("❌ Aucun fichier DOCX trouvé dans ce dossier")
        elif len(docs['docx']) == 1:
            selected_docx = docs['docx'][0]
            st.text(f"📄 Document source : {selected_docx.name}")
        else:
            # Plusieurs DOCX : proposer AUTO ou MANUEL
            docx_selection_mode = st.radio(
                "Mode de sélection du DOCX source",
                options=["AUTO (recommandé)", "MANUEL"],
                horizontal=True,
                help="AUTO sélectionne automatiquement le meilleur document RH-Pro (bilan, évaluation, rapport) en excluant les documents administratifs (contrat, devis, etc.)"
            )
            
            if docx_selection_mode == "AUTO (recommandé)":
                # Sélection AUTO
                best_docx, auto_select_mode = select_best_source_docx(docs['docx'])
                
                if best_docx:
                    selected_docx = best_docx
                    mode_emoji = "🎯" if auto_select_mode == "AUTO_PRIORITY" else "⚠️"
                    st.success(f"{mode_emoji} AUTO a sélectionné : **{selected_docx.name}** ({auto_select_mode})")
                    
                    # Afficher les alternatives
                    with st.expander("Voir les autres DOCX disponibles"):
                        for doc in docs['docx']:
                            emoji = "✅" if doc == selected_docx else "⚪"
                            st.text(f"{emoji} {doc.name}")
                else:
                    st.warning("⚠️ AUTO n'a trouvé aucun DOCX valide. Basculer en mode MANUEL.")
                    docx_selection_mode = "MANUEL"
            
            if docx_selection_mode == "MANUEL":
                # Sélection manuelle
                selected_docx_name = st.selectbox(
                    "Document DOCX source",
                    options=[d.name for d in docs['docx']],
                    help="Choisir le document à parser"
                )
                selected_docx = [d for d in docs['docx'] if d.name == selected_docx_name][0]
                auto_select_mode = "MANUAL"
        
        if selected_docx:
            # Options de génération
            col_opt1, col_opt2 = st.columns(2)
            
            with col_opt1:
                gate_profile = st.selectbox(
                    "Profil production gate",
                    options=["Auto-détection", "bilan_complet", "placement_suivi", "stage"]
                )
                if gate_profile == "Auto-détection":
                    gate_profile = None
            
            with col_opt2:
                output_format = st.multiselect(
                    "Formats de sortie",
                    options=["Normalized JSON", "Report JSON", "Markdown", "CSV summary"],
                    default=["Normalized JSON", "Report JSON"]
                )
            
            # Bouton génération
            if st.button("🚀 Générer le rapport", type="primary", key="generate_report"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    status_text.text("📄 Parsing du document...")
                    progress_bar.progress(30)
                    
                    # Import de la pipeline
                    from rhpro.parse_bilan import parse_bilan_docx_to_normalized
                    
                    # Ruleset
                    ruleset_path = Path.cwd() / "config" / "rulesets" / "rhpro_v1.yaml"
                    
                    # Parser
                    result = parse_bilan_docx_to_normalized(
                        str(selected_docx),
                        str(ruleset_path),
                        gate_profile_override=gate_profile
                    )
                    
                    progress_bar.progress(70)
                    status_text.text("✅ Parsing terminé, génération des sorties...")
                    
                    normalized = result["normalized"]
                    report = result["report"]
                    
                    # Enrichir le report avec les infos de sélection
                    if "diagnostic" not in report:
                        report["diagnostic"] = {}
                    report["diagnostic"]["source_docx_selected"] = str(selected_docx)
                    report["diagnostic"]["source_docx_mode"] = auto_select_mode
                    report["diagnostic"]["rag_sources_count"] = {
                        "docx": len(docs['docx']),
                        "pdf": len(docs['pdf']),
                        "txt": len(docs['txt']),
                        "msg": len(docs.get('msg', [])),
                        "audio": len(docs['audio'])
                    }
                    if 'excluded_dirs' in result:
                        report["diagnostic"]["excluded_dirs"] = result['excluded_dirs']
                    if 'excluded_files_count' in result:
                        report["diagnostic"]["excluded_files_count"] = result['excluded_files_count']
                    
                    # Préparer dossier de sortie
                    output_dir = Path.cwd() / "out" / "individual" / client_path.name
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Écrire les fichiers
                    import json
                    
                    if "Normalized JSON" in output_format:
                        with open(output_dir / "normalized.json", "w", encoding="utf-8") as f:
                            json.dump(normalized, f, ensure_ascii=False, indent=2)
                    
                    if "Report JSON" in output_format:
                        with open(output_dir / "report.json", "w", encoding="utf-8") as f:
                            json.dump(report, f, ensure_ascii=False, indent=2)
                    
                    # Extraire gate (nécessaire pour l'affichage des résultats)
                    gate = report.get("production_gate", {})
                    
                    if "Markdown" in output_format:
                        # Générer un markdown simple
                        md_lines = []
                        md_lines.append(f"# Rapport - {client_path.name}\n")
                        md_lines.append(f"**Document**: {selected_docx.name}\n")
                        md_lines.append(f"**Report type**: {report_type}\n\n")
                        
                        md_lines.append(f"## Production Gate\n")
                        md_lines.append(f"- **Status**: {gate.get('status', 'UNKNOWN')}\n")
                        md_lines.append(f"- **Profile**: {gate.get('profile', 'unknown')}\n")
                        md_lines.append(f"- **Coverage**: {report.get('required_coverage_ratio', 0):.1%}\n\n")
                        
                        with open(output_dir / "report.md", "w", encoding="utf-8") as f:
                            f.write("".join(md_lines))
                    
                    progress_bar.progress(100)
                    status_text.success("✅ Rapport généré avec succès!")
                    
                    # Afficher les résultats
                    st.divider()
                    st.subheader("📊 Résultats")
                    
                    col_res1, col_res2, col_res3, col_res4 = st.columns(4)
                    
                    with col_res1:
                        gate_status = gate.get('status', 'UNKNOWN')
                        emoji = "✅" if gate_status == "GO" else "⚠️"
                        st.metric("Gate Status", f"{emoji} {gate_status}")
                    
                    with col_res2:
                        profile = gate.get('profile', 'unknown')
                        st.metric("Profil", profile)
                    
                    with col_res3:
                        coverage = report.get('required_coverage_ratio', 0)
                        st.metric("Coverage", f"{coverage:.1%}")
                    
                    with col_res4:
                        missing = len(gate.get('missing_required_effective', []))
                        st.metric("Sections manquantes", missing)
                    
                    # Fichiers générés
                    st.info(f"📁 Fichiers générés dans : `{output_dir}`")
                    
                    # Téléchargements
                    st.subheader("📥 Téléchargements")
                    
                    dl_cols = st.columns(len(output_format))
                    
                    for i, fmt in enumerate(output_format):
                        if fmt == "Normalized JSON":
                            file_path = output_dir / "normalized.json"
                            if file_path.exists():
                                with dl_cols[i]:
                                    with open(file_path, "rb") as f:
                                        st.download_button(
                                            "📄 normalized.json",
                                            data=f.read(),
                                            file_name="normalized.json",
                                            mime="application/json"
                                        )
                        
                        elif fmt == "Report JSON":
                            file_path = output_dir / "report.json"
                            if file_path.exists():
                                with dl_cols[i]:
                                    with open(file_path, "rb") as f:
                                        st.download_button(
                                            "📊 report.json",
                                            data=f.read(),
                                            file_name="report.json",
                                            mime="application/json"
                                        )
                        
                        elif fmt == "Markdown":
                            file_path = output_dir / "report.md"
                            if file_path.exists():
                                with dl_cols[i]:
                                    with open(file_path, "rb") as f:
                                        st.download_button(
                                            "📝 report.md",
                                            data=f.read(),
                                            file_name="report.md",
                                            mime="text/markdown"
                                        )
                
                except Exception as e:
                    st.error(f"❌ Erreur lors de la génération: {e}")
                    import traceback
                    st.code(traceback.format_exc())


if __name__ == "__main__":
    show_client_report_generator_page()
