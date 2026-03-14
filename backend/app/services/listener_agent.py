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
from typing import Any, Callable, Optional, TYPE_CHECKING

from google import genai
from google.genai import types as genai_types

from app.config import settings

if TYPE_CHECKING:
    from fastapi import WebSocket
    from app.models.negotiation import NegotiationSession

logger = logging.getLogger(__name__)

POLL_INTERVAL = 10          # seconds between extraction cycles
WINDOW_SECONDS = 15         # audio window sent to Flash each cycle
FLASH_MODEL = "gemini-2.5-flash"   # standard (non-Live) model

EXTRACTION_PROMPT = """You are analyzing a snippet of a live negotiation conversation.
Extract the following in strict JSON (no markdown, no extra text):
{
  "item": "name of product/service being negotiated, or null",
  "seller_price": <number or null - what the seller is asking>,
  "user_offer": <number or null - what the user has currently offered>,
  "user_target_price": <number or null - what the user ultimately wants to pay>,
  "user_max_price": <number or null - the highest the user is willing to go>,
  "key_moments": ["one-sentence each"],
  "leverage_points": ["one-sentence each, max 3. Look for weaknesses or advantages."],
  "counterparty_sentiment": "positive|neutral|negative|unknown",
  "research_query": "A search query targeting CURRENT MARKET PRICES and KNOWN ISSUES for this specific item (e.g. 'used iPhone 15 Pro Max price 2025 eBay', 'common problems Samsung Galaxy S24 Ultra used'). Include the year. Prioritize price range queries. Return null only if item is completely unknown.",
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
        session: "NegotiationSession",
        audio_buffer: Any,
        gemini_send_lock: asyncio.Lock,
        websocket: "WebSocket",
        on_context_ready: Optional[Callable] = None,
    ):
        self.session = session
        self.session_id = session.session_id
        self.audio_buffer = audio_buffer
        self.gemini_send_lock = gemini_send_lock
        self.websocket = websocket
        self._on_context_ready = on_context_ready

        self._live_session: Optional[Any] = None
        self._task: Optional[asyncio.Task] = None
        self._research_task: Optional[asyncio.Task] = None
        self._running = False

        # Accumulated context for "Ask AI" query enrichment
        self.last_context: dict = {}
        self.accumulated_transcript: str = ""
        self._cycle_count: int = 0
        
        # Track the last sent context to detect changes (for deduplication)
        self._last_sent_context: dict = {}
        
        # Track last research query sent to avoid duplicate research calls
        self._last_research_query: str = ""
        # Time-based research cooldown — prevents re-firing when Flash varies query wording
        self._last_research_timestamp: float = 0.0
        
        # Queue for critical events detected before copilot is activated
        self._pre_activation_critical_events: list[dict] = []

        # Flash client (standard API, NOT Live)
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._flash_model = FLASH_MODEL

        logger.info(
            f"[ListenerAgent] Initialized session={self.session_id} "
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

        # Skip the entire extraction cycle while the user is speaking directly to the AI.
        # Without this guard, Flash processes the user's AI-addressed speech and incorrectly
        # assigns prices they reference (e.g. "they want $700") to user_target_price.
        if getattr(self.session, 'user_addressing_ai', False):
            logger.debug("[ListenerAgent] Skipping cycle — user is addressing AI")
            return

        # 2. Call Flash (standard API) — do NOT hold the lock here
        context = await asyncio.get_event_loop().run_in_executor(
            None, self._call_flash, audio_bytes
        )
        if context is None:
            return

        # 3. Detect critical events BEFORE merge (need both new context AND last_context)
        critical_events: list[dict] = []

        # ANCHOR_DETECTED: seller named a new/changed price
        new_price = context.get("seller_price")
        if new_price is not None and new_price != self.last_context.get("seller_price"):
            critical_events.append({
                "event_type": "ANCHOR_DETECTED",
                "detail": {
                    "new_price": new_price,
                    "old_price": self.last_context.get("seller_price"),
                },
            })

        # SENTIMENT_NEGATIVE: counterparty sentiment flipped to negative
        prev_sentiment = self.last_context.get("counterparty_sentiment")
        new_sentiment = context.get("counterparty_sentiment")
        if prev_sentiment in ("positive", "neutral") and new_sentiment == "negative":
            critical_events.append({
                "event_type": "SENTIMENT_NEGATIVE",
                "detail": {"from": prev_sentiment, "to": new_sentiment},
            })

        # URGENCY_DETECTED: urgency keywords in key_moments
        _URGENCY_KEYWORDS = (
            "urgent", "deadline", "today only", "last offer", "final price",
            "need to sell", "leaving", "other buyer",
        )
        for moment in context.get("key_moments", []):
            moment_lower = moment.lower()
            if any(kw in moment_lower for kw in _URGENCY_KEYWORDS):
                critical_events.append({
                    "event_type": "URGENCY_DETECTED",
                    "detail": {"moment": moment},
                })
                break  # one event per cycle is enough

        # PRESSURE_TACTIC: pressure language in leverage_points or key_moments
        _PRESSURE_MARKERS = (
            "scarc", "limited", "only one", "last chance", "take it or leave",
            "now or never", "emotional", "guilt", "pressure", "final", "ultimatum",
        )
        _pressure_sources = (
            context.get("leverage_points", []) + context.get("key_moments", [])
        )
        for text in _pressure_sources:
            text_lower = text.lower()
            if any(marker in text_lower for marker in _PRESSURE_MARKERS):
                critical_events.append({
                    "event_type": "PRESSURE_TACTIC",
                    "detail": {"text": text},
                })
                break  # one event per cycle is enough

        if critical_events:
            logger.info(
                f"[ListenerAgent] Cycle {self._cycle_count} — "
                f"{len(critical_events)} critical event(s): "
                f"{[e['event_type'] for e in critical_events]}"
            )

        # 4. Update accumulated state (merge AFTER detection so last_context still has old values)
        new_item = context.get("item")
        old_item = self.last_context.get("item")

        self._merge_context(context)

        # 5. Forward to frontend
        await self._send_context_update(context)

        # 6. Notify engine for Live AI injection (or queue if copilot not active)
        if not self.session.copilot_active:
            if critical_events:
                self._pre_activation_critical_events.extend(critical_events)
                logger.info(
                    f"[ListenerAgent] Copilot inactive, queued {len(critical_events)} critical event(s). "
                    f"Total queued: {len(self._pre_activation_critical_events)}"
                )
        elif self._on_context_ready:
            # Only inject if something meaningful changed OR there are critical events.
            # This prevents spamming the Live AI with identical context every 10 seconds.
            context_changed = self._has_context_changed(self.last_context)
            if context_changed or critical_events:
                if context_changed:
                    self._update_last_sent_context(self.last_context)
                await self._on_context_ready(self.last_context, critical_events)
        
        # 7. Trigger background market research — time-gated to once per 90s.
        # Gemini Flash re-generates research_query strings every cycle with slight wording
        # variation, so string-equality dedup fails. Time-based cooldown is reliable.
        new_query = self.last_context.get("research_query")
        _RESEARCH_COOLDOWN_SECS = 90
        current_time = time.time()
        if (new_query
                and (current_time - self._last_research_timestamp) > _RESEARCH_COOLDOWN_SECS
                and not self._research_task):
            logger.info(f"[ListenerAgent] Triggering research (cooldown passed): '{new_query}'")
            self._last_research_timestamp = current_time
            self._research_task = asyncio.create_task(self._run_market_research(new_query))

    async def _run_market_research(self, research_query: str) -> None:
        """Run asynchronous market research using Gemini Flash with Google Search."""
        try:
            # Notify frontend that research has started
            await self.websocket.send_json({
                "type": "RESEARCH_STARTED",
                "payload": {"query": research_query}
            })
            
            research_prompt = f"""
Search the internet for: "{research_query}"

You are helping someone negotiate a better deal RIGHT NOW. Return ONLY a valid JSON object with no markdown:
{{
  "insights": "Current market price range: $X-$Y (source/platform). [One key depreciation or condition fact]. [One specific negotiation leverage point — e.g. common defects, oversupply, or faster alternatives the buyer can mention]."
}}

Rules:
- Be specific with prices — give a dollar range, not a vague statement like "reasonable" or "fair"
- If you find eBay, Facebook Marketplace, or Craigslist comparable listings, cite the price range
- If you find known defects or common issues with this item model, mention them as buyer leverage
- Keep total response under 3 sentences inside "insights"
- If no price data found, state what was found and its negotiation relevance
"""
            
            logger.info(
                "Running market research",
                extra={
                    "session_id": self.session_id,
                    "research_query": research_query,
                    "research_prompt": research_prompt,
                },
            )
            
            # Run the blocking API call in an executor
            def do_research():
                return self._client.models.generate_content(
                    model=self._flash_model,
                    contents=research_prompt,
                    config=genai_types.GenerateContentConfig(
                        temperature=0.1,
                        tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())]
                    )
                )
                
            response = await asyncio.get_event_loop().run_in_executor(None, do_research)
            
            raw = response.text
            if raw:
                raw = raw.strip()
                if raw.startswith("```"):
                    raw = "\n".join(raw.split("\n")[1:])
                    raw = raw.rstrip("`").strip()
            else:
                raw = "{}"
                
            if not raw:
                market_data = {}
            else:
                market_data = json.loads(raw)
            logger.info(f"[ListenerAgent] Research complete for {research_query}: {market_data}")
            
            # We send the insights string directly as market_data
            insights = market_data.get("insights", "No insights found.") if market_data else "No insights found."
            self.last_context["market_data"] = insights
            
            # Notify frontend with results
            await self.websocket.send_json({
                "type": "RESEARCH_COMPLETE",
                "payload": {
                    "query": research_query,
                    "market_data": insights,
                    "timestamp": time.time()
                }
            })
            
        except Exception as e:
            logger.error(f"[ListenerAgent] Background research failed: {e}")
            await self.websocket.send_json({
                "type": "RESEARCH_FAILED",
                "payload": {"error": str(e)}
            })
        finally:
            self._research_task = None

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
            # FIX: Inject known item into prompt so Flash doesn't downgrade it to generic terms
            known_item = self.last_context.get("item")
            if known_item:
                prompt_with_item = f"""The negotiation is about: {known_item}. 
Extract the following in strict JSON (no markdown, no extra text):
{{
  "item": "{known_item}",  
  "seller_price": <number or null - what the seller is asking>,
  "user_offer": <number or null - what the user has currently offered>,
  "user_target_price": <number or null - what the user ultimately wants to pay>,
  "user_max_price": <number or null - the highest the user is willing to go>,
  "key_moments": ["one-sentence each"],
  "leverage_points": ["one-sentence each, max 3. Look for weaknesses or advantages."],
  "counterparty_sentiment": "positive|neutral|negative|unknown",
  "research_query": "A search query targeting CURRENT MARKET PRICES and KNOWN ISSUES for {known_item} (e.g. 'used {known_item} price 2025 eBay', 'common problems {known_item}'). Include the year. Prioritize price range queries.",
  "transcript_snippet": "verbatim excerpt (max 200 chars)"
}}
If audio is silent/unclear return all nulls. Prices should be numbers only (no currency symbols).
IMPORTANT: Keep the item as "{known_item}" - do not replace it with generic terms like "phone" or "it"."""
            else:
                prompt_with_item = EXTRACTION_PROMPT

            # Prepend speaker context so Flash correctly attributes prices/offers to the right role
            speaker = getattr(self.session, 'current_speaker', 'unknown')
            if speaker == "user":
                speaker_hint = "NOTE: The primary speaker in this audio window is the USER (the buyer). Attribute their price statements to 'user_offer', 'user_target_price', or 'user_max_price'.\n\n"
            else:
                speaker_hint = "NOTE: The primary speaker in this audio window is the COUNTERPARTY (the seller). Attribute their price statements to 'seller_price'.\n\n"
            prompt_with_item = speaker_hint + prompt_with_item

            audio_part = genai_types.Part(
                inline_data=genai_types.Blob(
                    mime_type="audio/wav",
                    data=audio_b64,
                )
            )
            text_part = genai_types.Part(text=prompt_with_item)

            logger.info(
                "Calling Flash model for context extraction",
                extra={
                    "session_id": self.session_id,
                    "prompt": prompt_with_item,
                    "audio_duration_seconds": len(audio_bytes) / 32000,
                },
            )

            response = self._client.models.generate_content(
                model=self._flash_model,
                contents=[genai_types.Content(parts=[audio_part, text_part])],
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )

            raw = response.text
            if raw:
                raw = raw.strip()
                if raw.startswith("```"):
                    raw = "\n".join(raw.split("\n")[1:])
                    raw = raw.rstrip("`").strip()
            
            if not raw:
                parsed = {}
            else:
                parsed = json.loads(raw)
            logger.info(
                "Flash model returned extracted context",
                extra={"session_id": self.session_id, "extracted_context": parsed},
            )
            return parsed

        except Exception as exc:
            logger.warning(f"[ListenerAgent] Flash call failed: {exc}")
            return None

    def _merge_context(self, context: dict) -> None:
        """Merge new context into accumulated state (non-destructive)."""
        for key in ("seller_price", "user_offer", "user_target_price", "user_max_price", "counterparty_sentiment", "research_query"):
            if context.get(key) is not None:
                self.last_context[key] = context[key]

        # Contamination guard: if a user pricing field equals the seller_price, Flash likely
        # heard the user REFERENCE the counterparty's price and incorrectly assigned it to
        # the buyer fields. Reject those values to prevent role confusion in the Live AI.
        seller_price = self.last_context.get("seller_price")
        if seller_price is not None:
            for field in ("user_offer", "user_target_price", "user_max_price"):
                if self.last_context.get(field) == seller_price:
                    logger.warning(
                        f"[ListenerAgent] Rejecting {field}={seller_price} — matches seller_price "
                        f"(likely contamination from user referencing counterparty's price)"
                    )
                    self.last_context[field] = None

        # FIX: Never downgrade the item - if we already have a specific item name,
        # don't overwrite it with a generic term like "phone" or "it"
        new_item = context.get("item")
        old_item = self.last_context.get("item")
        if new_item is not None:
            # Only update if: no previous item, OR new item is longer/more specific
            if old_item is None or len(new_item) > len(old_item):
                self.last_context["item"] = new_item
            # Log if we blocked a downgrade
            elif old_item and len(new_item) < len(old_item):
                logger.info(f"[ListenerAgent] Blocking item downgrade: '{old_item}' -> '{new_item}'")

        snippet = context.get("transcript_snippet", "")
        if snippet:
            speaker = getattr(self.session, 'current_speaker', 'unknown')
            label = "User" if speaker == "user" else "Counterparty"
            labeled = f"{label}: {snippet}"
            self.accumulated_transcript = (
                (self.accumulated_transcript + "\n" + labeled)[-2000:]
            )

        # Accumulate key moments and leverage points (deduplicated and capped)
        for field in ("key_moments", "leverage_points"):
            existing = self.last_context.get(field, [])
            new_items = context.get(field, [])
            
            # Add new items if they aren't already in the list
            for item in new_items:
                if item not in existing:
                    existing.append(item)
            
            # FIX: Cap the list to the 5 most recent items so the context doesn't grow forever
            # and cause the AI to repeatedly react to old triggers
            self.last_context[field] = existing[-5:]

    def _has_context_changed(self, context: dict) -> bool:
        """Check if any meaningful context has changed since last sent to AI."""
        if not self._last_sent_context:
            return True  # First time, always send
        
        last_sent = self._last_sent_context
        
        # Compare key fields that matter for the AI
        if context.get("item") != last_sent.get("item"):
            return True
        if context.get("seller_price") != last_sent.get("seller_price"):
            return True
        if context.get("user_offer") != last_sent.get("user_offer"):
            return True
        if context.get("user_target_price") != last_sent.get("user_target_price"):
            return True
        if context.get("user_max_price") != last_sent.get("user_max_price"):
            return True
        if context.get("counterparty_sentiment") != last_sent.get("counterparty_sentiment"):
            return True
        
        # Compare lists (key_moments, leverage_points)
        new_moments = context.get("key_moments", [])
        old_moments = last_sent.get("key_moments", [])
        if set(new_moments) != set(old_moments):
            return True
        
        new_leverage = context.get("leverage_points", [])
        old_leverage = last_sent.get("leverage_points", [])
        if set(new_leverage) != set(old_leverage):
            return True
        
        # Compare transcript snippet
        new_snippet = context.get("transcript_snippet", "")
        old_snippet = last_sent.get("transcript_snippet", "")
        if new_snippet != old_snippet:
            return True
        
        return False

    def _update_last_sent_context(self, context: dict) -> None:
        """Update the last sent context after successfully sending to AI."""
        self._last_sent_context = {
            "item": context.get("item"),
            "seller_price": context.get("seller_price"),
            "user_offer": context.get("user_offer"),
            "user_target_price": context.get("user_target_price"),
            "user_max_price": context.get("user_max_price"),
            "counterparty_sentiment": context.get("counterparty_sentiment"),
            "key_moments": context.get("key_moments", []),
            "leverage_points": context.get("leverage_points", []),
            "transcript_snippet": context.get("transcript_snippet", ""),
        }

    async def _send_context_update(self, context: dict) -> None:
        """Send CONTEXT_UPDATE to the frontend WebSocket."""
        try:
            payload = {
                "type": "CONTEXT_UPDATE",
                "payload": {
                    "item": self.last_context.get("item"),
                    "seller_price": self.last_context.get("seller_price"),
                    "user_offer": self.last_context.get("user_offer"),
                    "user_target_price": self.last_context.get("user_target_price"),
                    "user_max_price": self.last_context.get("user_max_price"),
                    "sentiment": self.last_context.get("counterparty_sentiment", "unknown"),
                    "key_moments": self.last_context.get("key_moments", []),
                    "leverage_points": self.last_context.get(
                        "leverage_points", []
                    ),
                    "transcript_snippet": context.get("transcript_snippet", ""),
                    "market_data": self.last_context.get("market_data"),
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
        if self.last_context.get("market_data"):
            parts.append(f"Market Research: {self.last_context['market_data']}")

        # Recent transcript
        if self.accumulated_transcript:
            recent = self.accumulated_transcript[-600:]
            parts.append(f"Recent conversation: \"{recent}\"")

        return "\n".join(parts)
