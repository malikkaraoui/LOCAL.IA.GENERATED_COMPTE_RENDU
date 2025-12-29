"""
Module RAG pour génération de comptes-rendus RH-Pro.

Construit un index RAG depuis les sources client et génère un rapport structuré.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib

# Import LlamaIndex components
try:
    from llama_index.core import (
        VectorStoreIndex,
        SimpleDirectoryReader,
        Document,
        Settings,
        StorageContext,
    )
    from llama_index.core.node_parser import SentenceSplitter
    from llama_index.embeddings.openai import OpenAIEmbedding
    from llama_index.llms.openai import OpenAI
    LLAMA_INDEX_AVAILABLE = True
except ImportError:
    LLAMA_INDEX_AVAILABLE = False


class RAGGenerator:
    """
    Générateur RAG pour comptes-rendus RH-Pro.
    """
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        embedding_model: str = "text-embedding-3-small",
        llm_model: str = "gpt-4o-mini",
        temperature: float = 0.1,
        training_state: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialise le générateur RAG.
        
        Args:
            chunk_size: Taille des chunks en tokens
            chunk_overlap: Overlap entre chunks
            embedding_model: Modèle d'embeddings
            llm_model: Modèle LLM pour génération
            temperature: Température du LLM
            training_state: État de training optionnel (patterns appris)
        """
        if not LLAMA_INDEX_AVAILABLE:
            import warnings
            warnings.warn(
                "⚠️ LlamaIndex non disponible. Mode dégradé activé. "
                "Pour activer le RAG avancé : pip install llama-index",
                RuntimeWarning
            )
            self.degraded_mode = True
        else:
            self.degraded_mode = False
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.training_state = training_state
        
        # Configuration LlamaIndex (seulement si disponible)
        if not self.degraded_mode:
            Settings.embed_model = OpenAIEmbedding(model=embedding_model)
            Settings.llm = OpenAI(model=llm_model, temperature=temperature)
            Settings.chunk_size = chunk_size
            Settings.chunk_overlap = chunk_overlap
        
        self.index = None
        self.sources_metadata = []
    
    def build_index_from_sources(
        self,
        sources_folder: str,
        file_extensions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Construit l'index RAG depuis un dossier de sources.
        
        Args:
            sources_folder: Dossier contenant les sources
            file_extensions: Extensions à inclure (par défaut : .docx, .pdf, .txt)
            
        Returns:
            Dict avec métadonnées de l'indexation
        """
        if self.degraded_mode:
            import warnings
            warnings.warn(
                "⚠️ Mode dégradé : indexation RAG désactivée (LlamaIndex non disponible)",
                RuntimeWarning
            )
            return {
                "status": "degraded",
                "sources_count": 0,
                "chunks_count": 0,
                "message": "LlamaIndex non disponible - mode dégradé"
            }
        
        sources_path = Path(sources_folder)
        
        if not sources_path.exists():
            raise FileNotFoundError(f"Dossier sources introuvable : {sources_folder}")
        
        if file_extensions is None:
            file_extensions = [".docx", ".pdf", ".txt", ".doc"]
        
        # Charger les documents
        documents = []
        self.sources_metadata = []
        
        from src.utils.file_filters import is_ignored_filename
        
        for file_path in sources_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in file_extensions and not is_ignored_filename(file_path):
                try:
                    # Lire le document
                    reader = SimpleDirectoryReader(
                        input_files=[str(file_path)],
                        filename_as_id=True,
                    )
                    docs = reader.load_data()
                    
                    # Ajouter métadonnées
                    for doc in docs:
                        doc.metadata.update({
                            "source_file": file_path.name,
                            "source_path": str(file_path),
                            "file_type": file_path.suffix,
                        })
                        documents.append(doc)
                    
                    self.sources_metadata.append({
                        "file": file_path.name,
                        "path": str(file_path),
                        "extension": file_path.suffix,
                        "docs_count": len(docs),
                    })
                
                except Exception as e:
                    self.sources_metadata.append({
                        "file": file_path.name,
                        "path": str(file_path),
                        "extension": file_path.suffix,
                        "error": str(e),
                    })
        
        if not documents:
            raise ValueError("Aucun document chargé depuis les sources")
        
        # Créer l'index
        self.index = VectorStoreIndex.from_documents(
            documents,
            show_progress=True,
        )
        
        # Récupérer les chunks créés
        nodes = self.index.docstore.docs
        chunks_info = []
        
        for node_id, node in nodes.items():
            chunks_info.append({
                "chunk_id": node_id,
                "source_file": node.metadata.get("source_file", "unknown"),
                "text_preview": node.text[:100] + "..." if len(node.text) > 100 else node.text,
                "text_length": len(node.text),
            })
        
        return {
            "sources_count": len(self.sources_metadata),
            "sources": self.sources_metadata,
            "documents_loaded": len(documents),
            "chunks_created": len(chunks_info),
            "chunks_preview": chunks_info[:10],  # Aperçu 10 premiers chunks
            "index_built": True,
            "timestamp": datetime.now().isoformat(),
        }
    
    def generate_report(
        self,
        template_fields: List[str],
        strict_mode: bool = True,
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        """
        Génère un rapport structuré avec RAG.
        
        Args:
            template_fields: Liste des champs à remplir
            strict_mode: Si True, interdit l'invention (retourne "Non renseigné")
            max_retries: Nombre max de tentatives par champ
            
        Returns:
            Dict avec les champs remplis et les métadonnées
        """
        if self.degraded_mode:
            import warnings
            warnings.warn(
                "⚠️ Mode dégradé : génération RAG désactivée (LlamaIndex non disponible)",
                RuntimeWarning
            )
            # Retourner des champs vides avec fallback "Non renseigné"
            filled_fields = {field: "Non renseigné" for field in template_fields}
            debug_info = {
                field: {
                    "value": "Non renseigné",
                    "error": "LlamaIndex non disponible - mode dégradé",
                    "degraded_mode": True
                }
                for field in template_fields
            }
            return {
                "fields": filled_fields,
                "debug": debug_info,
                "status": "degraded",
                "timestamp": datetime.now().isoformat()
            }
        
        if self.index is None:
            raise ValueError("Index RAG non construit. Appelez build_index_from_sources() d'abord.")
        
        # Créer le query engine
        query_engine = self.index.as_query_engine(
            similarity_top_k=5,
            response_mode="tree_summarize",
        )
        
        # Générer les champs
        filled_fields = {}
        debug_info = {}
        
        for field in template_fields:
            try:
                # Construire le prompt avec garde-fous (utilise training_state si disponible)
                prompt = self._build_field_prompt(field, strict_mode)
                
                # Ajouter context du training_state si disponible
                if self.training_state and "patterns" in self.training_state:
                    prompt = self._enrich_prompt_with_training_state(prompt, field)
                
                # Query RAG
                response = query_engine.query(prompt)
                
                # Extraire citations
                citations = self._extract_citations(response)
                
                # Extraire preuves textuelles (evidence)
                evidence = self._extract_evidence_from_citations(citations, field)
                
                # Vérifier si réponse valide
                value = str(response).strip()
                if self._is_hallucination(value, strict_mode):
                    value = "Non renseigné"
                
                filled_fields[field] = value
                debug_info[field] = {
                    "value": value,
                    "citations": citations,
                    "sources_used": [c["source"] for c in citations],
                    "confidence": self._estimate_confidence(response, citations),
                    "evidence": evidence,  # Preuves textuelles extraites
                }
            
            except Exception as e:
                filled_fields[field] = "Non renseigné"
                debug_info[field] = {
                    "value": "Non renseigné",
                    "error": str(e),
                    "citations": [],
                    "confidence": 0.0,
                }
        
        # Métriques de couverture
        metrics = self._calculate_coverage_metrics(filled_fields, debug_info)
        
        return {
            "fields": filled_fields,
            "debug": debug_info,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat(),
        }
    
    def _build_field_prompt(self, field: str, strict_mode: bool) -> str:
        """
        Construit le prompt pour un champ avec garde-fous.
        
        Args:
            field: Nom du champ
            strict_mode: Mode strict (pas d'invention)
            
        Returns:
            Prompt formaté
        """
        base_prompt = f"Extraire l'information suivante : {field}"
        
        if strict_mode:
            base_prompt += """

RÈGLES STRICTES :
- Utiliser UNIQUEMENT les informations présentes dans les documents
- Si l'information n'est pas trouvée, répondre exactement : "Non renseigné"
- Ne JAMAIS inventer, déduire ou supposer
- Citer la source (nom du document) si possible
"""
        
        return base_prompt
    
    def _enrich_prompt_with_training_state(self, prompt: str, field: str) -> str:
        """Enrichit le prompt avec le context du training_state."""
        if not self.training_state:
            return prompt
        
        enrichments = []
        
        # Ajouter info sur les titres attendus
        if "patterns" in self.training_state and "title_mappings" in self.training_state["patterns"]:
            title_mappings = self.training_state["patterns"]["title_mappings"]
            if title_mappings:
                enrichments.append(f"Titres fréquents observés : {', '.join(list(title_mappings.keys())[:5])}")
        
        # Ajouter info sur longueurs attendues
        if "patterns" in self.training_state and "section_lengths" in self.training_state["patterns"]:
            section_lengths = self.training_state["patterns"]["section_lengths"]
            if field in section_lengths and section_lengths[field]:
                avg_length = sum(section_lengths[field]) / len(section_lengths[field])
                enrichments.append(f"Longueur typique pour '{field}' : ~{avg_length:.0f} lignes")
        
        if enrichments:
            prompt += "\n\nContext (patterns appris) :\n" + "\n".join(f"- {e}" for e in enrichments)
        
        return prompt
    
    def _extract_citations(self, response) -> List[Dict[str, Any]]:
        """
        Extrait les citations depuis une réponse RAG.
        
        Args:
            response: Réponse du query engine
            
        Returns:
            Liste de citations avec source et snippet
        """
        citations = []
        
        if hasattr(response, "source_nodes"):
            for node in response.source_nodes:
                citations.append({
                    "source": node.metadata.get("source_file", "unknown"),
                    "snippet": node.text[:200] + "..." if len(node.text) > 200 else node.text,
                    "score": node.score if hasattr(node, "score") else None,
                    "full_text": node.text,  # Texte complet pour extraction de preuves
                })
        
        return citations
    
    def _extract_evidence_from_citations(
        self,
        citations: List[Dict[str, Any]],
        field: str
    ) -> List[str]:
        """
        Extrait les preuves textuelles pertinentes depuis les citations.
        
        Règle : no-evidence = no-claim
        Chaque valeur extraite doit avoir des preuves traçables.
        
        Args:
            citations: Liste des citations
            field: Nom du champ concerné
            
        Returns:
            Liste de snippets de preuves
        """
        evidence = []
        
        for citation in citations:
            # Pour chaque citation, extraire le snippet pertinent
            snippet = citation.get("snippet", "")
            full_text = citation.get("full_text", "")
            
            # Si le snippet contient l'information, le garder comme preuve
            if snippet:
                evidence.append({
                    "source": citation.get("source", "unknown"),
                    "text": snippet,
                    "score": citation.get("score", 0.0),
                })
        
        return evidence
    
    def _is_hallucination(self, value: str, strict_mode: bool) -> bool:
        """
        Détecte si une valeur est probablement une hallucination.
        
        Args:
            value: Valeur à vérifier
            strict_mode: Mode strict
            
        Returns:
            True si hallucination probable
        """
        if not strict_mode:
            return False
        
        # Patterns d'hallucination
        hallucination_patterns = [
            "je ne trouve pas",
            "impossible de",
            "pas d'information",
            "non mentionné",
            "je ne peux pas",
            "désolé",
        ]
        
        value_lower = value.lower()
        
        # Si contient pattern d'échec
        if any(pattern in value_lower for pattern in hallucination_patterns):
            return True
        
        # Si trop court (< 10 chars) et pas "Non renseigné"
        if len(value) < 10 and "non renseigné" not in value_lower:
            return True
        
        return False
    
    def _estimate_confidence(self, response, citations: List[Dict]) -> float:
        """
        Estime la confiance de la réponse.
        
        Args:
            response: Réponse RAG
            citations: Citations extraites
            
        Returns:
            Score de confiance (0.0 à 1.0)
        """
        if not citations:
            return 0.0
        
        # Moyenne des scores de similarité
        scores = [c.get("score", 0.0) for c in citations if c.get("score")]
        if not scores:
            return 0.5  # Confiance moyenne par défaut
        
        return sum(scores) / len(scores)
    
    def _calculate_coverage_metrics(
        self,
        fields: Dict[str, str],
        debug_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calcule les métriques de couverture.
        
        Args:
            fields: Champs remplis
            debug_info: Informations de debug
            
        Returns:
            Métriques de couverture
        """
        total_fields = len(fields)
        filled_fields = sum(
            1 for v in fields.values()
            if v and v != "Non renseigné"
        )
        
        # Couverture requise (champs obligatoires)
        required_fields = [
            "nom", "prenom", "date_naissance",
            "situation_professionnelle", "objectifs",
        ]
        
        required_filled = sum(
            1 for field in required_fields
            if field in fields and fields[field] != "Non renseigné"
        )
        
        # Confiance moyenne
        confidences = [
            info.get("confidence", 0.0)
            for info in debug_info.values()
            if "confidence" in info
        ]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            "total_fields": total_fields,
            "filled_fields": filled_fields,
            "coverage_pct": round((filled_fields / total_fields) * 100, 2),
            "required_fields": len(required_fields),
            "required_filled": required_filled,
            "required_coverage_pct": round((required_filled / len(required_fields)) * 100, 2),
            "avg_confidence": round(avg_confidence, 2),
            "quality_score": self._calculate_quality_score(
                filled_fields / total_fields,
                avg_confidence,
            ),
        }
    
    def _calculate_quality_score(
        self,
        coverage: float,
        confidence: float
    ) -> float:
        """
        Calcule un score de qualité global.
        
        Args:
            coverage: Taux de couverture (0.0 à 1.0)
            confidence: Confiance moyenne (0.0 à 1.0)
            
        Returns:
            Score de qualité (0.0 à 1.0)
        """
        # Pondération : 60% couverture, 40% confiance
        return round(coverage * 0.6 + confidence * 0.4, 2)


def get_chunks_preview(
    sources_folder: str,
    max_chunks: int = 10,
    chunk_size: int = 512,
) -> List[Dict[str, Any]]:
    """
    Génère un aperçu des chunks RAG sans construire l'index complet.
    
    Utile pour debug UI.
    
    Args:
        sources_folder: Dossier des sources
        max_chunks: Nombre max de chunks à retourner
        chunk_size: Taille des chunks
        
    Returns:
        Liste de chunks avec métadonnées
    """
    if not LLAMA_INDEX_AVAILABLE:
        import warnings
        warnings.warn(
            "⚠️ Mode dégradé : aperçu chunks désactivé (LlamaIndex non disponible)",
            RuntimeWarning
        )
        return []
    
    sources_path = Path(sources_folder)
    
    if not sources_path.exists():
        return []
    
    from src.utils.file_filters import is_ignored_filename
    
    # Charger quelques documents
    documents = []
    docx_files = [f for f in sources_path.rglob("*.docx") if not is_ignored_filename(f)][:3]  # Max 3 fichiers
    for file_path in docx_files:
        try:
            reader = SimpleDirectoryReader(
                input_files=[str(file_path)],
                filename_as_id=True,
            )
            docs = reader.load_data()
            for doc in docs:
                doc.metadata["source_file"] = file_path.name
                documents.append(doc)
        except:
            pass
    
    if not documents:
        return []
    
    # Splitter en chunks
    splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=50)
    nodes = splitter.get_nodes_from_documents(documents)
    
    # Retourner aperçu
    chunks = []
    for i, node in enumerate(nodes[:max_chunks]):
        chunks.append({
            "chunk_id": i,
            "source_file": node.metadata.get("source_file", "unknown"),
            "text": node.text,
            "text_length": len(node.text),
        })
    
    return chunks
