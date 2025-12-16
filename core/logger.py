"""Configuration centralisée du logging."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

# Niveaux de log par module
MODULE_LEVELS = {
    "core.extract": logging.DEBUG,
    "core.generate": logging.INFO,
    "core.render": logging.INFO,
    "core.context": logging.INFO,
}

DEFAULT_LEVEL = logging.INFO


class ColoredFormatter(logging.Formatter):
    """Formatter avec couleurs pour la console."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Vert
        "WARNING": "\033[33m",  # Jaune
        "ERROR": "\033[31m",  # Rouge
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Formate avec couleur selon le niveau."""
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]
        record.levelname = f"{color}{record.levelname}{reset}"
        return super().format(record)


def setup_logging(
    log_file: Path | None = None,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    format_json: bool = False,
) -> None:
    """
    Configure le système de logging.
    
    Args:
        log_file: Chemin du fichier de log (optionnel)
        console_level: Niveau de log pour la console
        file_level: Niveau de log pour le fichier
        format_json: Si True, log en JSON (pour parsing automatique)
    """
    # Format par défaut
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture tout
    root_logger.handlers.clear()  # Nettoyer handlers existants

    # Handler console avec couleurs
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_formatter = ColoredFormatter(log_format, datefmt=date_format)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Handler fichier si spécifié
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(file_level)
        
        if format_json:
            file_formatter = JsonFormatter()
        else:
            file_formatter = logging.Formatter(log_format, datefmt=date_format)
        
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Configurer niveaux par module
    for module_name, level in MODULE_LEVELS.items():
        logger = logging.getLogger(module_name)
        logger.setLevel(level)

    # Réduire verbosité des libs externes
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)


class JsonFormatter(logging.Formatter):
    """Formatter JSON pour logs structurés."""

    def format(self, record: logging.LogRecord) -> str:
        """Formate en JSON."""
        import json

        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Ajouter exception si présente
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Ajouter extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
            ]:
                log_data[key] = value

        return json.dumps(log_data, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    """
    Récupère un logger configuré.
    
    Args:
        name: Nom du logger (généralement __name__)
        
    Returns:
        Logger configuré
    """
    return logging.getLogger(name)


# Configuration par défaut au chargement du module
if not logging.getLogger().handlers:
    setup_logging()
