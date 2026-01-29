"""
Page Streamlit pour l'entraînement du pipeline RH-Pro.

Permet de :
1. Browse pour sélectionner DATASET → BATCH → Client
2. Scanner et analyser un dossier client
3. Normaliser en sandbox (mode safe)
4. Lancer RAG + génération DOCX
"""

import streamlit as st
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import pandas as pd

from src.rhpro.client_scanner import scan_client_folder, format_scan_report
from src.rhpro.client_normalizer import (
    normalize_client_to_sandbox,
    normalize_batch_to_sandbox,
    format_normalization_report,
)
from src.rhpro.client_finder import find_client_folders
from src.rhpro.batch_analyzer import (
    scan_batch_clients,
    get_client_analysis_detail,
)
from src.rhpro.report_generator import (
    generate_report_from_normalized,
    RHProReportGenerator,
)
from src.rhpro.rag_generator import get_chunks_preview
import pandas as pd


def browse_directory(label: str, help_text: str = "") -> Optional[str]:
    """
    Permet de sélectionner un dossier via saisie manuelle ou suggestions.
    Alternative sans tkinter pour compatibilité maximale.
    
    Args:
        label: Label pour le widget
        help_text: Texte d'aide
        
    Returns:
        Chemin du dossier ou None
    """
    # Suggestions de chemins communs
    suggestions = [
        "/Users/malik/Documents/RH PRO BASE DONNEE/DATASET TRAINING/BATCH 20",
        "/Users/malik/Documents/SCRIPT.IA_DATA/training_sandbox",
        "./sandbox",
        str(Path.home() / "Documents"),
    ]
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        path_input = st.text_input(
            label,
            value=st.session_state.get(f"path_{label}", ""),
            help=help_text,
            key=f"input_{label}",
            placeholder="Ex: /Users/malik/Documents/...",
        )
    
    with col2:
        st.write("")  # Spacer
        st.write("")  # Spacer
        # Bouton pour afficher les suggestions
        if st.button("💡", key=f"suggest_{label}", help="Afficher les suggestions"):
            st.session_state[f"show_suggestions_{label}"] = not st.session_state.get(f"show_suggestions_{label}", False)
    
    # Afficher les suggestions si demandé
    if st.session_state.get(f"show_suggestions_{label}", False):
        st.markdown("**Chemins suggérés** (cliquez pour utiliser) :")
        for suggestion in suggestions:
            if Path(suggestion).exists():
                if st.button(f"✅ {suggestion}", key=f"use_{label}_{hash(suggestion)}"):
                    st.session_state[f"path_{label}"] = suggestion
                    st.session_state[f"show_suggestions_{label}"] = False
                    st.rerun()
            else:
                st.caption(f"⚠️ {suggestion} (n'existe pas)")
    
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
    Mode batch (plusieurs clients) - Version améliorée avec table et actions.
    """
    st.subheader("📦 Mode Training - Batch")
    
    # Browse BATCH folder
    batch_root = browse_directory(
        "Batch racine (BATCH_20, etc.)",
        "Dossier contenant les dossiers clients"
    )
    
    if not batch_root or not Path(batch_root).exists():
        st.warning("⚠️ Veuillez sélectionner un batch valide")
        return
    
    st.success(f"✅ Batch sélectionné : `{Path(batch_root).name}`")
    
    # Bouton pour scanner/re-scanner le batch (toujours visible)
    col1, col2 = st.columns([3, 1])
    with col1:
        scan_button_label = "🔍 Scanner le batch" if "batch_analysis" not in st.session_state else "🔄 Re-scanner le batch"
        if st.button(scan_button_label, type="primary", use_container_width=True):
            with st.spinner("Scan en cours..."):
                try:
                    batch_analysis = scan_batch_clients(
                        batch_path=batch_root,
                        limit=None,
                        min_pipeline_score=0.3,
                    )
                    st.session_state["batch_analysis"] = batch_analysis
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erreur scan batch : {e}")
                    return
    
    with col2:
        if "batch_analysis" in st.session_state and st.button("🗑️ Effacer", use_container_width=True):
            del st.session_state["batch_analysis"]
            st.rerun()
    
    # Afficher les résultats du scan
    if "batch_analysis" not in st.session_state:
        st.info("💡 Cliquez sur 'Scanner le batch' pour analyser les clients")
        return
    
    batch_analysis = st.session_state["batch_analysis"]
    
    st.markdown("---")
    st.markdown("### 📊 Clients Détectés")
    
    # Statistiques du batch
    summary = batch_analysis["summary"]
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total clients", summary["total"])
    with col2:
        st.metric("✅ Pipeline Ready", summary["pipeline_ready"])
    with col3:
        st.metric("GOLD détectés", summary["gold_detected"])
    with col4:
        st.metric("⚠️ Warnings", summary["warnings_total"])
    
    # Table des clients
    clients = batch_analysis["clients"]
    
    # Créer DataFrame pour affichage
    df_data = []
    for idx, client in enumerate(clients):
        status_emoji = "✅" if client["compatible"] else "⚠️"
        gold_emoji = "✅" if client["gold_detected"] else "❌"
        
        # Compter les sources par type
        rag_summary = ", ".join([
            f"{ext}:{count}" 
            for ext, count in client["rag_sources_by_type"].items()
        ]) if client["rag_sources_by_type"] else "Aucune"
        
        df_data.append({
            "Sélection": False,
            "Nom dossier": client["folder_name"],
            "Compatibilité": f"{status_emoji} {client['compatibility_score']:.2f}",
            "GOLD": gold_emoji,
            "Sources RAG": f"{client['rag_sources_count']} ({rag_summary})",
            "Warnings": client["warnings_count"],
            "_index": idx,  # Pour retrouver le client
        })
    
    df = pd.DataFrame(df_data)
    
    # Afficher la table avec sélection
    st.markdown("#### Table des clients")
    
    # Utiliser data_editor pour permettre la sélection
    edited_df = st.data_editor(
        df.drop(columns=["_index"]),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Sélection": st.column_config.CheckboxColumn(
                "Sélectionner",
                help="Cocher pour analyser/normaliser/générer",
                default=False,
            ),
        },
        key="clients_table",
    )
    
    # Récupérer les clients sélectionnés
    selected_indices = [i for i, row in edited_df.iterrows() if row["Sélection"]]
    selected_clients = [clients[df_data[i]["_index"]] for i in selected_indices]
    
    if selected_clients:
        st.info(f"💡 {len(selected_clients)} client(s) sélectionné(s)")
        
        # Boutons d'action
        st.markdown("#### Actions")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔍 Analyser", help="Analyser en détail les clients sélectionnés"):
                st.session_state["show_analysis"] = True
                st.session_state["selected_clients"] = selected_clients
        
        with col2:
            if st.button("🔧 Normaliser", help="Normaliser en sandbox"):
                st.session_state["show_normalize"] = True
                st.session_state["selected_clients"] = selected_clients
        
        with col3:
            if st.button("🚀 Run (RAG+DOCX)", help="Générer comptes-rendus", type="primary"):
                st.session_state["show_generate"] = True
                st.session_state["selected_clients"] = selected_clients
    
    # Vue analyse client détaillée
    if st.session_state.get("show_analysis") and st.session_state.get("selected_clients"):
        st.markdown("---")
        show_detailed_analysis(st.session_state["selected_clients"])
    
    # Vue normalisation
    if st.session_state.get("show_normalize") and st.session_state.get("selected_clients"):
        st.markdown("---")
        show_normalize_view(st.session_state["selected_clients"], batch_root)
    
    # Vue génération
    if st.session_state.get("show_generate") and st.session_state.get("selected_clients"):
        st.markdown("---")
        show_generate_view(st.session_state["selected_clients"], batch_root)


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


def show_detailed_analysis(selected_clients: List[Dict[str, Any]]):
    """
    Affiche une analyse détaillée des clients sélectionnés.
    
    Args:
        selected_clients: Liste des clients à analyser
    """
    st.markdown("### 🔍 Analyse Détaillée")
    
    # Sélecteur de client à analyser
    client_names = [c["folder_name"] for c in selected_clients]
    selected_name = st.selectbox(
        "Client à analyser",
        options=client_names,
        key="analysis_client_select",
    )
    
    # Trouver le client
    client = next(c for c in selected_clients if c["folder_name"] == selected_name)
    scan_result = client.get("scan_result")
    
    if not scan_result:
        st.error("❌ Données de scan manquantes pour ce client")
        return
    
    # Générer l'analyse détaillée
    analysis = get_client_analysis_detail(scan_result)
    
    # Afficher les sections
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### ✅ Ce que j'ai trouvé")
        
        # GOLD
        if analysis["what_found"]["gold"]:
            gold = analysis["what_found"]["gold"]
            st.write(f"**GOLD** : {gold['name']}")
            st.write(f"  - Score : {gold['score']:.2f}")
            st.write(f"  - Taille : {gold['size_kb']:.1f} KB")
            st.write(f"  - Stratégie : {gold['strategy']}")
        else:
            st.write("**GOLD** : ❌ Non trouvé")
        
        st.write("")
        st.write(f"**Sources RAG** : {len(analysis['what_found']['rag_sources'])} fichiers")
        if analysis["what_found"]["rag_sources"]:
            with st.expander("Détails des sources"):
                for source in analysis["what_found"]["rag_sources"][:10]:
                    st.write(f"- {source['name']} ({source['category']}, {source['extension']})")
        
        st.write("")
        st.write(f"**Dossiers** : {sum(1 for f in analysis['what_found']['folders'] if f['found'])}/{len(analysis['what_found']['folders'])}")
    
    with col2:
        st.markdown("#### 🎯 Ce que je peux exploiter")
        
        if analysis["what_usable"]["gold_usable"]:
            st.success("✅ GOLD exploitable")
        else:
            st.error("❌ GOLD non exploitable")
        
        st.write(f"**Sources RAG exploitables** : {len(analysis['what_usable']['rag_sources_usable'])}")
        st.write(f"**Dossiers exploitables** : {len(analysis['what_usable']['folders_usable'])}")
    
    # Ce qui manque
    st.markdown("#### ⚠️ Ce qui manque pour être 100% pipeline")
    for missing in analysis["what_missing"]:
        if "✅" in missing:
            st.success(missing)
        elif "❌" in missing:
            st.error(missing)
        else:
            st.warning(missing)
    
    # Choix du GOLD
    if analysis["gold_choice"]:
        st.markdown("#### 📄 GOLD choisi")
        gold_choice = analysis["gold_choice"]
        st.info(f"**Fichier** : {gold_choice['file']}")
        st.write(f"**Score** : {gold_choice['score']:.2f}")
        st.write(f"**Raison** : {gold_choice['reason']}")
    
    # Aperçu chunks RAG (optionnel)
    if st.checkbox("Afficher aperçu chunks RAG (debug)", key="show_chunks"):
        with st.spinner("Chargement des chunks..."):
            try:
                sources_folder = Path(client["folder_path"])
                chunks = get_chunks_preview(str(sources_folder), max_chunks=10)
                
                if chunks:
                    st.markdown("#### 🔍 Aperçu 10 premiers chunks")
                    for i, chunk in enumerate(chunks[:10], 1):
                        with st.expander(f"Chunk {i} - {chunk['source_file']} ({chunk['text_length']} chars)"):
                            st.text(chunk['text'][:500] + "..." if len(chunk['text']) > 500 else chunk['text'])
                else:
                    st.warning("Aucun chunk généré")
            except Exception as e:
                st.error(f"Erreur génération chunks : {e}")


def show_normalize_view(selected_clients: List[Dict[str, Any]], batch_root: str):
    """
    Vue de normalisation des clients sélectionnés.
    
    Args:
        selected_clients: Liste des clients à normaliser
        batch_root: Chemin du batch racine
    """
    st.markdown("### 🔧 Normalisation en Sandbox")
    
    # Configuration
    col1, col2 = st.columns(2)
    
    with col1:
        batch_name = st.text_input(
            "Nom du batch",
            value=Path(batch_root).name,
            key="normalize_batch_name",
        )
    
    with col2:
        sandbox_root = st.text_input(
            "Sandbox racine",
            value="./sandbox",
            key="normalize_sandbox_root",
        )
    
    create_alias = st.checkbox(
        "Créer normalized/source.docx (alias)",
        value=True,
        help="Utile si le pipeline attend un fichier 'source.docx'",
    )
    
    st.write(f"**{len(selected_clients)} client(s) à normaliser**")
    
    if st.button("🚀 Lancer la normalisation", type="primary", key="normalize_btn"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        results = []
        
        for i, client in enumerate(selected_clients):
            status_text.text(f"Normalisation de {client['folder_name']}...")
            
            try:
                scan_result = client.get("scan_result")
                if not scan_result:
                    results.append({
                        "client": client["folder_name"],
                        "success": False,
                        "error": "Données de scan manquantes",
                    })
                    continue
                
                norm_result = normalize_client_to_sandbox(
                    scan_result,
                    batch_name=batch_name,
                    sandbox_root=sandbox_root,
                    create_normalized_alias=create_alias,
                )
                
                results.append({
                    "client": client["folder_name"],
                    "success": True,
                    "normalized_path": norm_result["normalized_path"],
                })
            
            except Exception as e:
                results.append({
                    "client": client["folder_name"],
                    "success": False,
                    "error": str(e),
                })
            
            progress_bar.progress((i + 1) / len(selected_clients))
        
        status_text.empty()
        progress_bar.empty()
        
        # Résultats
        success_count = sum(1 for r in results if r["success"])
        st.success(f"✅ Normalisation terminée : {success_count}/{len(selected_clients)} réussis")
        
        # Tableau des résultats
        for result in results:
            if result["success"]:
                st.success(f"✅ {result['client']} → {result['normalized_path']}")
            else:
                st.error(f"❌ {result['client']} : {result['error']}")
        
        # Stocker pour génération
        st.session_state["normalized_clients"] = [
            r for r in results if r["success"]
        ]


def show_generate_view(selected_clients: List[Dict[str, Any]], batch_root: str):
    """
    Vue de génération des comptes-rendus.
    
    Args:
        selected_clients: Liste des clients pour lesquels générer
        batch_root: Chemin du batch racine
    """
    st.markdown("### 🚀 Génération Comptes-Rendus RH-Pro")
    
    # Configuration
    col1, col2 = st.columns(2)
    
    with col1:
        output_dir = st.text_input(
            "Dossier de sortie",
            value="./output",
            key="generate_output_dir",
        )
    
    with col2:
        template_path = st.text_input(
            "Template DOCX (optionnel)",
            value="",
            key="generate_template_path",
            help="Laisser vide pour utiliser le template par défaut",
        )
    
    strict_mode = st.checkbox(
        "Mode strict (interdiction d'inventer)",
        value=True,
        help="Si activé, retourne 'Non renseigné' si information non trouvée",
    )
    
    st.write(f"**{len(selected_clients)} client(s) à traiter**")
    
    st.info("""
    💡 **Pipeline de génération** :
    1. Construire index RAG depuis sources/
    2. Extraire champs via RAG avec garde-fous
    3. Remplir template DOCX
    4. Générer outputs : generated.docx, debug.json, metrics.json
    """)
    
    if st.button("🚀 Lancer la génération", type="primary", key="generate_btn"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        results = []
        
        for i, client in enumerate(selected_clients):
            status_text.text(f"Génération pour {client['folder_name']}...")
            
            try:
                # Vérifier si client normalisé
                client_folder = Path(client["folder_path"])
                
                # Option 1 : Client déjà normalisé en sandbox
                normalized_path = Path("sandbox") / Path(batch_root).name / client["folder_name"]
                
                if normalized_path.exists():
                    # Générer depuis normalisé
                    gen_result = generate_report_from_normalized(
                        normalized_folder=str(normalized_path),
                        output_dir=output_dir,
                        template_path=template_path if template_path else None,
                        strict_mode=strict_mode,
                    )
                else:
                    # Générer directement (sans normalisation)
                    scan_result = client.get("scan_result")
                    if not scan_result or not scan_result.get("rag_sources"):
                        raise ValueError("Pas de sources RAG disponibles")
                    
                    # Créer dossier temporaire avec sources
                    import tempfile
                    import shutil
                    
                    with tempfile.TemporaryDirectory() as tmpdir:
                        sources_tmp = Path(tmpdir) / "sources"
                        sources_tmp.mkdir()
                        
                        # Copier les sources
                        for source in scan_result["rag_sources"]:
                            shutil.copy(source["path"], sources_tmp)
                        
                        # Générer
                        generator = RHProReportGenerator(
                            template_path=template_path if template_path else None,
                        )
                        
                        gen_result = generator.generate_from_client(
                            sources_folder=str(sources_tmp),
                            gold_path=scan_result["gold"]["path"] if scan_result["gold"] else None,
                            output_dir=output_dir,
                            client_name=client["folder_name"],
                            strict_mode=strict_mode,
                        )
                
                results.append({
                    "client": client["folder_name"],
                    "success": True,
                    "outputs": gen_result["outputs"],
                    "metrics": gen_result["metrics"],
                })
            
            except Exception as e:
                results.append({
                    "client": client["folder_name"],
                    "success": False,
                    "error": str(e),
                })
            
            progress_bar.progress((i + 1) / len(selected_clients))
        
        status_text.empty()
        progress_bar.empty()
        
        # Résultats
        success_count = sum(1 for r in results if r["success"])
        st.success(f"✅ Génération terminée : {success_count}/{len(selected_clients)} réussis")
        
        # Afficher les résultats
        for result in results:
            with st.expander(f"{'✅' if result['success'] else '❌'} {result['client']}", expanded=result["success"]):
                if result["success"]:
                    # Outputs
                    st.markdown("**Outputs générés** :")
                    outputs = result["outputs"]
                    st.write(f"- DOCX : `{outputs['generated_docx']}`")
                    st.write(f"- Debug JSON : `{outputs['debug_json']}`")
                    st.write(f"- Metrics JSON : `{outputs['metrics_json']}`")
                    if outputs.get("gold_reference"):
                        st.write(f"- GOLD référence : `{outputs['gold_reference']}`")
                    
                    # Métriques
                    st.markdown("**Métriques** :")
                    metrics = result["metrics"]
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Couverture", f"{metrics['coverage_pct']}%")
                    with col2:
                        st.metric("Couverture requise", f"{metrics['required_coverage_pct']}%")
                    with col3:
                        st.metric("Confiance", f"{metrics['avg_confidence']:.2f}")
                    with col4:
                        st.metric("Score qualité", f"{metrics['quality_score']:.2f}")
                    
                    # Boutons d'action
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"📄 Ouvrir debug.json", key=f"debug_{result['client']}"):
                            with open(outputs['debug_json'], 'r', encoding='utf-8') as f:
                                debug_data = json.load(f)
                                st.json(debug_data)
                    
                    with col2:
                        if st.button(f"📊 Ouvrir metrics.json", key=f"metrics_{result['client']}"):
                            with open(outputs['metrics_json'], 'r', encoding='utf-8') as f:
                                metrics_data = json.load(f)
                                st.json(metrics_data)
                else:
                    st.error(f"Erreur : {result['error']}")


if __name__ == "__main__":
    show_training_page()
