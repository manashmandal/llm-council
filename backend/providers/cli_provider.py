"""CLI-based model provider for local CLI tool access."""

import asyncio
import shutil
from typing import List, Dict, Any, Optional
from ..config import CLI_COMMANDS


async def query_cli(
    cli_name: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query a model via local CLI tool.

    Args:
        cli_name: CLI identifier (e.g., "gemini", "claude", "openai")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'content', or None if failed
    """
    if cli_name not in CLI_COMMANDS:
        print(f"Error: Unknown CLI '{cli_name}'. Available: {list(CLI_COMMANDS.keys())}")
        return None

    config = CLI_COMMANDS[cli_name]
    command = config["command"]
    args = config.get("args", [])
    cli_timeout = config.get("timeout", timeout)

    # Check if CLI exists
    if not shutil.which(command):
        print(f"Error: CLI command '{command}' not found in PATH")
        return None

    # Convert messages to a single prompt
    # For simplicity, concatenate all messages with role prefixes
    prompt_parts = []
    for msg in messages:
        role = msg['role']
        content = msg['content']
        if role == 'system':
            prompt_parts.append(f"System: {content}")
        elif role == 'user':
            prompt_parts.append(f"{content}")
        elif role == 'assistant':
            prompt_parts.append(f"Assistant: {content}")

    prompt = "\n\n".join(prompt_parts)

    try:
        # Build command
        cmd = [command] + args

        # Run CLI with prompt via stdin
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(input=prompt.encode('utf-8')),
            timeout=cli_timeout
        )

        if process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='replace')
            print(f"CLI '{cli_name}' failed with code {process.returncode}: {error_msg}")
            return None

        output = stdout.decode('utf-8', errors='replace').strip()

        return {
            'content': output,
            'reasoning_details': None
        }

    except asyncio.TimeoutError:
        print(f"CLI '{cli_name}' timed out after {cli_timeout}s")
        return None
    except Exception as e:
        print(f"Error executing CLI '{cli_name}': {e}")
        return None
