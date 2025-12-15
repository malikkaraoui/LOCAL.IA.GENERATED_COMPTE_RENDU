#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Orchestrateur unique pour la génération de rapports."""

from __future__ import annotations

import json
import logging
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from core.extract import extract_sources, walk_files
from core.generate import DEFAULT_FIELDS, generate_fields
from core.template_fields import build_field_specs, extract_placeholders_from_docx
from core.render import render_report
from core.export import docx_to_pdf

StatusCallback = Callable[[str], None]


@dataclass
class PipelineConfig:
    client_dir: Path
    template_path: Path
    output_dir: Path = Path("out")
    model: str = "mistral:latest"
    host: str = "http://localhost:11434"
    topk: int = 10
    temperature: float = 0.2
    top_p: float = 0.9
    include_filters: List[str] = field(default_factory=list)
    exclude_filters: List[str] = field(default_factory=list)
    fields: Optional[List[Dict[str, Any]]] = None
    name: str = ""
    surname: str = ""
    civility: str = "Monsieur"
    force_reextract: bool = False
    enable_soffice: bool = False
    report_filename: Optional[str] = None
    debug_subdir: str = "debug"
    export_pdf: bool = False


@dataclass
class PipelineResult:
    job_dir: Path
    extracted_path: Path
    answers_path: Path
    report_path: Path
    pdf_path: Optional[Path]
    debug_dir: Path
    elapsed_seconds: float
    steps: List[Dict[str, Any]]


def slugify(value: str) -> str:
    nfkd = unicodedata.normalize("NFKD", value)
    base = "".join(c for c in nfkd if not unicodedata.combining(c))
    slug = "".join(ch if ch.isalnum() else "_" for ch in base.lower())
    slug = "_".join(filter(None, slug.split("_")))
    return slug or "client"


class RapportOrchestrator:
    def __init__(self, status_callback: Optional[StatusCallback] = None) -> None:
        self.status_callback = status_callback
        self.logger = logging.getLogger("RapportOrchestrator")

    # Public API -------------------------------------------------

    def resolve_config(self, config: PipelineConfig) -> PipelineConfig:
        return self._prepare_config(config)

    def ensure_job_dir(self, config: PipelineConfig, existing: Optional[Path] = None) -> Path:
        if existing is not None:
            job_dir = Path(existing).expanduser().resolve()
            job_dir.mkdir(parents=True, exist_ok=True)
            self._log(f"Réutilisation du répertoire: {job_dir}")
            return job_dir
        return self._create_job_dir(config)

    def extract_sources(
        self,
        config: PipelineConfig,
        job_dir: Path,
        *,
        force: Optional[bool] = None,
    ) -> tuple[Path, Dict[str, Any], bool]:
        files = walk_files(config.client_dir)
        return self._handle_extraction(
            config,
            job_dir,
            files,
            force_override=config.force_reextract if force is None else force,
        )

    def generate_fields(
        self,
        config: PipelineConfig,
        job_dir: Path,
        payload: Dict[str, Any],
        *,
        progress_callback: Optional[Callable[[str, str, str], None]] = None,
    ) -> tuple[Path, Dict[str, Any]]:
        return self._handle_generation(config, job_dir, payload, progress_callback=progress_callback)

    def render_docx(
        self,
        config: PipelineConfig,
        job_dir: Path,
        answers: Dict[str, Any],
    ) -> Path:
        return self._handle_render(config, job_dir, answers)

    def export_pdf(self, docx_path: Path, output_dir: Optional[Path] = None) -> Path:
        self._log("Conversion DOCX -> PDF via LibreOffice...")
        pdf_path = docx_to_pdf(docx_path, output_dir)
        self._log(f"PDF généré -> {pdf_path}")
        return pdf_path

    def run(self, config: PipelineConfig) -> PipelineResult:
        start = time.time()
        self._log("Démarrage du pipeline...")

        resolved_cfg = self.resolve_config(config)
        job_dir = self.ensure_job_dir(resolved_cfg)
        steps: List[Dict[str, Any]] = []

        extracted_path, payload, reused_extraction = self.extract_sources(
            resolved_cfg, job_dir, force=resolved_cfg.force_reextract
        )
        steps.append({
            "name": "extraction",
            "path": str(extracted_path),
            "reused": reused_extraction,
            "documents": len(payload.get("documents", [])),
        })

        answers_path, answers = self.generate_fields(resolved_cfg, job_dir, payload)
        steps.append({
            "name": "generation",
            "path": str(answers_path),
            "fields": len(answers),
        })

        report_path = self.render_docx(resolved_cfg, job_dir, answers)
        steps.append({"name": "render", "path": str(report_path)})

        pdf_path: Optional[Path] = None
        if resolved_cfg.export_pdf:
            pdf_path = self.export_pdf(report_path)
            steps.append({"name": "pdf", "path": str(pdf_path)})

        elapsed = time.time() - start
        self._log(f"Pipeline terminé en {elapsed:.1f}s")

        return PipelineResult(
            job_dir=job_dir,
            extracted_path=extracted_path,
            answers_path=answers_path,
            report_path=report_path,
            pdf_path=pdf_path,
            debug_dir=job_dir / resolved_cfg.debug_subdir,
            elapsed_seconds=elapsed,
            steps=steps,
        )

    # Steps ------------------------------------------------------

    def _handle_extraction(
        self,
        config: PipelineConfig,
        job_dir: Path,
        files: List[Path],
        force_override: Optional[bool] = None,
    ) -> tuple[Path, Dict[str, Any], bool]:
        extracted_path = job_dir / "extracted.json"

        if not files:
            raise FileNotFoundError(f"Aucun fichier trouvé dans {config.client_dir}")

        force_flag = config.force_reextract if force_override is None else force_override
        needs_extraction = self._needs_extraction(files, extracted_path, force_flag)
        if not needs_extraction:
            self._log("Extraction déjà à jour, réutilisation des données existantes.")
            payload = json.loads(extracted_path.read_text(encoding="utf-8"))
            return extracted_path, payload, True

        self._log(f"Extraction des sources depuis {config.client_dir}...")
        payload = extract_sources(
            config.client_dir,
            enable_soffice=config.enable_soffice,
        )
        if not payload.get("documents"):
            self._log("⚠️ Aucun document exploitable n'a été trouvé dans ce dossier.")

        extracted_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self._log(f"Extraction écrite -> {extracted_path}")
        return extracted_path, payload, False

    def _handle_generation(
        self,
        config: PipelineConfig,
        job_dir: Path,
        payload: Dict[str, Any],
        *,
        progress_callback: Optional[Callable[[str, str, str], None]] = None,
    ) -> tuple[Path, Dict[str, Any]]:
        answers_path = job_dir / "answers.json"
        debug_dir = job_dir / config.debug_subdir
        self._log("Génération des champs via le LLM...")
        self._log(f"Cible LLM : {config.model} @ {config.host}")

        answers = generate_fields(
            payload,
            model=config.model,
            host=config.host,
            topk=config.topk,
            temperature=config.temperature,
            top_p=config.top_p,
            exclude_filters=config.exclude_filters,
            include_filters=config.include_filters,
            debug_dir=debug_dir,
            fields=config.fields or DEFAULT_FIELDS,
            status_callback=self._log,
            progress_callback=progress_callback,
        )

        answers_path.parent.mkdir(parents=True, exist_ok=True)
        answers_path.write_text(json.dumps(answers, ensure_ascii=False, indent=2), encoding="utf-8")

        self._log(f"Champs générés -> {answers_path}")
        return answers_path, answers

    def _handle_render(
        self,
        config: PipelineConfig,
        job_dir: Path,
        answers: Dict[str, Any],
    ) -> Path:
        report_name = config.report_filename or f"rapport_{slugify(config.client_dir.name)}.docx"
        report_path = job_dir / report_name
        self._log("Génération du DOCX final...")

        render_report(
            template=config.template_path,
            answers=answers,
            output=report_path,
            name=config.name,
            surname=config.surname,
            civility=config.civility,
        )

        self._log(f"DOCX généré -> {report_path}")
        return report_path

    # Helpers ----------------------------------------------------

    def _prepare_config(self, config: PipelineConfig) -> PipelineConfig:
        config.client_dir = Path(config.client_dir).expanduser().resolve()
        config.template_path = Path(config.template_path).expanduser().resolve()
        config.output_dir = Path(config.output_dir).expanduser().resolve()
        if not config.client_dir.exists():
            raise FileNotFoundError(f"Dossier client introuvable: {config.client_dir}")
        if not config.template_path.exists():
            raise FileNotFoundError(f"Template introuvable: {config.template_path}")
        if not config.fields:
            placeholders = extract_placeholders_from_docx(config.template_path)
            if placeholders:
                config.fields = build_field_specs(placeholders, DEFAULT_FIELDS)
                self._log(f"{len(config.fields)} champs détectés dans le template.")
            else:
                config.fields = list(DEFAULT_FIELDS)
        return config

    def _create_job_dir(self, config: PipelineConfig) -> Path:
        slug = slugify(config.client_dir.name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_dir = config.output_dir / f"{slug}_{timestamp}"
        job_dir.mkdir(parents=True, exist_ok=True)
        self._log(f"Répertoire de sortie: {job_dir}")
        return job_dir

    def _needs_extraction(self, files: List[Path], extracted_path: Path, force: bool) -> bool:
        if force or not extracted_path.exists():
            return True
        extracted_mtime = extracted_path.stat().st_mtime
        for path in files:
            try:
                if path.stat().st_mtime > extracted_mtime:
                    return True
            except FileNotFoundError:
                return True
        return False

    def _log(self, message: str) -> None:
        self.logger.info(message)
        if self.status_callback:
            self.status_callback(message)
