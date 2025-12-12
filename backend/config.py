"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# API Keys for different providers
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# API endpoints
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

# Provider detection: determines which API to use based on model identifier
# Format: "provider/model" uses direct API, "openrouter:provider/model" forces OpenRouter
# Special: "cli:<name>" uses local CLI tool instead of API
# Examples:
#   "openai/gpt-5.2" -> Direct OpenAI API
#   "anthropic/claude-opus-4-5-20251101" -> Direct Anthropic API
#   "openrouter:google/gemini-3-pro-preview" -> OpenRouter (no direct API)
#   "cli:gemini" -> Local Gemini CLI (stdin pipe)
#   "cli:claude" -> Local Claude CLI

# Council members - list of model identifiers
# Use direct provider format for OpenAI/Anthropic, prefix with "openrouter:" for others,
# or "cli:" for local CLI tools
COUNCIL_MODELS = [
    "cli:codex",                              # OpenAI Codex CLI (gpt-5.2)
    "cli:claude",                             # Claude CLI
    "cli:gemini",                             # Gemini CLI
    "anthropic/claude-opus-4-5-20251101",     # Direct Anthropic API (latest Opus)
]

# Chairman model - synthesizes final response
CHAIRMAN_MODEL = "cli:claude"

# Data directory for conversation storage
DATA_DIR = "data/conversations"

# Supported direct providers (others fall back to OpenRouter)
DIRECT_PROVIDERS = ["openai", "anthropic"]

# CLI-based model access configuration
# Format: "cli:<cli_name>" in model identifier routes to CLI execution
# Examples:
#   "cli:gemini" -> Executes: echo "<prompt>" | gemini
#   "cli:claude" -> Executes: echo "<prompt>" | claude
#   "cli:openai" -> Executes: echo "<prompt>" | openai
#
# Each CLI config specifies:
#   - command: The CLI command to execute
#   - args: Additional arguments (prompt is passed via stdin)
#   - timeout: Max execution time in seconds
CLI_COMMANDS = {
    "gemini": {
        "command": "gemini",
        "args": [],
        "timeout": 120,
    },
    "claude": {
        "command": "claude",
        "args": ["-p"],  # -p flag for prompt mode (non-interactive)
        "timeout": 120,
    },
    "codex": {
        "command": "codex",
        "args": ["exec", "--skip-git-repo-check"],
        "timeout": 120,
        "use_output_file": True,  # Codex writes clean output to -o file
    },
}
