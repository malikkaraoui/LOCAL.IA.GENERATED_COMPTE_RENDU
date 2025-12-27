"""
Page Streamlit pour l'entraînement du pipeline RH-Pro.

Permet de :
1. Browse pour sélectionner DATASET → BATCH → Client
2. Scanner et analyser un dossier client
3. Normaliser en sandbox (mode safe)
4. Lancer RAG + génération DOCX
"""

import streamlit as st
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import json

# Ajouter le projet au path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.rhpro.client_scanner import scan_client_folder, format_scan_report
from src.rhpro.client_normalizer import (
    normalize_client_to_sandbox,
    normalize_batch_to_sandbox,
    format_normalization_report,
)
from src.rhpro.client_finder import find_client_folders


def browse_directory(label: str, help_text: str = "") -> Optional[str]:
    """
    Permet de sélectionner un dossier via tkinter ou saisie manuelle.
    
    Args:
        label: Label pour le widget
        help_text: Texte d'aide
        
    Returns:
        Chemin du dossier ou None
    """
    col1, col2 = st.columns([3, 1])
    
    with col1:
        path_input = st.text_input(
            label,
            value=st.session_state.get(f"path_{label}", ""),
            help=help_text,
            key=f"input_{label}",
        )
    
    with col2:
        st.write("")  # Spacer
        st.write("")  # Spacer
        if st.button("📁 Browse", key=f"browse_{label}"):
            try:
                import tkinter as tk
                from tkinter import filedialog
                
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                
                folder_path = filedialog.askdirectory(
                    title=f"Sélectionner : {label}",
                    initialdir=path_input if path_input else None,
                )
                
                root.destroy()
                
                if folder_path:
                    st.session_state[f"path_{label}"] = folder_path
                    st.rerun()
            
            except Exception as e:
                st.error(f"Erreur browse : {e}")
    
    return path_input if path_input else None


def show_training_page():
    """
    Page principale d'entraînement.
    """
    st.title("🎓 Entraînement Pipeline RH-Pro")
    st.markdown("---")
    
    # Mode sélection
    mode = st.radio(
        "Mode de travail",
        options=["🔍 Analyser un client", "📦 Batch (plusieurs clients)", "⚙️ Configuration avancée"],
        horizontal=True,
    )
    
    st.markdown("---")
    
    if mode == "🔍 Analyser un client":
        show_single_client_mode()
    elif mode == "📦 Batch (plusieurs clients)":
        show_batch_mode()
    else:
        show_advanced_config()


def show_single_client_mode():
    """
    Mode analyse d'un seul client.
    """
    st.subheader("🔍 Analyse Client Individuel")
    
    # Browse dataset
    dataset_root = browse_directory(
        "Dataset racine",
        "Dossier contenant les sous-dossiers clients (structure NOM Prénom)"
    )
    
    if not dataset_root or not Path(dataset_root).exists():
        st.warning("⚠️ Veuillez sélectionner un dataset valide")
        return
    
    st.success(f"✅ Dataset : `{dataset_root}`")
    
    # Recherche client
    st.markdown("### 🔎 Recherche Client")
    
    search_query = st.text_input(
        "Nom du client (recherche floue)",
        placeholder="Ex: Karaoui, ARIFI, client",
        help="Recherche insensible à la casse et aux accents"
    )
    
    if search_query:
        try:
            # Recherche floue
            matches = find_client_folders(
                dataset_root,
                search_query,
                min_score=0.3,
                max_results=10,
            )
            
            if matches:
                st.info(f"💡 {len(matches)} résultat(s) trouvé(s)")
                
                # Selectbox avec scores
                options = [
                    f"{m['folder_name']} (score: {m['score']:.2f})"
                    for m in matches
                ]
                
                selected_option = st.selectbox(
                    "Sélectionner le client",
                    options=options,
                    key="client_select",
                )
                
                # Extraire le nom du client
                selected_idx = options.index(selected_option)
                selected_match = matches[selected_idx]
                client_folder = selected_match["path"]
                
                st.success(f"📁 Sélectionné : `{client_folder}`")
                
                # Bouton scanner
                if st.button("🔍 Scanner ce client", type="primary"):
                    with st.spinner("Scan en cours..."):
                        scan_result = scan_client_folder(client_folder)
                        st.session_state["last_scan"] = scan_result
                        st.rerun()
            
            else:
                st.warning(f"❌ Aucun client trouvé pour '{search_query}'")
        
        except Exception as e:
            st.error(f"Erreur recherche : {e}")
    
    # Afficher résultats scan
    if "last_scan" in st.session_state:
        show_scan_results(st.session_state["last_scan"])


def show_scan_results(scan_result: Dict[str, Any]):
    """
    Affiche les résultats d'un scan.
    """
    st.markdown("---")
    st.markdown("### 📊 Résultats du Scan")
    
    # Status global
    if scan_result["pipeline_ready"]:
        st.success("✅ Client PIPELINE-READY")
    else:
        st.error("❌ Client NON prêt pour le pipeline")
    
    # Métriques
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        gold_status = "✅" if scan_result["gold"] else "❌"
        st.metric(
            "GOLD détecté",
            gold_status,
            delta=f"Score: {scan_result['stats']['gold_score']:.2f}" if scan_result["gold"] else None,
        )
    
    with col2:
        st.metric(
            "Sources RAG",
            scan_result["stats"]["rag_sources_count"],
        )
    
    with col3:
        st.metric(
            "Dossiers OK",
            f"{scan_result['stats']['folders_detected']}/{len(scan_result['folder_structure'])}",
        )
    
    with col4:
        st.metric(
            "Taille totale",
            f"{scan_result['stats']['total_size_mb']} MB",
        )
    
    # Détails GOLD
    if scan_result["gold"]:
        with st.expander("📄 Détails GOLD", expanded=True):
            gold = scan_result["gold"]
            st.write(f"**Fichier** : `{Path(gold['path']).name}`")
            st.write(f"**Score** : {gold['score']:.2f}")
            st.write(f"**Stratégie** : {gold['strategy']}")
            st.write(f"**Taille** : {gold['size_bytes'] / 1024:.1f} KB")
            st.write(f"**Modifié** : {gold['modified']}")
    
    # Détails sources RAG
    if scan_result["rag_sources"]:
        with st.expander(f"📚 Sources RAG ({len(scan_result['rag_sources'])})"):
            for ext, count in scan_result["stats"]["extensions"].items():
                st.write(f"- **{ext}** : {count} fichier(s)")
            
            if st.checkbox("Afficher le détail des fichiers"):
                for source in scan_result["rag_sources"]:
                    st.write(f"- `{Path(source['path']).name}` ({source['category']})")
    
    # Warnings
    if scan_result["warnings"]:
        with st.expander("⚠️ Warnings", expanded=True):
            for warning in scan_result["warnings"]:
                st.warning(warning)
    
    # Structure dossiers
    with st.expander("📂 Structure des dossiers"):
        for key, path in scan_result["folder_structure"].items():
            status = "✅" if path else "❌"
            folder_name = Path(path).name if path else "Non trouvé"
            st.write(f"{status} **{key}** : `{folder_name}`")
    
    # Rapport texte
    with st.expander("📝 Rapport complet (texte)"):
        report_text = format_scan_report(scan_result)
        st.code(report_text, language="text")
    
    # Normalisation
    st.markdown("---")
    st.markdown("### 🔧 Normalisation")
    
    if not scan_result["pipeline_ready"]:
        st.error("❌ Impossible de normaliser : client non prêt")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        batch_name = st.text_input(
            "Nom du batch",
            value="TRAINING_BATCH",
            help="Nom du batch pour organiser la sandbox",
        )
    
    with col2:
        sandbox_root = st.text_input(
            "Sandbox racine",
            value="./sandbox",
            help="Dossier où créer la structure normalisée",
        )
    
    create_alias = st.checkbox(
        "Créer normalized/source.docx (alias)",
        value=True,
        help="Utile si le pipeline attend un fichier 'source.docx'",
    )
    
    if st.button("🚀 Normaliser en sandbox", type="primary"):
        with st.spinner("Normalisation en cours..."):
            try:
                norm_result = normalize_client_to_sandbox(
                    scan_result,
                    batch_name=batch_name,
                    sandbox_root=sandbox_root,
                    create_normalized_alias=create_alias,
                )
                
                st.success("✅ Normalisation réussie !")
                st.json(norm_result)
                
                # Stocker pour génération
                st.session_state["last_normalization"] = norm_result
                
            except Exception as e:
                st.error(f"❌ Erreur normalisation : {e}")


def show_batch_mode():
    """
    Mode batch (plusieurs clients).
    """
    st.subheader("📦 Normalisation Batch")
    
    # Browse dataset
    dataset_root = browse_directory(
        "Dataset racine",
        "Dossier contenant les sous-dossiers clients"
    )
    
    if not dataset_root or not Path(dataset_root).exists():
        st.warning("⚠️ Veuillez sélectionner un dataset valide")
        return
    
    st.success(f"✅ Dataset : `{dataset_root}`")
    
    # Lister clients disponibles
    dataset_path = Path(dataset_root)
    client_folders = [
        d.name for d in dataset_path.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ]
    
    st.info(f"💡 {len(client_folders)} dossier(s) trouvé(s)")
    
    # Sélection clients
    selected_clients = st.multiselect(
        "Clients à traiter",
        options=client_folders,
        default=client_folders[:5] if len(client_folders) >= 5 else client_folders,
        help="Sélectionner les clients à normaliser",
    )
    
    if not selected_clients:
        st.warning("⚠️ Sélectionnez au moins un client")
        return
    
    st.write(f"**{len(selected_clients)} client(s) sélectionné(s)**")
    
    # Configuration batch
    col1, col2 = st.columns(2)
    
    with col1:
        batch_name = st.text_input(
            "Nom du batch",
            value=f"BATCH_{len(selected_clients)}",
            key="batch_name_input",
        )
    
    with col2:
        sandbox_root = st.text_input(
            "Sandbox racine",
            value="./sandbox",
            key="sandbox_root_input",
        )
    
    continue_on_error = st.checkbox(
        "Continuer en cas d'erreur",
        value=True,
        help="Ne pas arrêter le batch si un client échoue",
    )
    
    # Lancer batch
    if st.button("🚀 Lancer la normalisation batch", type="primary"):
        with st.spinner(f"Traitement de {len(selected_clients)} client(s)..."):
            try:
                batch_result = normalize_batch_to_sandbox(
                    dataset_root=dataset_root,
                    client_names=selected_clients,
                    batch_name=batch_name,
                    sandbox_root=sandbox_root,
                    continue_on_error=continue_on_error,
                )
                
                st.success("✅ Batch terminé !")
                
                # Stats
                stats = batch_result["stats"]
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total", stats["total"])
                with col2:
                    st.metric("✅ Succès", stats["success"])
                with col3:
                    st.metric("⚠️ Non prêts", stats["not_ready"])
                with col4:
                    st.metric("❌ Erreurs", stats["errors"])
                
                # Rapport détaillé
                with st.expander("📝 Rapport détaillé"):
                    report_text = format_normalization_report(batch_result)
                    st.code(report_text, language="text")
                
                # JSON complet
                with st.expander("📄 Résultat JSON"):
                    st.json(batch_result)
                
                # Stocker résultats
                st.session_state["last_batch"] = batch_result
                
            except Exception as e:
                st.error(f"❌ Erreur batch : {e}")
                import traceback
                st.code(traceback.format_exc())


def show_advanced_config():
    """
    Configuration avancée.
    """
    st.subheader("⚙️ Configuration Avancée")
    
    st.markdown("""
    ### Paramètres de détection
    
    Configuration des seuils et stratégies de détection.
    """)
    
    # Seuils GOLD
    st.markdown("#### 📄 Détection GOLD")
    
    gold_min_score = st.slider(
        "Score minimum pour GOLD",
        min_value=0.0,
        max_value=1.0,
        value=0.3,
        step=0.05,
        help="Seuil de confiance minimum pour accepter un document comme GOLD",
    )
    
    gold_keywords = st.text_area(
        "Mots-clés GOLD (un par ligne)",
        value="rapport\nbilan\norientation\nsynthèse\nfinal",
        help="Mots-clés pour détecter le rapport final",
    )
    
    # Seuils RAG
    st.markdown("#### 📚 Sources RAG")
    
    min_rag_sources = st.number_input(
        "Nombre minimum de sources RAG",
        min_value=1,
        max_value=20,
        value=3,
        help="Nombre minimum de sources pour considérer le client prêt",
    )
    
    # Extensions
    st.markdown("#### 📎 Extensions acceptées")
    
    extensions = st.multiselect(
        "Extensions de fichiers",
        options=[".docx", ".pdf", ".txt", ".msg", ".doc", ".odt", ".rtf"],
        default=[".docx", ".pdf", ".txt", ".msg"],
        help="Extensions de fichiers à inclure dans les sources RAG",
    )
    
    st.info("💡 Configuration non encore implémentée (pour v2)")
    
    # Aperçu structure
    st.markdown("---")
    st.markdown("### 📂 Structure attendue")
    
    st.code("""
📁 NOM Prénom/
  ├── 01 Dossier personnel/    ← Sources RAG
  ├── 02 CV/
  ├── 03 Tests et bilans/      ← Sources RAG
  ├── 04 Stages/               ← Sources RAG
  ├── 05 Mesures AI/           ← Sources RAG
  ├── 06 Rapport final/        ← GOLD (rapport de référence)
  └── 07 Suivi/

Normalisation en sandbox :
📁 sandbox/BATCH_NAME/client_slug/
  ├── sources/                 ← Copies RAG
  ├── gold/
  │   └── rapport_final.docx   ← Copie GOLD
  ├── normalized/
  │   └── source.docx          ← Alias (optionnel)
  └── meta.json                ← Métadonnées
    """, language="text")


if __name__ == "__main__":
    show_training_page()
