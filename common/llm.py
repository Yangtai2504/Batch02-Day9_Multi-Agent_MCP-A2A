"""Shared LLM factory for all agents — Gemini 2.5 Flash via Vertex AI."""

import os
from typing import Any

from langchain_google_vertexai import ChatVertexAI


def extract_text(content: Any) -> str:
    """Extract plain text from LLM response content.

    Gemini 2.5 Flash returns content as a list of blocks when thinking is active.
    This helper normalises it back to a plain string.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return str(content)


def get_llm() -> ChatVertexAI:
    """Return a ChatVertexAI client using Gemini 2.5 Flash."""
    return ChatVertexAI(
        model=os.getenv("VERTEX_MODEL", "gemini-2.5-flash"),
        project=os.getenv("VERTEX_PROJECT", "vinuni-project"),
        location=os.getenv("VERTEX_LOCATION", "us-central1"),
        temperature=0.3,
        model_kwargs={"thinking_config": {"thinking_budget": 0}},
    )
