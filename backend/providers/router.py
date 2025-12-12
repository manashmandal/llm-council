"""
Unified provider router for multi-provider LLM queries.

Routes model queries to the appropriate API based on model identifier:
- "openai/model-name" -> Direct OpenAI API
- "anthropic/model-name" -> Direct Anthropic API
- "openrouter:provider/model-name" -> OpenRouter (explicit)
- "cli:name" -> Local CLI tool (e.g., cli:gemini, cli:claude)
- "other-provider/model-name" -> OpenRouter (fallback)
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple

from ..config import DIRECT_PROVIDERS
from .openai_provider import query_openai
from .anthropic_provider import query_anthropic
from .openrouter_provider import query_openrouter
from .cli_provider import query_cli


def parse_model_identifier(model: str) -> Tuple[str, str, str]:
    """
    Parse a model identifier into provider routing info.

    Args:
        model: Model identifier (e.g., "openai/gpt-4o", "openrouter:google/gemini-2.5-pro", "cli:gemini")

    Returns:
        Tuple of (route_to, provider, model_name) where:
        - route_to: "openai", "anthropic", "openrouter", or "cli"
        - provider: The provider name (e.g., "openai", "google", or CLI name)
        - model_name: The model name without provider prefix
    """
    # Check for CLI prefix
    if model.startswith("cli:"):
        cli_name = model[4:]  # Remove "cli:" prefix
        return ("cli", cli_name, cli_name)

    # Check for explicit openrouter: prefix
    if model.startswith("openrouter:"):
        remaining = model[11:]  # Remove "openrouter:" prefix
        if "/" in remaining:
            provider, model_name = remaining.split("/", 1)
        else:
            provider, model_name = "unknown", remaining
        return ("openrouter", provider, model_name)

    # Parse standard provider/model format
    if "/" in model:
        provider, model_name = model.split("/", 1)
    else:
        # No provider prefix, assume it's a model name for OpenRouter
        provider, model_name = "unknown", model

    # Route to direct API if provider supports it
    if provider in DIRECT_PROVIDERS:
        return (provider, provider, model_name)

    # Fallback to OpenRouter
    return ("openrouter", provider, model_name)


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query a model, automatically routing to the appropriate provider.

    Args:
        model: Model identifier (e.g., "openai/gpt-4o", "anthropic/claude-sonnet-4-20250514")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'content' and optional 'reasoning_details', or None if failed
    """
    route_to, provider, model_name = parse_model_identifier(model)

    if route_to == "cli":
        return await query_cli(provider, messages, timeout)
    elif route_to == "openai":
        return await query_openai(model_name, messages, timeout)
    elif route_to == "anthropic":
        return await query_anthropic(model_name, messages, timeout)
    else:
        # OpenRouter - reconstruct full model identifier without prefix
        if model.startswith("openrouter:"):
            openrouter_model = model[11:]  # Remove "openrouter:" prefix
        else:
            openrouter_model = model
        return await query_openrouter(openrouter_model, messages, timeout)


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]]
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel, routing each to the appropriate provider.

    Args:
        models: List of model identifiers
        messages: List of message dicts to send to each model

    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    # Create tasks for all models
    tasks = [query_model(model, messages) for model in models]

    # Wait for all to complete
    responses = await asyncio.gather(*tasks)

    # Map models to their responses
    return {model: response for model, response in zip(models, responses)}
