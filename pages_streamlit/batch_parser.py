"""
Page Streamlit pour le Batch Parser RH-Pro
"""
import streamlit as st
from pathlib import Path
import json
import pandas as pd
from datetime import datetime
from src.rhpro.batch_runner import discover_sources, run_batch


def show_batch_parser_page():
    """Page principale du Batch Parser"""
    st.title("🔄 Batch Parser RH-Pro")
    st.markdown("Parser et valider plusieurs dossiers clients en batch")
    
    # Initialiser session state
    if "batch_discovered" not in st.session_state:
        st.session_state.batch_discovered = []
    if "batch_result" not in st.session_state:
        st.session_state.batch_result = None
    
    # Configuration
    st.subheader("1. Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Root directory
        default_root = str(Path.cwd() / "data" / "samples")
        root_dir = st.text_input(
            "Dossier racine",
            value=default_root,
            help="Dossier contenant les dossiers clients avec source.docx"
        )
        
        # Browse button (using tkinter if available)
        if st.button("📁 Browse dossier", key="browse_root"):
            try:
                import tkinter as tk
                from tkinter import filedialog
                
                root = tk.Tk()
                root.withdraw()
                root.wm_attributes('-topmost', 1)
                
                selected = filedialog.askdirectory(
                    title="Sélectionner le dossier racine",
                    initialdir=root_dir
                )
                
                if selected:
                    st.session_state.batch_root_dir = selected
                    st.rerun()
            except ImportError:
                st.warning("tkinter non disponible. Saisissez le chemin manuellement.")
        
        # Utiliser le dossier sélectionné si disponible
        if "batch_root_dir" in st.session_state:
            root_dir = st.session_state.batch_root_dir
        
        # Découverte
        if st.button("🔍 Découvrir les dossiers", key="discover"):
            if not Path(root_dir).exists():
                st.error(f"❌ Dossier introuvable: {root_dir}")
            else:
                with st.spinner("Découverte en cours..."):
                    try:
                        discovered = discover_sources(root_dir)
                        st.session_state.batch_discovered = discovered
                        
                        if discovered:
                            st.success(f"✅ {len(discovered)} dossier(s) découvert(s)")
                        else:
                            st.warning("⚠️ Aucun dossier contenant 'source.docx' trouvé")
                    except Exception as e:
                        st.error(f"❌ Erreur: {e}")
    
    with col2:
        # Ruleset
        default_ruleset = str(Path.cwd() / "config" / "rulesets" / "rhpro_v1.yaml")
        ruleset_path = st.text_input(
            "Ruleset YAML",
            value=default_ruleset,
            help="Configuration des règles de parsing"
        )
        
        # Profile override
        profile_override = st.selectbox(
            "Profil de production gate",
            options=["Auto-détection", "bilan_complet", "placement_suivi", "stage"],
            help="Forcer un profil ou laisser l'auto-détection"
        )
        
        if profile_override == "Auto-détection":
            profile_override = None
        
        # Output directory
        default_output = str(Path.cwd() / "out" / "batch" / datetime.now().strftime("%Y%m%d_%H%M%S"))
        output_dir = st.text_input(
            "Dossier de sortie",
            value=default_output,
            help="Où stocker les rapports générés"
        )
        
        # Options
        write_in_source = st.checkbox(
            "Écrire source_normalized.json dans chaque dossier client",
            value=False
        )
    
    # Liste des dossiers découverts
    if st.session_state.batch_discovered:
        st.subheader("2. Dossiers découverts")
        
        # Multiselect avec tous sélectionnés par défaut
        all_folders = [str(f.relative_to(root_dir)) for f in st.session_state.batch_discovered]
        selected_folders = st.multiselect(
            "Dossiers à parser",
            options=all_folders,
            default=all_folders,
            help="Sélectionnez les dossiers à traiter"
        )
        
        if not selected_folders:
            st.warning("⚠️ Aucun dossier sélectionné")
        else:
            st.info(f"📊 {len(selected_folders)} dossier(s) sélectionné(s)")
            
            # Bouton lancer batch
            if st.button("🚀 Lancer le batch", type="primary", key="run_batch"):
                if not Path(ruleset_path).exists():
                    st.error(f"❌ Ruleset introuvable: {ruleset_path}")
                else:
                    # Créer un sous-dossier temporaire avec seulement les dossiers sélectionnés
                    # (ou traiter directement root_dir et filtrer les résultats)
                    
                    with st.spinner("🔄 Parsing en cours... Cela peut prendre quelques minutes."):
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        try:
                            # Exécuter le batch
                            batch_result = run_batch(
                                root_dir=root_dir,
                                ruleset_path=ruleset_path,
                                output_dir=output_dir,
                                write_normalized_in_source=write_in_source,
                                gate_profile_override=profile_override
                            )
                            
                            # Filtrer les résultats selon la sélection
                            if len(selected_folders) < len(all_folders):
                                batch_result["results"] = [
                                    r for r in batch_result["results"]
                                    if str(Path(r["client_dir"]).relative_to(root_dir)) in selected_folders
                                ]
                                # Recalculer le summary
                                filtered_results = batch_result["results"]
                                successful = [r for r in filtered_results if r["status"] == "success"]
                                go_count = sum(1 for r in successful if r.get("gate_status") == "GO")
                                no_go_count = sum(1 for r in successful if r.get("gate_status") == "NO-GO")
                                
                                batch_result["summary"] = {
                                    "total_processed": len(filtered_results),
                                    "successful": len(successful),
                                    "errors": len([r for r in filtered_results if r["status"] == "error"]),
                                    "gate_go": go_count,
                                    "gate_no_go": no_go_count,
                                    "avg_coverage": round(
                                        sum(r.get("required_coverage_ratio", 0) for r in successful) / max(len(successful), 1),
                                        3
                                    )
                                }
                            
                            st.session_state.batch_result = batch_result
                            progress_bar.progress(100)
                            status_text.success("✅ Batch terminé!")
                            
                        except Exception as e:
                            st.error(f"❌ Erreur lors du batch: {e}")
                            import traceback
                            st.code(traceback.format_exc())
    
    # Résultats
    if st.session_state.batch_result:
        st.divider()
        st.subheader("3. Résultats")
        
        result = st.session_state.batch_result
        summary = result["summary"]
        
        # Métriques
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total", summary["total_processed"])
        with col2:
            st.metric("Succès", summary["successful"], delta_color="normal")
        with col3:
            st.metric("Erreurs", summary["errors"], delta_color="inverse")
        with col4:
            st.metric("Gate GO", summary["gate_go"], delta_color="normal")
        with col5:
            avg_cov = summary["avg_coverage"]
            st.metric("Coverage moyen", f"{avg_cov:.1%}")
        
        # Tableau détaillé
        st.subheader("Détails par client")
        
        # Préparer les données pour le tableau
        table_data = []
        for r in result["results"]:
            if r["status"] == "success":
                table_data.append({
                    "Client": r["client_name"],
                    "Profil": r.get("profile", "?"),
                    "Gate": r.get("gate_status", "?"),
                    "Coverage": f"{r.get('required_coverage_ratio', 0):.1%}",
                    "Sections manquantes": len(r.get("missing_required_sections", [])),
                    "Titres inconnus": r.get("unknown_titles_count", 0),
                    "Placeholders": r.get("placeholders_count", 0),
                    "Status": "✅"
                })
            else:
                table_data.append({
                    "Client": r["client_name"],
                    "Profil": "-",
                    "Gate": "-",
                    "Coverage": "-",
                    "Sections manquantes": "-",
                    "Titres inconnus": "-",
                    "Placeholders": "-",
                    "Status": f"❌ {r.get('error_type', 'Error')}"
                })
        
        # Afficher le tableau
        if table_data:
            df = pd.DataFrame(table_data)
            
            # Colorer selon le gate status
            def color_gate(val):
                if val == "GO":
                    return "background-color: #d4edda"
                elif val == "NO-GO":
                    return "background-color: #f8d7da"
                return ""
            
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )
        
        # Détails par client (expandeurs)
        st.subheader("Détails des raisons")
        
        for r in result["results"]:
            if r["status"] == "success":
                client = r["client_name"]
                gate_status = r.get("gate_status", "?")
                emoji = "✅" if gate_status == "GO" else "⚠️"
                
                with st.expander(f"{emoji} {client} — {gate_status}"):
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        st.markdown("**Profil**")
                        st.code(r.get("profile", "?"))
                        
                        st.markdown("**Signaux détectés**")
                        signals = r.get("signals", {})
                        if signals:
                            st.json(signals)
                        else:
                            st.text("N/A")
                    
                    with col_b:
                        st.markdown("**Raisons du statut**")
                        reasons = r.get("reasons", [])
                        if reasons:
                            for reason in reasons:
                                st.text(f"• {reason}")
                        else:
                            st.text("N/A")
                        
                        st.markdown("**Sections manquantes**")
                        missing = r.get("missing_required_sections", [])
                        if missing:
                            st.text(", ".join(missing[:5]))
                            if len(missing) > 5:
                                st.text(f"... et {len(missing) - 5} autres")
                        else:
                            st.text("✓ Aucune")
        
        # Téléchargements
        st.divider()
        st.subheader("4. Téléchargements")
        
        output_path = Path(result["output_dir"]) if "output_dir" in result else Path(output_dir)
        
        col_dl1, col_dl2 = st.columns(2)
        
        # JSON
        json_file = output_path / "batch_report.json"
        if json_file.exists():
            with col_dl1:
                with open(json_file, "rb") as f:
                    st.download_button(
                        "📄 Télécharger batch_report.json",
                        data=f.read(),
                        file_name="batch_report.json",
                        mime="application/json",
                        use_container_width=True
                    )
        
        # Markdown
        md_file = output_path / "batch_report.md"
        if md_file.exists():
            with col_dl2:
                with open(md_file, "rb") as f:
                    st.download_button(
                        "📝 Télécharger batch_report.md",
                        data=f.read(),
                        file_name="batch_report.md",
                        mime="text/markdown",
                        use_container_width=True
                    )
        
        st.info(f"📁 Tous les fichiers sont dans: {output_path}")


if __name__ == "__main__":
    show_batch_parser_page()
