"""Module extractors - Support extraction multi-format."""

from .msg_extractor import (
    MSG_SUPPORT_AVAILABLE,
    extract_msg_to_text,
    extract_msg_safe,
)

__all__ = [
    "MSG_SUPPORT_AVAILABLE",
    "extract_msg_to_text",
    "extract_msg_safe",
]
