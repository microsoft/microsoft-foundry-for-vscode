"""Foundry protocol adapter — subclasses FoundryCBAgent."""

import logging
import time
import uuid
from typing import AsyncGenerator, Union

from dotenv import load_dotenv
load_dotenv(override=False)

import _telemetry  # noqa: F401  — App Insights connection string discovery

from azure.ai.agentserver.core.server.base import FoundryCBAgent
from azure.ai.agentserver.core.server.common.agent_run_context import AgentRunContext
from azure.ai.agentserver.core.models.projects import (
    Response as OpenAIResponse,
    ResponseStreamEvent,
    ResponseCreatedEvent,
    ResponseInProgressEvent,
    ResponseOutputItemAddedEvent,
    ResponseContentPartAddedEvent,
    ResponseTextDeltaEvent,
    ResponseTextDoneEvent,
    ResponseContentPartDoneEvent,
    ResponseOutputItemDoneEvent,
    ResponseCompletedEvent,
    ResponsesAssistantMessageItemResource,
)

logger = logging.getLogger("foundry_adapter")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _extract_input_text(request) -> str:
    """Extract plain text from Foundry input (string or array-of-items)."""
    raw = request.get("input", "") if isinstance(request, dict) else getattr(request, "input", "")
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        parts = []
        for item in raw:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                content = item.get("content", "")
                if isinstance(content, str):
                    parts.append(content)
                elif isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict):
                            parts.append(part.get("text", ""))
                        elif isinstance(part, str):
                            parts.append(part)
            elif hasattr(item, "content"):
                content = getattr(item, "content", "")
                if isinstance(content, str):
                    parts.append(content)
                elif isinstance(content, list):
                    for part in content:
                        parts.append(getattr(part, "text", "") if hasattr(part, "text") else str(part))
        return "\n".join(p for p in parts if p)
    return str(raw)


def _make_message_item(item_id: str, text: str, *, status: str = "completed"):
    """Create a ResponsesAssistantMessageItemResource."""
    return ResponsesAssistantMessageItemResource({
        "type": "message",
        "id": item_id,
        "role": "assistant",
        "status": status,
        "content": [{"type": "output_text", "text": text, "annotations": []}],
    })


def _make_response(response_id: str, status: str, output: list, created_at: int):
    """Create an OpenAIResponse object."""
    return OpenAIResponse({
        "id": response_id,
        "object": "response",
        "status": status,
        "created_at": created_at,
        "output": [item.as_dict() if hasattr(item, "as_dict") else item for item in output],
        "metadata": {},
    })


class CopilotFoundryAdapter(FoundryCBAgent):
    """Bridges CopilotAgent <-> Foundry responses protocol."""

    def __init__(self, agent):
        super().__init__()
        self._agent = agent

    async def _load_conversation_history(self, conversation_id: str) -> str | None:
        """Load prior conversation turns from Foundry for cold-start bootstrap."""
        if not self._project_endpoint:
            logger.debug("No project endpoint — skipping history load")
            return None
        try:
            openai_client = await self._create_openai_client()
            items = []
            async for item in openai_client.conversations.items.list(conversation_id):
                items.append(item)
            # API returns reverse chronological — restore order
            items.reverse()

            if not items:
                return None

            lines = []
            for item in items:
                role = getattr(item, "role", None)
                # Extract text content
                content = getattr(item, "content", None)
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    text_parts = []
                    for part in content:
                        if isinstance(part, dict):
                            text_parts.append(part.get("text", ""))
                        elif hasattr(part, "text"):
                            text_parts.append(part.text)
                    text = " ".join(p for p in text_parts if p)
                else:
                    continue
                if not text:
                    continue
                label = "User" if role == "user" else "Assistant"
                lines.append(f"{label}: {text}")

            return "\n".join(lines) if lines else None
        except Exception:
            logger.warning("Failed to load conversation history for %s", conversation_id, exc_info=True)
            return None

    async def agent_run(
        self, context: AgentRunContext
    ) -> Union[OpenAIResponse, AsyncGenerator[ResponseStreamEvent, None]]:
        text = _extract_input_text(context.raw_payload)
        conversation_id = context.conversation_id

        # Load history on cold start (no cached session and no resumable session ID)
        history = None
        if conversation_id and not self._agent.has_session(conversation_id) and not self._agent.has_session_id(conversation_id):
            history = await self._load_conversation_history(conversation_id)

        if context.stream:
            return self._stream_response(context, text, conversation_id=conversation_id, history=history)
        return await self._non_stream_response(context, text, conversation_id=conversation_id, history=history)

    async def _non_stream_response(
        self,
        context: AgentRunContext,
        text: str,
        *,
        conversation_id: str | None = None,
        history: str | None = None,
    ) -> OpenAIResponse:
        result = await self._agent.run(text, stream=False, conversation_id=conversation_id, history=history)
        output_text = getattr(result, "text", "") or str(result)
        item = _make_message_item(_new_id("msg"), output_text)
        return _make_response(context.response_id, "completed", [item], int(time.time()))

    async def _stream_response(
        self,
        context: AgentRunContext,
        text: str,
        *,
        conversation_id: str | None = None,
        history: str | None = None,
    ) -> AsyncGenerator[ResponseStreamEvent, None]:
        response_id = context.response_id
        item_id = _new_id("msg")
        created_at = int(time.time())
        seq = 0

        def _seq():
            nonlocal seq
            s = seq
            seq += 1
            return s

        # Response shell for lifecycle events
        def _resp_shell(status, output=None):
            return _make_response(response_id, status, output or [], created_at)

        # 1. Lifecycle: created + in_progress
        yield ResponseCreatedEvent({
            "type": "response.created",
            "sequence_number": _seq(),
            "response": _resp_shell("in_progress").as_dict(),
        })
        yield ResponseInProgressEvent({
            "type": "response.in_progress",
            "sequence_number": _seq(),
            "response": _resp_shell("in_progress").as_dict(),
        })

        # 2. Output item added
        item_shell = _make_message_item(item_id, "", status="in_progress")
        yield ResponseOutputItemAddedEvent({
            "type": "response.output_item.added",
            "sequence_number": _seq(),
            "output_index": 0,
            "item": item_shell.as_dict(),
        })

        # 3. Content part added
        yield ResponseContentPartAddedEvent({
            "type": "response.content_part.added",
            "sequence_number": _seq(),
            "item_id": item_id,
            "output_index": 0,
            "content_index": 0,
            "part": {"type": "output_text", "text": "", "annotations": []},
        })

        # 4. Stream text deltas
        full_text = ""
        try:
            stream = self._agent.run(text, stream=True, conversation_id=conversation_id, history=history)
            async for update in stream:
                chunk = getattr(update, "text", None) or str(update)
                if not chunk:
                    continue
                full_text += chunk
                yield ResponseTextDeltaEvent({
                    "type": "response.output_text.delta",
                    "sequence_number": _seq(),
                    "item_id": item_id,
                    "output_index": 0,
                    "content_index": 0,
                    "delta": chunk,
                })
        except Exception as exc:
            logger.exception("Agent streaming failed")
            full_text = f"Error: {exc}"

        # 5. Finalize
        yield ResponseTextDoneEvent({
            "type": "response.output_text.done",
            "sequence_number": _seq(),
            "item_id": item_id,
            "output_index": 0,
            "content_index": 0,
            "text": full_text,
        })
        yield ResponseContentPartDoneEvent({
            "type": "response.content_part.done",
            "sequence_number": _seq(),
            "item_id": item_id,
            "output_index": 0,
            "content_index": 0,
            "part": {"type": "output_text", "text": full_text, "annotations": []},
        })

        final_item = _make_message_item(item_id, full_text)
        yield ResponseOutputItemDoneEvent({
            "type": "response.output_item.done",
            "sequence_number": _seq(),
            "output_index": 0,
            "item": final_item.as_dict(),
        })
        yield ResponseCompletedEvent({
            "type": "response.completed",
            "sequence_number": _seq(),
            "response": _resp_shell("completed", [final_item]).as_dict(),
        })

    def run(self, port: int = None):
        """Start the server, hooking agent start/stop into the Starlette lifecycle."""
        agent = self._agent

        @self.app.on_event("startup")
        async def _start_agent():
            logger.info("Starting CopilotAgent…")
            await agent.start()

        @self.app.on_event("shutdown")
        async def _stop_agent():
            logger.info("Stopping CopilotAgent…")
            await agent.stop()

        if port is not None:
            super().run(port=port)
        else:
            super().run()
