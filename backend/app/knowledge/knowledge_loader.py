from __future__ import annotations

import json
import os
import re
import logging
from typing import Any

logger = logging.getLogger(__name__)


def resolve_file_path(file_path: str) -> str:
    if os.path.isabs(file_path) and os.path.exists(file_path):
        return file_path

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidate_paths = [
        os.path.join(base_dir, file_path),
        os.path.join(os.path.dirname(base_dir), file_path),
        file_path,
    ]
    for p in candidate_paths:
        if os.path.exists(p):
            return p
    return file_path


def load_knowledge_chunks(file_path: str) -> list[str]:
    """
    Loads knowledge chunks from either a JSON file (business_knowledge.json)
    or a Markdown file (knowledge.md).
    """
    resolved = resolve_file_path(file_path)
    if not os.path.exists(resolved):
        logger.error("Knowledge file not found at path: %s", resolved)
        raise FileNotFoundError(f"Không tìm thấy file tri thức tại: {resolved}")

    if resolved.endswith(".json"):
        return _load_from_json(resolved)
    else:
        return _load_from_markdown(resolved)


def _load_from_json(file_path: str) -> list[str]:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunks: list[str] = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                topic = item.get("topic", "").strip()
                desc = item.get("description", "").strip()
                if topic and desc:
                    chunks.append(f"{topic}:\n{desc}")
                elif desc:
                    chunks.append(desc)
                elif topic:
                    chunks.append(topic)
            elif isinstance(item, str) and item.strip():
                chunks.append(item.strip())
    elif isinstance(data, dict):
        for k, v in data.items():
            chunks.append(f"{k}: {str(v)}")

    logger.info("Loaded %d business knowledge chunks from JSON %s", len(chunks), file_path)
    return chunks



def _load_from_markdown(file_path: str) -> list[str]:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    raw_sections = re.split(r"\n(?=-\s+)", content)
    chunks = []

    for section in raw_sections:
        cleaned = section.strip()
        if cleaned and len(cleaned) > 10:
            if cleaned.startswith("- "):
                cleaned_text = cleaned[2:].strip()
            else:
                cleaned_text = cleaned
            if cleaned_text:
                chunks.append(cleaned_text)

    logger.info("Loaded %d knowledge chunks from Markdown %s", len(chunks), file_path)
    return chunks


def load_knowledge_chunks_from_markdown(file_path: str) -> list[str]:
    """Backward compatibility alias."""
    return load_knowledge_chunks(file_path)

