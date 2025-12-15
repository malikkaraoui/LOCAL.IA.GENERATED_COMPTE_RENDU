"""Dataclasses partagées pour l'orchestrateur."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SourceDoc:
    path: str
    ext: str
    size_bytes: int
    mtime_iso: str
    extractor: str
    text: str
    text_sha256: str
    pages: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


@dataclass
class ExtractionPayload:
    root: Path
    generated_at: str
    enable_soffice: bool
    counts: Dict[str, int]
    documents: List[SourceDoc]


@dataclass
class Chunk:
    chunk_id: str
    source_path: str
    page: Optional[int]
    text: str


@dataclass
class RetrievalResult:
    rank: int
    score: float
    chunk: Chunk
