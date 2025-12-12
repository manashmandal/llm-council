# CLAUDE.md - Technical Notes for LLM Council

This file contains technical details, architectural decisions, and important implementation notes for future development sessions.

## Project Overview

LLM Council is a 3-stage deliberation system where multiple LLMs collaboratively answer user questions. The key innovation is anonymized peer review in Stage 2, preventing models from playing favorites.

## Architecture

### Backend Structure (`backend/`)

**`config.py`**
- Multi-provider API key configuration: `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`
- Dynamic config loading/saving via `load_council_config()`, `save_council_config()`
- `get_council_models()` and `get_chairman_model()` for runtime config access
- `CLI_COMMANDS` dict configures local CLI tools (gemini, claude, codex)
- Config persisted to `data/council_config.json`
- Backend runs on **port 8001** (NOT 8000 - user had another app on 8000)

**`backend/providers/`** - Multi-Provider Module
- **`router.py`**: Unified routing based on model identifier format:
  - `openai/model-name` → Direct OpenAI API
  - `anthropic/model-name` → Direct Anthropic API
  - `openrouter:provider/model-name` → OpenRouter (explicit)
  - `cli:name` → Local CLI tool (gemini, claude, codex)
  - `provider/model-name` → OpenRouter (fallback)
- **`openai_provider.py`**: Direct OpenAI API client
- **`anthropic_provider.py`**: Direct Anthropic API client (with message format conversion)
- **`openrouter_provider.py`**: OpenRouter proxy API client
- **`cli_provider.py`**: CLI-based model execution via subprocess
- All providers return dict with 'content' and optional 'reasoning_details'
- Graceful degradation: returns None on failure, continues with successful responses

**`council.py`** - The Core Logic
- `stage1_collect_responses()`: Parallel queries to all council models
- `stage2_collect_rankings()`:
  - Anonymizes responses as "Response A, B, C, etc."
  - Creates `label_to_model` mapping for de-anonymization
  - Prompts models to evaluate and rank (with strict format requirements)
  - Returns tuple: (rankings_list, label_to_model_dict)
  - Each ranking includes both raw text and `parsed_ranking` list
- `stage3_synthesize_final()`: Chairman synthesizes from all responses + rankings
- `parse_ranking_from_text()`: Extracts "FINAL RANKING:" section, handles both numbered lists and plain format
- `calculate_aggregate_rankings()`: Computes average rank position across all peer evaluations

**`storage.py`**
- JSON-based conversation storage in `data/conversations/`
- Each conversation: `{id, created_at, messages[]}`
- Assistant messages contain: `{role, stage1, stage2, stage3}`
- `delete_conversation()`: Removes conversation file from storage
- Note: metadata (label_to_model, aggregate_rankings) is NOT persisted to storage, only returned via API

**`main.py`**
- FastAPI app with CORS enabled for localhost:5173, localhost:5174, and localhost:3000
- **API Endpoints**:
  - `GET /api/health`: Health check - reports API key status, CLI tool availability, model readiness
  - `GET /api/config`: Get current council/chairman configuration
  - `POST /api/config`: Update council/chairman configuration (persists to file)
  - `DELETE /api/conversations/{id}`: Delete a conversation
  - `POST /api/conversations/{id}/message`: Returns metadata in addition to stages
- Metadata includes: label_to_model mapping and aggregate_rankings

### Frontend Structure (`frontend/src/`)

**`App.jsx`**
- Main orchestration: manages conversations list and current conversation
- Handles message sending and metadata storage
- Important: metadata is stored in the UI state for display but not persisted to backend JSON

**`components/ChatInterface.jsx`**
- Multiline textarea (3 rows, resizable)
- Enter to send, Shift+Enter for new line
- User messages wrapped in markdown-content class for padding

**`components/Stage1.jsx`**
- Tab view of individual model responses
- ReactMarkdown rendering with markdown-content wrapper

**`components/Stage2.jsx`**
- **Critical Feature**: Tab view showing RAW evaluation text from each model
- De-anonymization happens CLIENT-SIDE for display (models receive anonymous labels)
- Shows "Extracted Ranking" below each evaluation so users can validate parsing
- Aggregate rankings shown with average position and vote count
- Explanatory text clarifies that boldface model names are for readability only

**`components/Stage3.jsx`**
- Final synthesized answer from chairman
- Green-tinted background (#f0fff0) to highlight conclusion

**Styling (`*.css`)**
- Light mode theme (not dark mode)
- Primary color: #4a90e2 (blue)
- Global markdown styling in `index.css` with `.markdown-content` class
- 12px padding on all markdown content to prevent cluttered appearance

## Key Design Decisions

### Stage 2 Prompt Format
The Stage 2 prompt is very specific to ensure parseable output:
```
1. Evaluate each response individually first
2. Provide "FINAL RANKING:" header
3. Numbered list format: "1. Response C", "2. Response A", etc.
4. No additional text after ranking section
```

This strict format allows reliable parsing while still getting thoughtful evaluations.

### De-anonymization Strategy
- Models receive: "Response A", "Response B", etc.
- Backend creates mapping: `{"Response A": "openai/gpt-5.1", ...}`
- Frontend displays model names in **bold** for readability
- Users see explanation that original evaluation used anonymous labels
- This prevents bias while maintaining transparency

### Error Handling Philosophy
- Continue with successful responses if some models fail (graceful degradation)
- Never fail the entire request due to single model failure
- Log errors but don't expose to user unless all models fail

### UI/UX Transparency
- All raw outputs are inspectable via tabs
- Parsed rankings shown below raw text for validation
- Users can verify system's interpretation of model outputs
- This builds trust and allows debugging of edge cases

## Important Implementation Details

### Relative Imports
All backend modules use relative imports (e.g., `from .config import ...`) not absolute imports. This is critical for Python's module system to work correctly when running as `python -m backend.main`.

### Port Configuration
- Backend: 8001 (changed from 8000 to avoid conflict)
- Frontend: 5173 (Vite default)
- Update both `backend/main.py` and `frontend/src/api.js` if changing

### Markdown Rendering
All ReactMarkdown components must be wrapped in `<div className="markdown-content">` for proper spacing. This class is defined globally in `index.css`.

### Model Configuration
Models are configured via `data/council_config.json` (with defaults in `backend/config.py`). Configuration can be changed at runtime via the `/api/config` endpoint. Chairman can be same or different from council members.

**Model Identifier Formats**:
- `openai/gpt-4o` → Direct OpenAI API
- `anthropic/claude-sonnet-4-20250514` → Direct Anthropic API
- `openrouter:google/gemini-2.5-pro` → OpenRouter (explicit)
- `google/gemini-3-pro-preview` → OpenRouter (fallback for unknown providers)
- `cli:gemini` → Local Gemini CLI
- `cli:claude` → Local Claude CLI
- `cli:codex` → Local Codex CLI (uses output file mode)

## Common Gotchas

1. **Module Import Errors**: Always run backend as `python -m backend.main` from project root, not from backend directory
2. **CORS Issues**: Frontend must match allowed origins in `main.py` CORS middleware
3. **Ranking Parse Failures**: If models don't follow format, fallback regex extracts any "Response X" patterns in order
4. **Missing Metadata**: Metadata is ephemeral (not persisted), only available in API responses

## CLI Provider Setup

The system supports local CLI tools as model providers. Each CLI must be installed and accessible in PATH.

**Supported CLIs**:
- `gemini`: Google's Gemini CLI (prompt via stdin)
- `claude`: Anthropic's Claude CLI (uses `-p` flag for prompt mode)
- `codex`: OpenAI's Codex CLI (uses output file via `-o` flag)

**CLI Configuration** (in `config.py`):
```python
CLI_COMMANDS = {
    "gemini": {"command": "gemini", "args": [], "timeout": 120},
    "claude": {"command": "claude", "args": ["-p"], "timeout": 120},
    "codex": {"command": "codex", "args": ["exec", "--skip-git-repo-check"], "timeout": 120, "use_output_file": True},
}
```

**Health Check**: Use `GET /api/health` to verify CLI tools are available (checks `shutil.which()`).

## Environment Variables

Copy `.env.example` to `.env` and configure:
```
OPENROUTER_API_KEY=...  # Required for OpenRouter models
OPENAI_API_KEY=...      # Optional: Direct OpenAI API access
ANTHROPIC_API_KEY=...   # Optional: Direct Anthropic API access
```

## Future Enhancement Ideas

- ~~Configurable council/chairman via UI~~ (Done: `/api/config` endpoint)
- Streaming responses instead of batch loading
- ~~Export conversations~~ (Done: conversation deletion added)
- Model performance analytics over time
- Custom ranking criteria (not just accuracy/insight)
- Support for reasoning models (o1, etc.) with special handling
- Frontend settings UI for model configuration
- CLI tool auto-detection and suggestions

## Testing Notes

Use `test_openrouter.py` to verify API connectivity and test different model identifiers before adding to council. The script tests both streaming and non-streaming modes.

## Data Flow Summary

```
User Query
    ↓
Stage 1: Parallel queries → [individual responses]
    ↓
Stage 2: Anonymize → Parallel ranking queries → [evaluations + parsed rankings]
    ↓
Aggregate Rankings Calculation → [sorted by avg position]
    ↓
Stage 3: Chairman synthesis with full context
    ↓
Return: {stage1, stage2, stage3, metadata}
    ↓
Frontend: Display with tabs + validation UI
```

The entire flow is async/parallel where possible to minimize latency.
