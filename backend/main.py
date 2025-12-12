"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
import json
import asyncio
import shutil

from . import storage
from .council import run_full_council, generate_conversation_title, stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, calculate_aggregate_rankings
from .config import (
    OPENROUTER_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY,
    CLI_COMMANDS, get_council_models, get_chairman_model, save_council_config
)

app = FastAPI(title="LLM Council API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


def _get_model_info(model: str, api_keys: dict, cli_tools: dict) -> dict:
    """Helper to get model info with type and ready status."""
    model_info = {"identifier": model}
    if model.startswith("cli:"):
        cli_name = model[4:]
        model_info["type"] = "cli"
        model_info["ready"] = cli_tools.get(cli_name, {}).get("available", False)
    elif model.startswith("openrouter:"):
        model_info["type"] = "openrouter"
        model_info["ready"] = api_keys["openrouter"]["configured"]
    elif model.startswith("openai/"):
        model_info["type"] = "openai"
        model_info["ready"] = api_keys["openai"]["configured"]
    elif model.startswith("anthropic/"):
        model_info["type"] = "anthropic"
        model_info["ready"] = api_keys["anthropic"]["configured"]
    else:
        model_info["type"] = "openrouter"
        model_info["ready"] = api_keys["openrouter"]["configured"]
    return model_info


@app.get("/api/health")
async def health_check():
    """
    Doctor endpoint - checks availability of API keys and CLI tools.
    Returns status of each provider and model configuration.
    """
    # Check API keys
    api_keys = {
        "openrouter": {
            "configured": bool(OPENROUTER_API_KEY),
            "key_preview": f"{OPENROUTER_API_KEY[:8]}..." if OPENROUTER_API_KEY else None
        },
        "openai": {
            "configured": bool(OPENAI_API_KEY),
            "key_preview": f"{OPENAI_API_KEY[:8]}..." if OPENAI_API_KEY else None
        },
        "anthropic": {
            "configured": bool(ANTHROPIC_API_KEY),
            "key_preview": f"{ANTHROPIC_API_KEY[:8]}..." if ANTHROPIC_API_KEY else None
        }
    }

    # Check CLI tools
    cli_tools = {}
    for cli_name, config in CLI_COMMANDS.items():
        command = config["command"]
        cli_tools[cli_name] = {
            "command": command,
            "available": shutil.which(command) is not None,
            "path": shutil.which(command)
        }

    # Get current council config (dynamic)
    council_models = get_council_models()
    chairman_model = get_chairman_model()

    # Check model configuration
    models = [_get_model_info(m, api_keys, cli_tools) for m in council_models]
    chairman_info = _get_model_info(chairman_model, api_keys, cli_tools)

    # Overall status
    all_models_ready = all(m["ready"] for m in models) and chairman_info["ready"]

    return {
        "status": "healthy" if all_models_ready else "degraded",
        "api_keys": api_keys,
        "cli_tools": cli_tools,
        "council_models": models,
        "chairman_model": chairman_info,
        "all_ready": all_models_ready
    }


class UpdateConfigRequest(BaseModel):
    """Request to update council configuration."""
    council_models: List[str]
    chairman_model: str


@app.get("/api/config")
async def get_config():
    """Get current council configuration."""
    return {
        "council_models": get_council_models(),
        "chairman_model": get_chairman_model()
    }


@app.post("/api/config")
async def update_config(request: UpdateConfigRequest):
    """Update council configuration."""
    save_council_config(request.council_models, request.chairman_model)
    return {
        "status": "ok",
        "council_models": request.council_models,
        "chairman_model": request.chairman_model
    }


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation."""
    deleted = storage.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "ok", "deleted": conversation_id}


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    storage.add_user_message(conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    # Run the 3-stage council process
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content
    )

    # Add assistant message with all stages
    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        try:
            # Add user message
            storage.add_user_message(conversation_id, request.content)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Stage 1: Collect responses
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results = await stage1_collect_responses(request.content)
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            # Stage 2: Collect rankings
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(request.content, stage1_results)
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            # Stage 3: Synthesize final answer
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(request.content, stage1_results, stage2_results)
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
