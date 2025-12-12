"""OpenAI API client for direct model queries."""

import httpx
from typing import List, Dict, Any, Optional
from ..config import OPENAI_API_KEY, OPENAI_API_URL


async def query_openai(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query OpenAI API directly.

    Args:
        model: Model name (e.g., "gpt-4o", "gpt-4o-mini", "o1")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'content' and optional 'reasoning_details', or None if failed
    """
    if not OPENAI_API_KEY:
        print(f"Error: OPENAI_API_KEY not configured")
        return None

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                OPENAI_API_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            message = data['choices'][0]['message']

            return {
                'content': message.get('content'),
                'reasoning_details': message.get('reasoning_details')  # For o1 models
            }

    except httpx.HTTPStatusError as e:
        print(f"OpenAI API error for {model}: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        print(f"Error querying OpenAI model {model}: {e}")
        return None
