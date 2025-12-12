"""
Multi-provider LLM API clients.

This module provides a unified interface to query models from different providers:
- OpenAI (direct API)
- Anthropic/Claude (direct API)
- OpenRouter (proxy for other providers like Google, xAI, etc.)
- CLI (local CLI tools like gemini, claude, openai)

Usage:
    from backend.providers import query_model, query_models_parallel

    # Query via API
    response = await query_model("openai/gpt-4o", messages)

    # Query via CLI
    response = await query_model("cli:gemini", messages)

    # Query multiple models in parallel
    responses = await query_models_parallel(["openai/gpt-4o", "cli:gemini"], messages)
"""

from .router import query_model, query_models_parallel

__all__ = ["query_model", "query_models_parallel"]
