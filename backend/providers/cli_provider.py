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
        error_msg = f"Unknown CLI '{cli_name}'. Available: {list(CLI_COMMANDS.keys())}"
        print(f"Error: {error_msg}")
        return {'error': True, 'content': f"Error: {error_msg}"}

    config = CLI_COMMANDS[cli_name]
    command = config["command"]
    args = config.get("args", [])
    cli_timeout = config.get("timeout", timeout)
    use_output_file = config.get("use_output_file", False)
    use_positional_arg = config.get("use_positional_arg", False)
    model_arg = config.get("model_arg", [])
    output_format_arg = config.get("output_format_arg", [])
    prompt_flag = config.get("prompt_flag", None)

    # Check if CLI exists
    if not shutil.which(command):
        error_msg = f"CLI command '{command}' not found in PATH"
        print(f"Error: {error_msg}")
        return {'error': True, 'content': f"Error: {error_msg}"}

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
        cmd = [command] + args + model_arg + output_format_arg

        # Determine how to pass the prompt
        if use_output_file:
            # For CLIs that use output file (like Codex), add the -o flag
            output_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            output_file.close()
            cmd.extend(["-o", output_file.name])
            # Codex takes prompt as argument, not stdin
            cmd.append(prompt)
            stdin_input = None
        elif prompt_flag:
            # For CLIs that take prompt as a flag value (e.g., -p "prompt")
            cmd.extend([prompt_flag, prompt])
            stdin_input = None
        elif use_positional_arg:
            # For CLIs that take prompt as positional argument
            cmd.append(prompt)
            stdin_input = None
        else:
            # Default: pass prompt via stdin
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
            stderr_text = stderr.decode('utf-8', errors='replace')
            # Try to extract a meaningful error message from stderr
            error_lines = [l for l in stderr_text.split('\n') if 'error' in l.lower() or 'Error' in l]
            if error_lines:
                error_msg = error_lines[0].strip()
            else:
                error_msg = stderr_text[:200] if stderr_text else f"Exit code {process.returncode}"
            print(f"CLI '{cli_name}' failed with code {process.returncode}: {stderr_text}")
            return {'error': True, 'content': f"Error: CLI '{cli_name}' failed - {error_msg}"}

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
        error_msg = f"CLI '{cli_name}' timed out after {cli_timeout}s"
        print(error_msg)
        return {'error': True, 'content': f"Error: {error_msg}"}
    except Exception as e:
        error_msg = f"Error executing CLI '{cli_name}': {e}"
        print(error_msg)
        return {'error': True, 'content': f"Error: {error_msg}"}
    finally:
        # Clean up temp file
        if output_file and os.path.exists(output_file.name):
            os.unlink(output_file.name)
