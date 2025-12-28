"""Extracteur pour fichiers .msg (emails Outlook).

Ce module permet d'extraire le contenu texte des emails Outlook .msg,
incluant métadonnées (subject, from, to, date) et pièces jointes.

Usage:
    from core.extractors.msg_extractor import extract_msg_to_text, MSG_SUPPORT_AVAILABLE
    
    if MSG_SUPPORT_AVAILABLE:
        text, meta = extract_msg_to_text(msg_path, output_dir)
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Optional

from ..logger import get_logger

LOG = get_logger("core.extractors.msg")

# ✅ Lazy import : si extract_msg n'est pas installé, pas de crash
MSG_SUPPORT_AVAILABLE = False
try:
    import extract_msg
    MSG_SUPPORT_AVAILABLE = True
    LOG.info("extract-msg disponible : support .msg activé")
except ImportError:
    LOG.warning("extract-msg non installé : les fichiers .msg ne seront pas indexés")
    extract_msg = None  # type: ignore


# Extensions autorisées pour extraction pièces jointes
ALLOWED_ATTACHMENT_EXTENSIONS = {".pdf", ".docx", ".txt", ".doc"}

# Limite taille texte email (200k caractères)
MAX_EMAIL_TEXT_SIZE = 200_000


def _strip_html_tags(html: str) -> str:
    """Convertit HTML en texte brut (strip tags simple)."""
    # Remplacer <br>, <p>, <div> par newlines
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</p>", "\n\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</div>", "\n", html, flags=re.IGNORECASE)
    
    # Supprimer tous les tags HTML
    text = re.sub(r"<[^>]+>", "", html)
    
    # Décoder entités HTML basiques
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    
    # Nettoyer espaces multiples
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    return text.strip()


def _safe_email_string(value: Optional[str]) -> str:
    """Convertit une valeur en string UTF-8 safe."""
    if value is None:
        return ""
    try:
        return str(value).strip()
    except Exception:
        return ""


def _hash_msg(path: Path) -> str:
    """Génère un hash unique pour le fichier .msg."""
    return hashlib.sha256(f"{path.name}_{path.stat().st_size}".encode()).hexdigest()[:12]


def extract_msg_to_text(
    msg_path: Path,
    output_dir: Optional[Path] = None,
) -> tuple[str, dict]:
    """Extrait le contenu d'un fichier .msg en texte indexable.
    
    Args:
        msg_path: Chemin vers le fichier .msg
        output_dir: Dossier pour extraire les pièces jointes (optionnel)
        
    Returns:
        tuple[str, dict]:
            - text: Contenu texte formaté pour indexation RAG
            - meta: Métadonnées (subject, from, to, date, attachments_count, extracted_attachments_paths)
            
    Raises:
        ImportError: Si extract-msg n'est pas installé
        Exception: Si l'extraction échoue
    """
    if not MSG_SUPPORT_AVAILABLE or extract_msg is None:
        raise ImportError("extract-msg non installé : pip install extract-msg>=0.48.0")
    
    msg_path = Path(msg_path).resolve()
    if not msg_path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {msg_path}")
    
    LOG.info("Extraction .msg : %s", msg_path.name)
    
    try:
        # Charger le message
        msg = extract_msg.Message(str(msg_path))
        
        # ✅ Extraire métadonnées
        subject = _safe_email_string(msg.subject)
        sender = _safe_email_string(msg.sender)
        to_recipients = _safe_email_string(msg.to)
        cc_recipients = _safe_email_string(msg.cc)
        date = _safe_email_string(msg.date)
        
        # ✅ Extraire body (texte ou HTML)
        body_text = ""
        if hasattr(msg, "body") and msg.body:
            body_text = _safe_email_string(msg.body)
        elif hasattr(msg, "htmlBody") and msg.htmlBody:
            # Convertir HTML -> texte
            body_text = _strip_html_tags(msg.htmlBody)
        
        if not body_text:
            body_text = "(body vide)"
        
        # ✅ Limiter taille
        if len(body_text) > MAX_EMAIL_TEXT_SIZE:
            body_text = body_text[:MAX_EMAIL_TEXT_SIZE] + "\n\n[...contenu tronqué...]"
        
        # ✅ Lister pièces jointes
        attachments = []
        extracted_attachments_paths = []
        
        if hasattr(msg, "attachments") and msg.attachments:
            for att in msg.attachments:
                att_name = getattr(att, "longFilename", None) or getattr(att, "shortFilename", "unknown")
                attachments.append(att_name)
                
                # ✅ Extraire pièces jointes autorisées
                if output_dir:
                    att_ext = Path(att_name).suffix.lower()
                    if att_ext in ALLOWED_ATTACHMENT_EXTENSIONS:
                        try:
                            # Créer sous-dossier unique pour ce mail
                            msg_hash = _hash_msg(msg_path)
                            att_dir = output_dir / f"msg_{msg_hash}"
                            att_dir.mkdir(parents=True, exist_ok=True)
                            
                            # Extraire pièce jointe
                            att_path = att_dir / att_name
                            att.save(customPath=str(att_dir), customFilename=att_name)
                            
                            if att_path.exists():
                                extracted_attachments_paths.append(str(att_path))
                                LOG.debug("Pièce jointe extraite : %s", att_name)
                        except Exception as e:
                            LOG.warning("Échec extraction pièce jointe %s : %s", att_name, e)
        
        # ✅ Fermer le message
        msg.close()
        
        # ✅ Formater texte indexable
        lines = [
            "[EMAIL_MSG]",
            f"Subject: {subject}",
            f"From: {sender}",
            f"To: {to_recipients}",
        ]
        
        if cc_recipients:
            lines.append(f"Cc: {cc_recipients}")
        
        if date:
            lines.append(f"Date: {date}")
        
        if attachments:
            lines.append(f"Attachments: {'; '.join(attachments)}")
        
        lines.append("---")
        lines.append("Body:")
        lines.append(body_text)
        
        text = "\n".join(lines)
        
        # ✅ Métadonnées
        meta = {
            "subject": subject,
            "from": sender,
            "to": to_recipients,
            "cc": cc_recipients,
            "date": date,
            "attachments_count": len(attachments),
            "attachments_list": attachments,
            "extracted_attachments_paths": extracted_attachments_paths,
        }
        
        LOG.debug(
            "Email extrait : %d caractères, %d pièces jointes (%d extraites)",
            len(text),
            len(attachments),
            len(extracted_attachments_paths),
        )
        
        return text, meta
        
    except Exception as exc:
        LOG.error("Échec extraction .msg %s : %s", msg_path.name, exc)
        raise


def extract_msg_safe(msg_path: Path, output_dir: Optional[Path] = None) -> tuple[Optional[str], Optional[dict], Optional[str]]:
    """Version safe de extract_msg_to_text qui ne lève jamais d'exception.
    
    Args:
        msg_path: Chemin vers le fichier .msg
        output_dir: Dossier pour extraire les pièces jointes (optionnel)
        
    Returns:
        tuple[Optional[str], Optional[dict], Optional[str]]:
            - text: Contenu texte (None si échec)
            - meta: Métadonnées (None si échec)
            - error: Message d'erreur (None si succès)
    """
    if not MSG_SUPPORT_AVAILABLE:
        return None, None, "MSG_EXTRACTOR_MISSING"
    
    try:
        text, meta = extract_msg_to_text(msg_path, output_dir)
        return text, meta, None
    except Exception as exc:
        error_msg = f"MSG_EXTRACT_FAILED: {str(exc)[:200]}"
        LOG.warning("Extraction .msg échouée pour %s : %s", msg_path.name, exc)
        return None, None, error_msg
