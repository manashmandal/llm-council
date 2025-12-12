"""Anthropic/Claude API client for direct model queries."""

import httpx
from typing import List, Dict, Any, Optional
from ..config import ANTHROPIC_API_KEY, ANTHROPIC_API_URL


async def query_anthropic(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query Anthropic API directly.

    Args:
        model: Model name (e.g., "claude-sonnet-4-20250514", "claude-opus-4-20250514")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'content' and optional 'reasoning_details', or None if failed
    """
    if not ANTHROPIC_API_KEY:
        print(f"Error: ANTHROPIC_API_KEY not configured")
        return None

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }

    # Convert OpenAI-style messages to Anthropic format
    # Extract system message if present
    system_content = None
    anthropic_messages = []

    for msg in messages:
        if msg['role'] == 'system':
            system_content = msg['content']
        else:
            anthropic_messages.append({
                'role': msg['role'],
                'content': msg['content']
            })

    payload = {
        "model": model,
        "messages": anthropic_messages,
        "max_tokens": 8192,
    }

    if system_content:
        payload["system"] = system_content

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                ANTHROPIC_API_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()

            # Extract text content from Anthropic response format
            # Response content is an array of content blocks
            content_blocks = data.get('content', [])
            text_content = ""
            reasoning_details = None

            for block in content_blocks:
                if block.get('type') == 'text':
                    text_content += block.get('text', '')
                elif block.get('type') == 'thinking':
                    # Extended thinking (for Claude with thinking enabled)
                    reasoning_details = block.get('thinking', '')

            return {
                'content': text_content,
                'reasoning_details': reasoning_details
            }

    except httpx.HTTPStatusError as e:
        print(f"Anthropic API error for {model}: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        print(f"Error querying Anthropic model {model}: {e}")
        return None
