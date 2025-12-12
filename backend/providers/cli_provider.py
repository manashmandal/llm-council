"""CLI-based model provider for local CLI tool access."""

import asyncio
import shutil
import tempfile
import os
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
        cli_name: CLI identifier (e.g., "gemini", "claude", "codex")
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
    use_output_file = config.get("use_output_file", False)

    # Check if CLI exists
    if not shutil.which(command):
        print(f"Error: CLI command '{command}' not found in PATH")
        return None

    # Convert messages to a single prompt
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

    output_file = None
    try:
        # Build command
        cmd = [command] + args

        # For CLIs that use output file (like Codex), add the -o flag
        if use_output_file:
            output_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            output_file.close()
            cmd.extend(["-o", output_file.name])
            # Codex takes prompt as argument, not stdin
            cmd.append(prompt)
            stdin_input = None
        else:
            stdin_input = prompt.encode('utf-8')

        # Run CLI
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE if stdin_input else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(input=stdin_input),
            timeout=cli_timeout
        )

        if process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='replace')
            print(f"CLI '{cli_name}' failed with code {process.returncode}: {error_msg}")
            return None

        # Get output from file or stdout
        if use_output_file and output_file:
            with open(output_file.name, 'r') as f:
                output = f.read().strip()
        else:
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
    finally:
        # Clean up temp file
        if output_file and os.path.exists(output_file.name):
            os.unlink(output_file.name)
