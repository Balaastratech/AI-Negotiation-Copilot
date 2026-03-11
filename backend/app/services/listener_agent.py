"""
listener_agent.py — Background Gemini Flash listener
-----------------------------------------------------
Every POLL_INTERVAL seconds the agent:
  1. Grabs a WINDOW_SECONDS window from the AudioBuffer
  2. Sends audio + extraction prompt to gemini-2.5-flash (standard REST API)
  3. Parses the JSON context from the response
  4. Injects the context into the Live session (system role, no response triggered)
  5. Forwards CONTEXT_UPDATE to the frontend websocket

Design principles (from the architecture plan):
- Flash call (2-5s) NEVER holds the gemini_send_lock
- Lock is only grabbed for the fast inject send (< 100ms)
- A failed cycle is logged and skipped — never kills the loop
- Accumulated transcript is kept for the "Ask AI" query construction
"""

import asyncio
import base64
import json
import logging
import time
from typing import Any, Optional, TYPE_CHECKING

from google import genai
from google.genai import types as genai_types

from app.config import settings

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)

POLL_INTERVAL = 10          # seconds between extraction cycles
WINDOW_SECONDS = 15         # audio window sent to Flash each cycle
FLASH_MODEL = "gemini-2.5-flash"   # standard (non-Live) model

EXTRACTION_PROMPT = """You are analyzing a snippet of a live negotiation conversation.
Extract the following in strict JSON (no markdown, no extra text):
{
  "item": "name of product/service being negotiated, or null",
  "seller_price": <number or null>,
  "user_offer": <number or null>,
  "key_moments": ["one-sentence each"],
  "leverage_points": ["one-sentence each, max 3"],
  "sentiment": "positive|neutral|negative|unknown",
  "transcript_snippet": "verbatim excerpt (max 200 chars)"
}
If audio is silent/unclear return all nulls. Prices should be numbers only (no currency symbols).
"""


class ListenerAgent:
    """
    Background asyncio task that polls the AudioBuffer and extracts context.
    """

    def __init__(
        self,
        session_id: str,
        audio_buffer: Any,
        gemini_send_lock: asyncio.Lock,
        websocket: "WebSocket",
    ):
        self.session_id = session_id
        self.audio_buffer = audio_buffer
        self.gemini_send_lock = gemini_send_lock
        self.websocket = websocket

        self._live_session: Optional[Any] = None
        self._task: Optional[asyncio.Task] = None
        self._running = False

        # Accumulated context for "Ask AI" query enrichment
        self.last_context: dict = {}
        self.accumulated_transcript: str = ""
        self._cycle_count: int = 0

        # Flash client (standard API, NOT Live)
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._flash_model = FLASH_MODEL

        logger.info(
            f"[ListenerAgent] Initialized session={session_id} "
            f"poll={POLL_INTERVAL}s window={WINDOW_SECONDS}s"
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background polling loop."""
        self._running = True
        self._task = asyncio.create_task(
            self._poll_loop(), name=f"listener-{self.session_id[:8]}"
        )
        logger.info(f"[ListenerAgent] Started — session={self.session_id}")

    async def stop(self) -> None:
        """Gracefully stop the polling loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=3.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        logger.info(f"[ListenerAgent] Stopped — session={self.session_id}")

    # ------------------------------------------------------------------
    # Polling loop
    # ------------------------------------------------------------------

    async def _poll_loop(self) -> None:
        """Main loop — runs every POLL_INTERVAL seconds."""
        # Give the session a moment to stabilise before first poll
        await asyncio.sleep(POLL_INTERVAL)

        while self._running:
            cycle_start = time.monotonic()
            try:
                await self._run_cycle()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning(
                    f"[ListenerAgent] Cycle {self._cycle_count} error "
                    f"(skipping): {exc}",
                    exc_info=True,
                )

            elapsed = time.monotonic() - cycle_start
            sleep_time = max(0.0, POLL_INTERVAL - elapsed)
            await asyncio.sleep(sleep_time)

    # ------------------------------------------------------------------
    # Single extraction cycle
    # ------------------------------------------------------------------

    async def _run_cycle(self) -> None:
        self._cycle_count += 1
        logger.debug(
            f"[ListenerAgent] Cycle {self._cycle_count} — "
            f"buffer={self.audio_buffer.duration_seconds:.1f}s"
        )

        # 1. Grab audio window
        audio_bytes = self.audio_buffer.get_window(WINDOW_SECONDS)
        if len(audio_bytes) < 3200:  # < 0.1s of audio — skip
            logger.debug("[ListenerAgent] Not enough audio yet, skipping")
            return

        # 2. Call Flash (standard API) — do NOT hold the lock here
        context = await asyncio.get_event_loop().run_in_executor(
            None, self._call_flash, audio_bytes
        )
        if context is None:
            return

        # 3. Update accumulated state
        self._merge_context(context)

        # 4. Forward to frontend
        await self._send_context_update(context)

    def _call_flash(self, audio_bytes: bytes) -> Optional[dict]:
        """
        Synchronous call to Gemini Flash (run in executor so it doesn't
        block the event loop).  Returns parsed context dict or None.
        """
        try:
            import struct
            def pcm_to_wav(pcm_data: bytes, sample_rate: int = 16000, num_channels: int = 1, sample_width: int = 2) -> bytes:
                byte_rate = sample_rate * num_channels * sample_width
                block_align = num_channels * sample_width
                data_size = len(pcm_data)
                chunk_size = 36 + data_size
                header = struct.pack(
                    '<4sI4s4sIHHIIHH4sI',
                    b'RIFF', chunk_size, b'WAVE', b'fmt ', 16, 1, num_channels,
                    sample_rate, byte_rate, block_align, sample_width * 8, b'data', data_size
                )
                return header + pcm_data

            wav_bytes = pcm_to_wav(audio_bytes)
            audio_b64 = base64.b64encode(wav_bytes).decode("utf-8")

            # Build content with inline audio + text prompt
            audio_part = genai_types.Part(
                inline_data=genai_types.Blob(
                    mime_type="audio/wav",
                    data=audio_b64,
                )
            )
            text_part = genai_types.Part(text=EXTRACTION_PROMPT)

            response = self._client.models.generate_content(
                model=self._flash_model,
                contents=[genai_types.Content(parts=[audio_part, text_part])],
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )

            raw = response.text.strip()
            # Strip any accidental markdown fences
            if raw.startswith("```"):
                raw = "\n".join(raw.split("\n")[1:])
                raw = raw.rstrip("`").strip()

            parsed = json.loads(raw)
            logger.debug(f"[ListenerAgent] Flash result: {parsed}")
            return parsed

        except Exception as exc:
            logger.warning(f"[ListenerAgent] Flash call failed: {exc}")
            return None

    def _merge_context(self, context: dict) -> None:
        """Merge new context into accumulated state (non-destructive)."""
        for key in ("item", "seller_price", "user_offer", "sentiment"):
            if context.get(key) is not None:
                self.last_context[key] = context[key]

        snippet = context.get("transcript_snippet", "")
        if snippet:
            self.accumulated_transcript = (
                (self.accumulated_transcript + " " + snippet)[-2000:]
            )

        # Accumulate key moments and leverage points (deduplicated)
        for field in ("key_moments", "leverage_points"):
            existing = set(self.last_context.get(field, []))
            for item in context.get(field, []):
                existing.add(item)
            self.last_context[field] = list(existing)



    async def _send_context_update(self, context: dict) -> None:
        """Send CONTEXT_UPDATE to the frontend WebSocket."""
        try:
            payload = {
                "type": "CONTEXT_UPDATE",
                "payload": {
                    "item": self.last_context.get("item"),
                    "seller_price": self.last_context.get("seller_price"),
                    "user_offer": self.last_context.get("user_offer"),
                    "sentiment": self.last_context.get("sentiment", "unknown"),
                    "key_moments": self.last_context.get("key_moments", []),
                    "leverage_points": self.last_context.get(
                        "leverage_points", []
                    ),
                    "transcript_snippet": context.get("transcript_snippet", ""),
                    "cycle": self._cycle_count,
                },
            }
            await self.websocket.send_json(payload)
            logger.info(
                f"[ListenerAgent] CONTEXT_UPDATE sent cycle={self._cycle_count}"
            )
        except Exception as exc:
            logger.warning(
                f"[ListenerAgent] Failed to send CONTEXT_UPDATE: {exc}"
            )

    # ------------------------------------------------------------------
    # Public helpers (used by negotiation_engine)
    # ------------------------------------------------------------------

    def build_advisor_query(self, user_context: dict) -> str:
        """
        Build the ADVISOR_QUERY text injected by handle_ask_ai_button.
        Merges user-supplied context (from SetupDialog) with
        listener-accumulated context.
        """
        parts = ["🔔 ADVISOR_QUERY"]

        # From user setup form
        if user_context.get("item"):
            parts.append(f"Item: {user_context['item']}")
        if user_context.get("target_price"):
            parts.append(f"User target: {user_context['target_price']}")
        if user_context.get("max_price"):
            parts.append(f"User maximum: {user_context['max_price']}")
        if user_context.get("extra_context"):
            parts.append(f"Notes: {user_context['extra_context']}")

        # From listener
        if self.last_context.get("item") and not user_context.get("item"):
            parts.append(f"Detected item: {self.last_context['item']}")
        if self.last_context.get("seller_price"):
            parts.append(
                f"Seller is asking: {self.last_context['seller_price']}"
            )
        if self.last_context.get("user_offer"):
            parts.append(
                f"User has offered: {self.last_context['user_offer']}"
            )
        if self.last_context.get("leverage_points"):
            parts.append(
                "Leverage points: "
                + "; ".join(self.last_context["leverage_points"])
            )

        # Recent transcript
        if self.accumulated_transcript:
            recent = self.accumulated_transcript[-600:]
            parts.append(f"Recent conversation: \"{recent}\"")

        return "\n".join(parts)
