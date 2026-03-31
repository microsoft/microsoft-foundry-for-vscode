"""
Copilot Skills Agent - A code-based hosted agent using FoundryCBAgent.
Demonstrates direct control over streaming and non-streaming responses
with the Azure AI AgentServer Core SDK.
"""

import datetime
import os
from typing import Any, AsyncGenerator, Union

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agentserver.core import AgentRunContext, FoundryCBAgent
from azure.ai.agentserver.core.models import (
    Response as OpenAIResponse,
    ResponseStreamEvent,
)
from azure.ai.agentserver.core.models.projects import (
    ItemContentOutputText,
    ResponseCompletedEvent,
    ResponseCreatedEvent,
    ResponseOutputItemAddedEvent,
    ResponsesAssistantMessageItemResource,
    ResponseTextDeltaEvent,
    ResponseTextDoneEvent,
)
from azure.ai.agentserver.core.logger import get_logger
from dotenv import load_dotenv

load_dotenv(override=True)

logger = get_logger()

SYSTEM_PROMPT = "You are a helpful assistant."


class CopilotSkillsAgent(FoundryCBAgent):
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        self.model = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4.1-mini")
        project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "")

        if project_endpoint:
            project_client = AIProjectClient(
                endpoint=project_endpoint,
                credential=DefaultAzureCredential(),
            )
            self.client = project_client.get_openai_client()
            logger.info("Initialized OpenAI client via AIProjectClient.")
        else:
            raise ValueError("Set AZURE_AI_PROJECT_ENDPOINT environment variable.")

    def _stream_final_text(self, final_text: str, context: AgentRunContext):
        """Yield streaming events for the final text."""

        async def _async_stream():
            assembled = ""
            seq = 0

            def next_seq() -> int:
                nonlocal seq
                current = seq
                seq += 1
                return current

            yield ResponseCreatedEvent(
                sequence_number=next_seq(),
                response=OpenAIResponse(
                    output=[],
                    conversation=context.get_conversation_object(),
                    agent=context.get_agent_id_object(),
                    id=context.response_id,
                ),
            )

            item_id = context.id_generator.generate_message_id()
            yield ResponseOutputItemAddedEvent(
                sequence_number=next_seq(),
                output_index=0,
                item=ResponsesAssistantMessageItemResource(
                    id=item_id,
                    status="in_progress",
                    content=[ItemContentOutputText(text="", annotations=[])],
                ),
            )

            words = final_text.split(" ")
            for idx, token in enumerate(words):
                piece = token if idx == len(words) - 1 else token + " "
                assembled += piece
                yield ResponseTextDeltaEvent(
                    sequence_number=next_seq(),
                    output_index=0,
                    content_index=0,
                    delta=piece,
                )

            yield ResponseTextDoneEvent(
                sequence_number=next_seq(),
                output_index=0,
                content_index=0,
                text=assembled,
            )

            yield ResponseCompletedEvent(
                sequence_number=next_seq(),
                response=OpenAIResponse(
                    agent=context.get_agent_id_object(),
                    conversation=context.get_conversation_object(),
                    metadata={},
                    temperature=0.0,
                    top_p=0.0,
                    user="user",
                    id=context.response_id,
                    created_at=int(datetime.datetime.now(datetime.timezone.utc).timestamp()),
                    output=[
                        ResponsesAssistantMessageItemResource(
                            id=item_id,
                            status="completed",
                            content=[ItemContentOutputText(text=assembled, annotations=[])],
                        )
                    ],
                ),
            )

        return _async_stream()

    def _final_text_to_response(self, final_text: str, context: AgentRunContext) -> OpenAIResponse:
        """Build a non-streaming OpenAI Response."""
        return OpenAIResponse({
            "object": "response",
            "agent": context.get_agent_id_object(),
            "conversation": context.get_conversation_object(),
            "metadata": {},
            "type": "message",
            "role": "assistant",
            "user": "",
            "id": context.response_id,
            "created_at": int(datetime.datetime.now(datetime.timezone.utc).timestamp()),
            "output": [
                ResponsesAssistantMessageItemResource(
                    id=context.id_generator.generate_message_id(),
                    status="completed",
                    content=[ItemContentOutputText(text=final_text, annotations=[])],
                )
            ],
            "status": "completed",
        })

    async def agent_run(
        self, context: AgentRunContext
    ) -> Union[OpenAIResponse, AsyncGenerator[ResponseStreamEvent, Any]]:
        is_stream = context.request.get("stream", False)
        request_input = context.request.get("input")
        logger.info(f"Received input: {request_input}")

        if isinstance(request_input, str):
            request_input = [{"type": "message", "role": "user", "content": request_input}]

        input_messages = [
            {"type": "message", "role": "system", "content": SYSTEM_PROMPT}
        ]
        input_messages += request_input

        resp = self.client.responses.create(
            model=self.model,
            input=input_messages,
        )

        text_chunks = []
        for item in resp.output:
            txt = _extract_text(item)
            if txt:
                text_chunks.append(txt)

        final_text = "\n".join(text_chunks).strip() or "I couldn't generate a response."

        if is_stream:
            return self._stream_final_text(final_text, context)
        return self._final_text_to_response(final_text, context)


def _extract_text(item: Any) -> str:
    """Extract text from a response output item (dict or SDK object)."""
    if isinstance(item, dict):
        if item.get("type") == "output_text":
            return item.get("text", "") or ""
        if item.get("type") == "message":
            return "\n".join(
                c.get("text", "") for c in item.get("content", [])
                if isinstance(c, dict) and c.get("type") == "output_text"
            ).strip()
        return ""

    t = getattr(item, "type", None)
    if t == "output_text":
        return getattr(item, "text", "") or ""
    if t == "message":
        return "\n".join(
            getattr(c, "text", "") for c in (getattr(item, "content", None) or [])
            if getattr(c, "type", None) == "output_text"
        ).strip()
    return ""


if __name__ == "__main__":
    agent = CopilotSkillsAgent()
    agent.run()
