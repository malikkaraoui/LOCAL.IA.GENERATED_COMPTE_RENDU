"""
Page Streamlit pour l'affichage et l'analyse des résultats de validation batch.

Fonctionnalités :
- Affichage status (GO/NO_GO/DRAFT) avec tooltips
- Filtres (afficher uniquement NO_GO, avec GOLD, etc.)
- Export batch_report.json et CSV
- Vue détaillée par client (Pourquoi NO_GO, Actions recommandées)
"""
import streamlit as st
from pathlib import Path
import json
import pandas as pd
from typing import Dict, Any, List, Optional
import sys

# Ajouter src/ au path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rhpro.batch_report import (
    load_batch_report,
    filter_batch_report,
    print_batch_summary,
)


def show_batch_validation_page():
    """Page d'affichage des résultats de validation batch."""
    st.title("📊 Validation Batch - RH-Pro")
    st.markdown("Analyse et visualisation des résultats de validation")
    
    # Sélection du batch report
    st.subheader("1. Charger un Batch Report")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        report_path = st.text_input(
            "Chemin vers batch_report.json",
            value="output/batch_report.json",
            help="Fichier batch_report.json généré après validation"
        )
    
    with col2:
        if st.button("📂 Browse", key="browse_report"):
            try:
                import tkinter as tk
                from tkinter import filedialog
                
                root = tk.Tk()
                root.withdraw()
                root.wm_attributes('-topmost', 1)
                
                selected = filedialog.askopenfilename(
                    title="Sélectionner batch_report.json",
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
                )
                
                if selected:
                    st.session_state.batch_report_path = selected
                    st.rerun()
            except ImportError:
                st.warning("tkinter non disponible")
    
    # Utiliser le chemin sélectionné si disponible
    if "batch_report_path" in st.session_state:
        report_path = st.session_state.batch_report_path
    
    # Charger le rapport
    if not Path(report_path).exists():
        st.warning(f"⚠️ Fichier introuvable: {report_path}")
        st.info("💡 Générez d'abord un batch avec validation pour créer ce fichier")
        return
    
    try:
        report = load_batch_report(Path(report_path))
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement: {e}")
        return
    
    # Résumé global
    st.subheader("2. Résumé Global")
    
    summary = report.get("summary", {})
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total", summary.get("total", 0))
    
    with col2:
        go_count = summary.get("go_count", 0)
        go_rate = summary.get("go_rate", 0)
        st.metric("✅ GO", go_count, f"{go_rate:.1f}%")
    
    with col3:
        no_go_count = summary.get("no_go_count", 0)
        st.metric("❌ NO_GO", no_go_count)
    
    with col4:
        draft_count = summary.get("draft_count", 0)
        st.metric("📝 DRAFT", draft_count)
    
    with col5:
        gold_count = summary.get("gold_detected_count", 0)
        gold_rate = summary.get("gold_rate", 0)
        st.metric("🏆 GOLD", gold_count, f"{gold_rate:.1f}%")
    
    # Top raisons d'échec
    if summary.get("top_failure_reasons"):
        st.markdown("### 🔍 Top Raisons d'Échec")
        
        reasons_data = []
        for reason in summary["top_failure_reasons"][:5]:
            reasons_data.append({
                "Raison": reason["reason"],
                "Occurrences": reason["count"],
            })
        
        df_reasons = pd.DataFrame(reasons_data)
        st.dataframe(df_reasons, use_container_width=True, hide_index=True)
    
    # Filtres
    st.subheader("3. Filtrer les Résultats")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Statut",
            options=["Tous", "GO", "NO_GO", "DRAFT"],
            key="status_filter"
        )
    
    with col2:
        gold_filter = st.checkbox(
            "Uniquement avec GOLD",
            value=False,
            key="gold_filter"
        )
    
    with col3:
        search_query = st.text_input(
            "Rechercher client",
            placeholder="Nom du client...",
            key="search_filter"
        )
    
    # Appliquer les filtres
    clients = report.get("clients", [])
    
    if status_filter != "Tous":
        clients = [c for c in clients if c["status"] == status_filter]
    
    if gold_filter:
        clients = [c for c in clients if c.get("gold_detected", False)]
    
    if search_query:
        clients = [c for c in clients if search_query.lower() in c["client_name"].lower()]
    
    st.info(f"📋 {len(clients)} client(s) affiché(s)")
    
    # Boutons d'export
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Télécharger batch_report.json", use_container_width=True):
            report_json = json.dumps(report, indent=2, ensure_ascii=False)
            st.download_button(
                label="💾 Enregistrer JSON",
                data=report_json,
                file_name=f"batch_report_{report['batch_name']}.json",
                mime="application/json"
            )
    
    with col2:
        csv_path = Path(report_path).parent / "batch_report.csv"
        if csv_path.exists():
            with open(csv_path, 'r', encoding='utf-8') as f:
                csv_data = f.read()
            
            st.download_button(
                label="📊 Télécharger CSV",
                data=csv_data,
                file_name=f"batch_report_{report['batch_name']}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    # Table des clients
    st.subheader("4. Résultats par Client")
    
    if not clients:
        st.warning("⚠️ Aucun client à afficher avec les filtres actuels")
        return
    
    # Créer le DataFrame pour la table
    table_data = []
    for client in clients:
        # Icône status
        status = client["status"]
        if status == "GO":
            status_icon = "✅"
        elif status == "NO_GO":
            status_icon = "❌"
        else:
            status_icon = "📝"
        
        table_data.append({
            "Status": f"{status_icon} {status}",
            "Client": client["client_name"],
            "Profile": client["profile"],
            "Quality": f"{client['scores'].get('quality_score', 0):.2f}",
            "Coverage": f"{client['scores'].get('required_coverage', 0) * 100:.1f}%",
            "Sources": client["sources_count"],
            "GOLD": "🏆" if client.get("gold_detected") else "—",
            "Champs Critiques": len(client.get("missing_critical_fields", [])),
        })
    
    df = pd.DataFrame(table_data)
    
    # Afficher avec sélection
    selected_indices = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row"
    )
    
    # Vue détaillée du client sélectionné
    if selected_indices and len(selected_indices["selection"]["rows"]) > 0:
        selected_idx = selected_indices["selection"]["rows"][0]
        selected_client = clients[selected_idx]
        
        show_client_detail_view(selected_client)


def show_client_detail_view(client: Dict[str, Any]):
    """Affiche la vue détaillée d'un client avec diagnostics et actions."""
    st.markdown("---")
    st.subheader(f"📋 Détails : {client['client_name']}")
    
    # Statut et scores
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status = client["status"]
        if status == "GO":
            st.success(f"✅ {status}")
        elif status == "NO_GO":
            st.error(f"❌ {status}")
        else:
            st.warning(f"📝 {status}")
    
    with col2:
        st.metric("Quality Score", f"{client['scores'].get('quality_score', 0):.2f}")
    
    with col3:
        st.metric("Coverage", f"{client['scores'].get('required_coverage', 0) * 100:.1f}%")
    
    with col4:
        st.metric("Confiance", f"{client['scores'].get('avg_confidence', 0):.2f}")
    
    # Pourquoi NO_GO / DRAFT ?
    if client["status"] in ["NO_GO", "DRAFT"]:
        st.markdown("### ❌ Pourquoi ce statut ?")
        
        reasons = client.get("reasons", [])
        if reasons:
            for i, reason in enumerate(reasons, 1):
                # Décomposer la raison
                if ":" in reason:
                    reason_type, reason_detail = reason.split(":", 1)
                    st.markdown(f"{i}. **{reason_type}** : {reason_detail}")
                else:
                    st.markdown(f"{i}. {reason}")
        else:
            st.info("Aucune raison spécifique fournie")
        
        # Champs critiques manquants
        missing_critical = client.get("missing_critical_fields", [])
        if missing_critical:
            st.markdown("#### 🔴 Champs Critiques Manquants")
            for field in missing_critical:
                st.markdown(f"- `{field}`")
    
    # Actions recommandées
    st.markdown("### 🔧 Actions Recommandées")
    
    actions = client.get("actions", [])
    if actions:
        for i, action in enumerate(actions, 1):
            # Interpréter l'action
            action_icon = "📝"
            if "add_sources" in action:
                action_icon = "📄"
            elif "identity" in action:
                action_icon = "👤"
            elif "gold" in action:
                action_icon = "🏆"
            elif "verify" in action:
                action_icon = "🔍"
            
            st.markdown(f"{i}. {action_icon} **{action}**")
            
            # Ajouter des suggestions contextuelles
            if action == "add_identity_sources":
                st.info("💡 Ajoutez des documents contenant l'identité (CV, pièce d'identité, etc.)")
            elif action == "add_rag_sources":
                st.info("💡 Ajoutez des sources au dossier client (minimum 1 document)")
            elif action == "select_gold_candidate":
                st.info("💡 Marquez un document comme GOLD de référence")
            elif action == "improve_source_quality":
                st.info("💡 Vérifiez la qualité et la pertinence des sources")
    else:
        st.success("✅ Aucune action requise")
    
    # Sources utilisées
    st.markdown("### 📚 Sources Utilisées")
    
    sources_by_type = client.get("sources_by_type", {})
    if sources_by_type:
        cols = st.columns(len(sources_by_type))
        for idx, (ext, count) in enumerate(sources_by_type.items()):
            with cols[idx]:
                st.metric(ext.upper(), count)
    else:
        st.warning("⚠️ Aucune source détectée")
    
    # Liens vers les outputs
    st.markdown("### 📂 Outputs Générés")
    
    outputs = client.get("outputs", {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        if outputs.get("generated_docx"):
            docx_path = outputs["generated_docx"]
            if Path(docx_path).exists():
                st.success(f"✅ DOCX : `{Path(docx_path).name}`")
                if st.button("📄 Ouvrir DOCX", key=f"open_docx_{client['client_name']}"):
                    import subprocess
                    subprocess.run(["open", docx_path], check=False)
            else:
                st.warning("⚠️ DOCX non trouvé")
        
        if outputs.get("metrics_json"):
            metrics_path = outputs["metrics_json"]
            if Path(metrics_path).exists():
                st.success(f"✅ Metrics : `{Path(metrics_path).name}`")
    
    with col2:
        if outputs.get("debug_json"):
            debug_path = outputs["debug_json"]
            if Path(debug_path).exists():
                st.success(f"✅ Debug : `{Path(debug_path).name}`")
                
                # Bouton pour afficher debug.json
                if st.button("🔍 Voir Debug JSON", key=f"view_debug_{client['client_name']}"):
                    with open(debug_path, 'r', encoding='utf-8') as f:
                        debug_data = json.load(f)
                    
                    with st.expander("📄 debug.json", expanded=True):
                        st.json(debug_data)
        
        if outputs.get("validation_json"):
            validation_path = outputs["validation_json"]
            if Path(validation_path).exists():
                st.success(f"✅ Validation : `{Path(validation_path).name}`")
    
    # GOLD référence
    if client.get("gold_detected") and client.get("gold_path"):
        st.markdown("### 🏆 GOLD Référence")
        gold_path = client["gold_path"]
        st.info(f"📄 {Path(gold_path).name}")
        
        if st.button("📖 Ouvrir GOLD", key=f"open_gold_{client['client_name']}"):
            import subprocess
            subprocess.run(["open", gold_path], check=False)


def main():
    """Point d'entrée pour test standalone."""
    show_batch_validation_page()


if __name__ == "__main__":
    main()
