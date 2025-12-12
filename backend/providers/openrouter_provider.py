"""OpenRouter API client for proxied model queries."""

import httpx
from typing import List, Dict, Any, Optional
from ..config import OPENROUTER_API_KEY, OPENROUTER_API_URL


async def query_openrouter(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query a model via OpenRouter API.

    Args:
        model: OpenRouter model identifier (e.g., "google/gemini-2.5-pro", "x-ai/grok-3")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'content' and optional 'reasoning_details', or None if failed
    """
    if not OPENROUTER_API_KEY:
        print(f"Error: OPENROUTER_API_KEY not configured")
        return None

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            message = data['choices'][0]['message']

            return {
                'content': message.get('content'),
                'reasoning_details': message.get('reasoning_details')
            }

    except httpx.HTTPStatusError as e:
        print(f"OpenRouter API error for {model}: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        print(f"Error querying OpenRouter model {model}: {e}")
        return None
