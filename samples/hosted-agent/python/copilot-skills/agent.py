"""CopilotAgent — thin wrapper around CopilotClient for run/stream."""

import asyncio
import logging
import os
from types import SimpleNamespace

from copilot import CopilotClient
from copilot.generated.session_events import SessionEvent, SessionEventType

logger = logging.getLogger("copilot_agent")


def _approve_all(request, context):
    """Auto-approve all permission requests (no interactive user in container)."""
    return {"kind": "approved"}


def _make_stream_event_handler(queue: "asyncio.Queue[SimpleNamespace | Exception | None]"):
    """Build an event handler that maps Copilot SDK events to queued text chunks.

    Surfaces tool execution, reasoning, and skill events as inline annotations
    so callers get real-time visibility into agent activity.
    """
    # Track tool names from start events so completions can reference them
    active_tools: dict[str, str] = {}  # tool_call_id -> name

    def _tool_name(event_data) -> str:
        return (
            getattr(event_data, "tool_name", None)
            or getattr(event_data, "mcp_tool_name", None)
            or "tool"
        )

    def handler(event: SessionEvent) -> None:
        etype = event.type

        # --- Final answer text ---
        if etype == SessionEventType.ASSISTANT_MESSAGE_DELTA:
            if event.data.delta_content:
                queue.put_nowait(SimpleNamespace(text=event.data.delta_content))

        # --- Tool / skill activity ---
        elif etype == SessionEventType.TOOL_EXECUTION_START:
            name = _tool_name(event.data)
            call_id = getattr(event.data, "tool_call_id", None)
            if call_id:
                active_tools[call_id] = name
            queue.put_nowait(SimpleNamespace(
                text=f"\n> Calling `{name}` ...\n",
                annotation=True,
            ))
        elif etype == SessionEventType.TOOL_EXECUTION_PROGRESS:
            msg = getattr(event.data, "progress_message", None)
            if msg:
                queue.put_nowait(SimpleNamespace(text=f"> {msg}\n", annotation=True))
        elif etype == SessionEventType.TOOL_EXECUTION_COMPLETE:
            call_id = getattr(event.data, "tool_call_id", None)
            name = active_tools.pop(call_id, None) if call_id else None
            if not name:
                name = _tool_name(event.data)
            queue.put_nowait(SimpleNamespace(
                text=f"> `{name}` done\n",
                annotation=True,
            ))
        elif etype == SessionEventType.SKILL_INVOKED:
            name = getattr(event.data, "tool_name", None) or "skill"
            queue.put_nowait(SimpleNamespace(
                text=f"\n> Skill: `{name}`\n",
                annotation=True,
            ))

        # --- Reasoning / thinking ---
        elif etype == SessionEventType.ASSISTANT_REASONING_DELTA:
            if getattr(event.data, "delta_content", None):
                queue.put_nowait(SimpleNamespace(
                    text=event.data.delta_content,
                    annotation=True,
                ))

        # --- Turn boundaries ---
        elif etype == SessionEventType.ASSISTANT_TURN_START:
            queue.put_nowait(SimpleNamespace(
                text="\n> Processing...\n",
                annotation=True,
            ))

        # --- Lifecycle ---
        elif etype == SessionEventType.SESSION_IDLE:
            queue.put_nowait(None)
        elif etype == SessionEventType.SESSION_ERROR:
            queue.put_nowait(RuntimeError(getattr(event.data, "message", None) or "Session error"))

    return handler


class CopilotAgent:
    """Wraps CopilotClient with a simple run(prompt, stream=) interface."""

    def __init__(self, *, skill_directories: list[str] | None = None):
        self._skill_directories = skill_directories or []
        self._client: CopilotClient | None = None
        # Session caches keyed by conversation_id
        self._sessions: dict[str, object] = {}
        self._session_ids: dict[str, str] = {}

    async def start(self) -> None:
        if self._client is not None:
            return
        self._client = CopilotClient()
        await self._client.start()

    async def stop(self) -> None:
        if self._client is not None:
            # Destroy all cached sessions before stopping
            for conv_id, session in list(self._sessions.items()):
                try:
                    await session.destroy()
                except Exception:
                    logger.debug("Failed to destroy session for %s", conv_id, exc_info=True)
            self._sessions.clear()
            self._session_ids.clear()
            await self._client.stop()
            self._client = None

    def has_session(self, conversation_id: str) -> bool:
        return conversation_id in self._sessions

    def has_session_id(self, conversation_id: str) -> bool:
        return conversation_id in self._session_ids

    def _build_session_config(self, streaming: bool) -> dict:
        config: dict = {
            "streaming": streaming,
            "on_permission_request": _approve_all,
        }
        model = os.environ.get("GITHUB_COPILOT_MODEL")
        if model:
            config["model"] = model
        if self._skill_directories:
            config["skill_directories"] = self._skill_directories
        return config

    async def _get_or_create_session(
        self,
        conversation_id: str,
        streaming: bool,
        history: str | None = None,
    ):
        """Three-tier session retrieval: hot cache, warm resume, cold create."""
        assert self._client is not None, "Call start() first"

        # Hot: return cached session
        if conversation_id in self._sessions:
            logger.debug("Hot session for %s", conversation_id)
            return self._sessions[conversation_id]

        # Warm: resume from saved session ID
        if conversation_id in self._session_ids:
            saved_id = self._session_ids[conversation_id]
            try:
                config = self._build_session_config(streaming)
                session = await self._client.resume_session(saved_id, **config)
                self._sessions[conversation_id] = session
                logger.info("Resumed session %s for %s", saved_id, conversation_id)
                return session
            except Exception:
                logger.warning(
                    "Failed to resume session %s, falling through to cold path",
                    saved_id,
                    exc_info=True,
                )
                self._session_ids.pop(conversation_id, None)

        # Cold: create new session, optionally bootstrap with history
        config = self._build_session_config(streaming)
        session = await self._client.create_session(**config)
        if history:
            logger.info("Bootstrapping session with conversation history for %s", conversation_id)
            try:
                preamble = (
                    "Here is the prior conversation history for context. "
                    "Do not repeat or summarize it — just use it as context "
                    "for the user's next message.\n\n" + history
                )
                await session.send_and_wait(preamble, timeout=120.0)
            except Exception:
                logger.warning("Failed to bootstrap history", exc_info=True)

        self._sessions[conversation_id] = session
        if hasattr(session, "session_id"):
            self._session_ids[conversation_id] = session.session_id
        logger.info("Created new session for %s", conversation_id)
        return session

    def _evict_session(self, conversation_id: str) -> None:
        """Remove a session from cache (e.g. after an error)."""
        self._sessions.pop(conversation_id, None)

    async def _run_once(
        self,
        prompt: str,
        *,
        conversation_id: str | None = None,
        history: str | None = None,
    ) -> SimpleNamespace:
        assert self._client is not None, "Call start() first"

        # Ephemeral path: no conversation_id → create-use-destroy
        if not conversation_id:
            session = await self._client.create_session(**self._build_session_config(streaming=False))
            try:
                event = await session.send_and_wait(prompt, timeout=120.0)
                text = event.data.content if event else ""
                return SimpleNamespace(text=text or "")
            finally:
                await session.destroy()

        # Persistent path
        session = await self._get_or_create_session(conversation_id, streaming=False, history=history)
        try:
            event = await session.send_and_wait(prompt, timeout=120.0)
            text = event.data.content if event else ""
            return SimpleNamespace(text=text or "")
        except Exception:
            logger.exception("Session error for %s, evicting", conversation_id)
            self._evict_session(conversation_id)
            raise

    async def _stream(
        self,
        prompt: str,
        *,
        conversation_id: str | None = None,
        history: str | None = None,
    ):
        assert self._client is not None, "Call start() first"

        # Ephemeral path: no conversation_id → create-use-destroy
        if not conversation_id:
            session = await self._client.create_session(**self._build_session_config(streaming=True))
            queue: asyncio.Queue[SimpleNamespace | Exception | None] = asyncio.Queue()
            unsubscribe = session.on(_make_stream_event_handler(queue))
            try:
                await session.send(prompt)
                while True:
                    item = await queue.get()
                    if item is None:
                        break
                    if isinstance(item, Exception):
                        raise item
                    yield item
            finally:
                unsubscribe()
                await session.destroy()
            return

        # Persistent path
        session = await self._get_or_create_session(conversation_id, streaming=True, history=history)
        queue: asyncio.Queue[SimpleNamespace | Exception | None] = asyncio.Queue()
        unsubscribe = session.on(_make_stream_event_handler(queue))
        try:
            await session.send(prompt)
            while True:
                item = await queue.get()
                if item is None:
                    break
                if isinstance(item, Exception):
                    raise item
                yield item
        except Exception:
            logger.exception("Streaming error for %s, evicting", conversation_id)
            self._evict_session(conversation_id)
            raise
        finally:
            unsubscribe()

    def run(
        self,
        prompt: str,
        *,
        stream: bool = False,
        conversation_id: str | None = None,
        history: str | None = None,
    ):
        """Return a coroutine (stream=False) or async generator (stream=True)."""
        if stream:
            return self._stream(prompt, conversation_id=conversation_id, history=history)
        return self._run_once(prompt, conversation_id=conversation_id, history=history)
