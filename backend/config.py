"""Configuration for the LLM Council."""

import os
import json
from pathlib import Path
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

# Data directory for storage
DATA_DIR = "data/conversations"
CONFIG_FILE = "data/council_config.json"

# Default council configuration
DEFAULT_COUNCIL_MODELS = [
    "cli:codex",
    "cli:gemini",
]
DEFAULT_CHAIRMAN_MODEL = "anthropic/claude-opus-4-5-20251101"


def _ensure_config_dir():
    """Ensure the data directory exists."""
    Path("data").mkdir(exist_ok=True)


def load_council_config():
    """Load council configuration from file, or return defaults."""
    _ensure_config_dir()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get('council_models', DEFAULT_COUNCIL_MODELS), config.get('chairman_model', DEFAULT_CHAIRMAN_MODEL)
        except (json.JSONDecodeError, IOError):
            pass
    return DEFAULT_COUNCIL_MODELS.copy(), DEFAULT_CHAIRMAN_MODEL


def save_council_config(council_models: list, chairman_model: str):
    """Save council configuration to file."""
    _ensure_config_dir()
    config = {
        'council_models': council_models,
        'chairman_model': chairman_model
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def get_council_models():
    """Get current council models."""
    models, _ = load_council_config()
    return models


def get_chairman_model():
    """Get current chairman model."""
    _, chairman = load_council_config()
    return chairman


# For backward compatibility - these will be loaded dynamically
COUNCIL_MODELS, CHAIRMAN_MODEL = load_council_config()

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
        "args": ["--allowed-tools", "google_search"],  # Enable Google Search grounding
        "model_arg": ["-m", "gemini-2.5-pro"],  # Specify model explicitly
        "output_format_arg": ["--output-format", "text"],  # Ensure text output
        "prompt_flag": "-p",  # Flag to pass prompt as argument value
        "timeout": 120,
    },
    "claude": {
        "command": "claude",
        "args": ["-p", "--allowedTools", "WebSearch,WebFetch"],  # Enable web search tools
        "timeout": 120,
    },
    "codex": {
        "command": "codex",
        "args": ["exec", "--skip-git-repo-check", "--enable", "web_search_request"],  # Enable web search
        "timeout": 120,
        "use_output_file": True,  # Codex writes clean output to -o file
    },
}
