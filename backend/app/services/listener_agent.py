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

POLL_INTERVAL = 2           # seconds between extraction cycles
WINDOW_SECONDS = 10         # audio window sent to Flash each cycle (fallback audio path)
MIN_NEW_AUDIO = 1.5         # minimum seconds of new audio required before extraction
FLASH_MODEL = "gemini-2.5-flash"       # context extraction model
FAST_TRANSCRIBE_MODEL = "gemini-2.5-flash"  # STT model for per-segment transcription (same as FLASH_MODEL)

# ── Text extraction prompt (used when labeled transcript is available) ─────────
# Text→text is 5-10x faster than audio→text. Once we have a labeled transcript
# from the event-driven per-segment STT, we use this instead of the audio path.
_TEXT_EXTRACTION_PROMPT = """Analyze this labeled negotiation transcript and extract context.
Return strict JSON only — no markdown, no extra text.
{
  "item": "specific name of what is being negotiated. null only if completely unclear.",
  "negotiation_type": "one of: buying_goods | selling_goods | renting | salary | service | contract | other | unknown — from the USER's perspective.",
  "buyer_offer": null,
  "counterparty_price": null,
  "user_price": null,
  "user_target_price": null,
  "user_walk_away_price": null,
  "counterparty_goal": "one sentence — what counterparty wants beyond price. null if unknown.",
  "key_moments": [],
  "leverage_points": [],
  "counterparty_sentiment": "positive|neutral|negative|unknown",
  "research_query": "precise search query for current market value. null if item too generic.",
  "research_needed": false,
  "research_gap": null,
  "transcript_snippet": "verbatim excerpt of the most important exchange (max 400 chars)"
}

ATTRIBUTION RULES:
- Lines starting with "User [" or "User:" = statements by the USER
- Lines starting with "Counterparty [" or "Counterparty:" = statements by the COUNTERPARTY
- Price stated in a User line → user_price (and buyer_offer if user is buying)
- Price stated in a Counterparty line → counterparty_price
- NEVER assign the same price to both buyer_offer and counterparty_price unless they agreed

Transcript:
"""

EXTRACTION_PROMPT = """You are analyzing a snippet of a live negotiation conversation.
Extract the following in strict JSON (no markdown, no extra text):
{
  "item": "specific name of what is being negotiated — product, service, role, property, or deal. Be as specific as possible. null only if completely unclear.",
  "negotiation_type": "one of: buying_goods | selling_goods | renting | salary | service | contract | other | unknown — ALWAYS from the USER's perspective. If the COUNTERPARTY is selling, the USER is buying → use buying_goods. If the COUNTERPARTY is buying, the USER is selling → use selling_goods.",
  "buyer_offer": <number or null - what price has the BUYER offered? This is what the buyer is willing to pay.>,
  "counterparty_price": <number or null - what price is the COUNTERPARTY (the other party, not the user) asking for or offering?>,
  "user_price": <number or null - what price has the USER stated they want or are offering?>,
  "user_target_price": <number or null - what price does the USER ultimately want to achieve?>,
  "user_walk_away_price": <number or null - the USER's absolute limit - won't go beyond this price.>,
  "counterparty_goal": "one sentence — what the counterparty is trying to achieve beyond just price (e.g. quick sale, fill vacancy, hit monthly target, reduce risk). null if unknown.",
  "key_moments": ["one-sentence each — notable things said that shift the negotiation"],
  "leverage_points": ["one-sentence each, max 3 — any time pressure, information asymmetry, alternatives, weaknesses, or advantages relevant to this specific type of negotiation"],
  "counterparty_sentiment": "positive|neutral|negative|unknown",
  "research_query": "A precise search query to find current fair market value or benchmarks for this specific negotiation. Tailor to the domain — for goods use price comparison sites, for salary use compensation data, for hotels use booking rates, for rentals use local listings. Include the year. CRITICAL: Return null if the item is too generic (e.g. just 'car', 'phone', 'house', 'laptop') without specific details like make/model/year/location. Only return a query if you have enough specifics to get meaningful results.",
  "research_needed": <true or false — set true if you are uncertain about something that would materially help the user and a web search could resolve it>,
  "research_gap": "A specific question you cannot answer from the audio alone that a web search could resolve — e.g. 'Is $150/night above market for a 3-star hotel in this city in low season?', 'What are common pressure tactics used by car dealers and how to counter them?', 'What is the typical salary range for this role in this industry?'. null if research_needed is false.",
  "transcript_snippet": "verbatim excerpt of the most important exchange (max 400 chars)"
}

CRITICAL PRICE ATTRIBUTION RULES:
- Use speaker labels (User: / Counterparty:) in the transcript to determine who said what
- If USER says "I want to sell for $X" → user_price=$X, seller_asking_price=$X
- If USER says "I'll offer $X" or "I'll pay $X" → user_price=$X, buyer_offer=$X
- If COUNTERPARTY says "I'm selling for $X" → counterparty_price=$X, seller_asking_price=$X
- If COUNTERPARTY says "I'll pay $X" or "I offer $X" → counterparty_price=$X, buyer_offer=$X
- ALWAYS fill both the role-specific fields (buyer_offer/seller_asking_price) AND the role-agnostic fields (user_price/counterparty_price)
- NEVER put the same price in both buyer_offer and seller_asking_price unless they actually agreed on a price

If audio is silent/unclear return all nulls. Prices should be numbers only (no currency symbols).
Set research_needed=true when: you don't know the fair market value, you heard a claim you can't verify, you detected a tactic you're unsure how to counter in this domain, or the item/scenario is unusual and you lack specific knowledge to help the user effectively.
IMPORTANT: Do not generate a research_query for generic items without specifics. Examples of TOO GENERIC: "car" (need make/model/year), "phone" (need brand/model), "house" (need location/size), "laptop" (need brand/specs). Only generate research_query when you have actionable details.
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
        
        # Track audio buffer position to detect new audio
        self._last_processed_duration: float = 0.0
        
        # Force next extraction flag (set by manual speaker identification)
        self._force_next_extraction: bool = False
        
        # Research state
        self._last_research_query: str = ""
        # Time-based minimum cooldown — prevents spam even with event-driven triggers
        self._last_research_timestamp: float = 0.0
        # Track what item/type research was last run for — triggers re-research on change
        self._last_researched_item: str = ""
        self._last_researched_type: str = ""
        # Count of critical events since last research — triggers re-research on accumulation
        self._critical_events_since_research: int = 0
        # Last research_gap searched — prevents re-searching the same uncertainty
        self._last_research_gap: str = ""
        
        # Queue for critical events detected before copilot is activated
        self._pre_activation_critical_events: list[dict] = []

        # Session start time — used to compute relative timestamps in transcript
        self._session_start_time: float = time.time()

        # Debounce for text extraction (max once per 1.5s)
        self._last_text_extraction_time: float = 0.0

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
    # Event-driven fast transcription (called by NegotiationEngine on speaker switch)
    # ------------------------------------------------------------------

    async def transcribe_segment(
        self,
        speaker: str,
        audio: bytes,
        start_time: float,
        end_time: float,
    ) -> None:
        """
        Called by NegotiationEngine when a speaker turn ends (button switch).
        Transcribes the audio slice immediately (~1-1.5s) and:
          - Appends a labeled line to accumulated_transcript
          - Sends TRANSCRIPT_UPDATE to the frontend sidebar
          - Triggers a fast text-based context extraction cycle
        """
        if len(audio) < 3200:  # < 0.1s of audio — skip noise
            return

        duration = len(audio) / 32000
        logger.info(f"[ListenerAgent] Fast-transcribing {speaker} segment: {duration:.1f}s")

        try:
            text = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._fast_transcribe(audio)
            )
        except Exception as exc:
            logger.warning(f"[ListenerAgent] Fast transcription failed: {exc}")
            return

        if not text or not text.strip():
            return

        text = text.strip()
        label = "User" if speaker == "user" else "Counterparty"

        # Timestamp relative to session start
        elapsed = start_time - self._session_start_time
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        ts_str = f"{mins}:{secs:02d}"

        # Append to accumulated transcript (this is what future text extractions read)
        self.accumulated_transcript += f"\n{label} [{ts_str}]: {text}"
        # Keep transcript bounded
        if len(self.accumulated_transcript) > 8000:
            self.accumulated_transcript = self.accumulated_transcript[-6000:]

        logger.info(f"[ListenerAgent] Transcript line: {label}: {text[:100]}")

        # Push to frontend sidebar immediately
        try:
            await self.websocket.send_json({
                "type": "TRANSCRIPT_UPDATE",
                "payload": {
                    "id": f"seg_{int(start_time * 1000)}",
                    "speaker": speaker,
                    "text": text,
                    "timestamp": int(start_time * 1000),
                    "start_time": start_time,
                    "end_time": end_time,
                },
            })
        except Exception as exc:
            logger.warning(f"[ListenerAgent] TRANSCRIPT_UPDATE send failed: {exc}")

        # Immediately extract updated negotiation context from the new transcript
        asyncio.create_task(self._run_text_extraction_cycle())

    def _fast_transcribe(self, audio_bytes: bytes) -> str:
        """
        Synchronous STT — run in executor to avoid blocking the event loop.
        Converts PCM to WAV, sends to gemini-2.0-flash, returns raw transcript text.
        """
        import struct

        def _pcm_to_wav(pcm_data: bytes) -> bytes:
            sr, nc, sw = 16000, 1, 2
            br = sr * nc * sw
            ba = nc * sw
            ds = len(pcm_data)
            hdr = struct.pack(
                "<4sI4s4sIHHIIHH4sI",
                b"RIFF", 36 + ds, b"WAVE", b"fmt ", 16, 1, nc,
                sr, br, ba, sw * 8, b"data", ds,
            )
            return hdr + pcm_data

        wav_bytes = _pcm_to_wav(audio_bytes)
        audio_b64 = base64.b64encode(wav_bytes).decode()

        response = self._client.models.generate_content(
            model=FAST_TRANSCRIBE_MODEL,
            contents=[
                genai_types.Content(parts=[
                    genai_types.Part(
                        inline_data=genai_types.Blob(
                            data=audio_b64,
                            mime_type="audio/wav",
                        )
                    ),
                    genai_types.Part(
                        text=(
                            "Transcribe the speech in this audio clip. "
                            "Return ONLY the spoken words verbatim. "
                            "No labels, no timestamps, no formatting, no commentary."
                        )
                    ),
                ])
            ],
            config=genai_types.GenerateContentConfig(temperature=0.0),
        )
        return (response.text or "").strip()

    async def _run_text_extraction_cycle(self) -> None:
        """
        Fast context extraction from the labeled text transcript (~0.5-1s).
        Text→text is 5-10x faster than the audio extraction path.
        Debounced to run at most once every 1.5s to avoid hammering the API.
        """
        # Debounce
        now = time.time()
        if now - self._last_text_extraction_time < 1.5:
            return
        self._last_text_extraction_time = now

        transcript = self.accumulated_transcript.strip()
        if not transcript or len(transcript) < 20:
            return

        if getattr(self.session, "user_addressing_ai", False):
            return  # Don't extract during Ask AI window

        prompt = _TEXT_EXTRACTION_PROMPT + transcript[-2500:]

        def do_extract():
            return self._client.models.generate_content(
                model=FLASH_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(temperature=0.1),
            )

        try:
            response = await asyncio.get_event_loop().run_in_executor(None, do_extract)
            raw = (response.text or "").strip()
            if raw.startswith("```"):
                raw = "\n".join(raw.split("\n")[1:]).rstrip("`").strip()
            if not raw:
                return
            context = json.loads(raw)
        except Exception as exc:
            logger.warning(f"[ListenerAgent] Text extraction failed: {exc}")
            return

        # Same post-processing as audio path
        await self._post_process_context(context)

    async def _post_process_context(self, context: dict) -> None:
        """
        Common post-extraction processing shared by both the audio path (_run_cycle)
        and the text path (_run_text_extraction_cycle):
          - Detect critical events
          - Merge into accumulated state
          - Send CONTEXT_UPDATE to frontend
          - Inject into Live AI (if copilot active)
          - Trigger market research if needed
        """
        # ── Critical event detection ────────────────────────────────────────
        critical_events: list[dict] = []

        new_price = context.get("seller_asking_price") or context.get("counterparty_price")
        old_price = self.last_context.get("seller_asking_price") or self.last_context.get("counterparty_price")
        if new_price is not None and new_price != old_price:
            critical_events.append({
                "event_type": "ANCHOR_DETECTED",
                "detail": {"new_price": new_price, "old_price": old_price},
            })

        prev_sentiment = self.last_context.get("counterparty_sentiment")
        new_sentiment = context.get("counterparty_sentiment")
        if prev_sentiment in ("positive", "neutral") and new_sentiment == "negative":
            critical_events.append({
                "event_type": "SENTIMENT_NEGATIVE",
                "detail": {"from": prev_sentiment, "to": new_sentiment},
            })

        _URGENCY_KEYWORDS = (
            "urgent", "deadline", "today only", "last offer", "final price",
            "need to sell", "leaving", "other buyer",
        )
        for moment in context.get("key_moments", []):
            if any(kw in moment.lower() for kw in _URGENCY_KEYWORDS):
                critical_events.append({"event_type": "URGENCY_DETECTED", "detail": {"moment": moment}})
                break

        _PRESSURE_MARKERS = (
            "scarc", "limited", "only one", "last chance", "take it or leave",
            "now or never", "emotional", "guilt", "pressure", "final", "ultimatum",
        )
        for text in (context.get("leverage_points", []) + context.get("key_moments", [])):
            if any(m in text.lower() for m in _PRESSURE_MARKERS):
                critical_events.append({"event_type": "PRESSURE_TACTIC", "detail": {"text": text}})
                break

        # ── Merge + forward ─────────────────────────────────────────────────
        self._merge_context(context)
        await self._send_context_update(context)

        if not self.session.copilot_active:
            if critical_events:
                self._pre_activation_critical_events.extend(critical_events)
        elif self._on_context_ready:
            context_changed = self._has_context_changed(self.last_context)
            if context_changed or critical_events:
                if context_changed:
                    self._update_last_sent_context(self.last_context)
                await self._on_context_ready(self.last_context, critical_events)

        if critical_events:
            self._critical_events_since_research += len(critical_events)

        # ── Market research trigger ──────────────────────────────────────────
        new_query = self.last_context.get("research_query")
        research_gap = context.get("research_gap")
        research_needed = context.get("research_needed", False)
        _RESEARCH_COOLDOWN_SECS = 90
        current_time = time.time()
        cooldown_passed = (current_time - self._last_research_timestamp) > _RESEARCH_COOLDOWN_SECS

        if cooldown_passed and not self._research_task:
            current_item = self.last_context.get("item") or ""
            current_type = self.last_context.get("negotiation_type") or ""
            market_data_missing = not self.last_context.get("market_data")
            item_changed = current_item and current_item != self._last_researched_item
            type_changed = current_type and current_type != self._last_researched_type
            critical_pressure = self._critical_events_since_research >= 2
            first_research = not self._last_researched_item
            has_price_context = any(
                self.last_context.get(f) is not None
                for f in ("seller_asking_price", "buyer_offer", "counterparty_price", "user_price", "user_target_price")
            )
            gap_is_new = (
                research_needed and research_gap and research_gap != self._last_research_gap
            )
            should_research = (
                (first_research and has_price_context)
                or item_changed or type_changed
                or (market_data_missing and current_item)
                or critical_pressure or gap_is_new
            ) and (new_query or gap_is_new)

            if should_research:
                reason = (
                    "ai_uncertainty" if gap_is_new and not (first_research or item_changed or type_changed)
                    else "first_research" if first_research
                    else "item_changed" if item_changed
                    else "type_changed" if type_changed
                    else "market_data_missing" if market_data_missing
                    else "critical_pressure"
                )
                effective_query = research_gap if gap_is_new else new_query
                logger.info(f"[ListenerAgent] Triggering research ({reason}): '{effective_query}'")
                self._last_research_timestamp = current_time
                self._last_researched_item = current_item
                self._last_researched_type = current_type
                self._critical_events_since_research = 0
                if gap_is_new:
                    self._last_research_gap = research_gap
                self._research_task = asyncio.create_task(
                    self._run_market_research(
                        effective_query, reason,
                        research_gap if gap_is_new else None,
                    )
                )

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

        # Skip while user is speaking directly to the AI — prevents their question
        # from polluting negotiation context extraction.
        if getattr(self.session, "user_addressing_ai", False):
            logger.debug("[ListenerAgent] Skipping cycle — user is addressing AI")
            return

        # ── FAST PATH: text-based extraction ────────────────────────────────
        # Once we have a labeled transcript from event-driven per-segment STT,
        # use text extraction (0.5-1s) instead of audio extraction (2-5s).
        if self.accumulated_transcript and len(self.accumulated_transcript.strip()) > 30:
            await self._run_text_extraction_cycle()
            return

        # ── MANUAL SPEAKER MODE: skip audio path entirely ───────────────────
        # When the user has clicked a speaker button (speaker_segment_start > 0),
        # speaker labeling is 100% owned by event-driven transcribe_segment().
        # The audio path cannot know who spoke what — it will always get it wrong
        # in races between button clicks and async processing.
        if getattr(self.session, 'speaker_segment_start', 0) > 0:
            logger.debug("[ListenerAgent] Skipping audio cycle — manual speaker mode active")
            return

        # ── SLOW PATH: audio extraction (fallback before any transcript) ────
        current_duration = self.audio_buffer.duration_seconds

        logger.debug(
            f"[ListenerAgent] Cycle {self._cycle_count} (audio) — "
            f"buffer={current_duration:.1f}s, last_processed={self._last_processed_duration:.1f}s"
        )

        # 1. Check if we have enough NEW audio since last extraction
        new_audio_duration = current_duration - self._last_processed_duration
        if not self._force_next_extraction and new_audio_duration < MIN_NEW_AUDIO:
            logger.debug(
                f"[ListenerAgent] Only {new_audio_duration:.1f}s of new audio "
                f"(need {MIN_NEW_AUDIO}s), skipping extraction"
            )
            return

        if self._force_next_extraction:
            logger.info(
                f"[ListenerAgent] Force extraction triggered — "
                f"re-extracting last {WINDOW_SECONDS}s with correct speaker context"
            )
            self._force_next_extraction = False

        # 2. Grab audio window
        audio_bytes = self.audio_buffer.get_window(WINDOW_SECONDS)
        if len(audio_bytes) < 3200:  # < 0.1s of audio — skip
            logger.debug("[ListenerAgent] Not enough audio yet, skipping")
            return
        
        # Update the last processed position BEFORE extraction
        # (so if extraction fails, we'll retry with the same audio next cycle)
        self._last_processed_duration = current_duration

        # 3. Build speaker-segmented audio (Solution 1 + Solution 2 combined)
        # Split the 15s window into per-speaker chunks using the timeline,
        # AND inject the timeline as a hint for Flash to handle overlaps.
        now = time.time()
        window_start_ts = now - WINDOW_SECONDS
        speaker_timeline = getattr(self.session, 'speaker_timeline', [])

        # Filter timeline entries within the current window
        window_entries = [e for e in speaker_timeline if e.get("timestamp", 0) >= window_start_ts]

        # Build segments: list of {speaker, start_seconds_ago, end_seconds_ago}
        # "seconds_ago" is relative to NOW so we can use get_segment()
        segments = []
        if window_entries:
            for i, entry in enumerate(window_entries):
                seg_start_ts = entry["timestamp"]
                seg_end_ts = window_entries[i + 1]["timestamp"] if i + 1 < len(window_entries) else now
                start_ago = now - seg_start_ts
                end_ago = now - seg_end_ts
                # Clamp to window bounds
                start_ago = min(start_ago, WINDOW_SECONDS)
                end_ago = max(end_ago, 0.0)
                if start_ago > end_ago:
                    audio_chunk = self.audio_buffer.get_segment(start_ago, end_ago)
                    if len(audio_chunk) >= 3200:  # at least 0.1s
                        segments.append({
                            "speaker": entry["speaker"],
                            "audio": audio_chunk,
                            "start_ago": start_ago,
                            "end_ago": end_ago,
                        })

        # Fall back to full window if no timeline data
        if not segments:
            segments = [{"speaker": getattr(self.session, 'current_speaker', 'unknown'), "audio": audio_bytes, "start_ago": WINDOW_SECONDS, "end_ago": 0.0}]

        logger.info(
            f"[ListenerAgent] Cycle {self._cycle_count} — "
            f"{len(segments)} speaker segment(s): "
            + str([f"{s['speaker']}({s['start_ago']:.1f}s-{s['end_ago']:.1f}s)" for s in segments])
        )

        # 4. Call Flash with segments + timeline hint
        context = await asyncio.get_event_loop().run_in_executor(
            None, self._call_flash, audio_bytes, segments
        )
        if context is None:
            return
        
        # 2.5. Process diarization if present (audio path only)
        # Skip diarization when manual speaker buttons are in use — the event-driven
        # transcribe_segment() is the authoritative label source in that case.
        manual_until = getattr(self.session, 'manual_override_until', 0) or 0
        if "diarization" in context and context["diarization"] and time.time() >= manual_until:
            await self._process_diarization(context["diarization"])

        # Shared post-processing: events, merge, inject, research
        await self._post_process_context(context)

    async def _run_market_research(self, research_query: str, trigger_reason: str = "scheduled", research_gap: str = None) -> None:
        """Run asynchronous market research using Gemini Flash with Google Search."""
        try:
            # Notify frontend that research has started
            await self.websocket.send_json({
                "type": "RESEARCH_STARTED",
                "payload": {"query": research_query}
            })

            # Build context snapshot for the prompt
            item = self.last_context.get("item") or "unknown"
            negotiation_type = self.last_context.get("negotiation_type") or "unknown"
            counterparty_goal = self.last_context.get("counterparty_goal") or "unknown"
            seller_price = (
                self.last_context.get("counterparty_price")
                or self.last_context.get("seller_asking_price")
            )
            key_moments = self.last_context.get("key_moments", [])
            leverage_points = self.last_context.get("leverage_points", [])

            context_summary = (
                f"Item/Subject: {item}\n"
                f"Negotiation Type: {negotiation_type}\n"
                f"Counterparty Goal: {counterparty_goal}\n"
                f"Counterparty's Current Price/Rate: {seller_price}\n"
                f"Key Moments So Far: {'; '.join(key_moments) if key_moments else 'none'}\n"
                f"Known Leverage Points: {'; '.join(leverage_points) if leverage_points else 'none'}\n"
                f"Research Trigger: {trigger_reason}"
            )

            research_prompt = f"""
You are providing real-time intelligence to help someone negotiate RIGHT NOW.

CURRENT NEGOTIATION CONTEXT:
{context_summary}

{"SPECIFIC KNOWLEDGE GAP TO RESOLVE: " + research_gap if research_gap else "SEARCH QUERY: " + '"' + research_query + '"'}

Search the internet and return ONLY a valid JSON object with no markdown:
{{
  "price_range": "The fair market range as a specific number range with source (e.g. '$X–$Y on Booking.com', '$X–$Y/year per Glassdoor', '$X–$Y on eBay sold listings'). null if not found.",
  "key_facts": "One critical fact that directly affects the value or negotiating position in this specific scenario — depreciation, seasonal demand, vacancy rate, industry benchmark, known defects, supply/demand conditions. null if not found.",
  "leverage": "One specific leverage point the user can deploy in the next 60 seconds — a competing alternative, a market condition, a timing pressure on the counterparty, or an information advantage. Make it concrete and actionable.",
  "tactics": "Two or three real-world negotiation tactics that expert negotiators use specifically for this type of deal ({negotiation_type}). Base these on actual negotiation research and what works in practice for this domain. Format as: 'Tactic 1: [name] — [one sentence how to use it]. Tactic 2: [name] — [one sentence]. Tactic 3: [name] — [one sentence].'",
  "gap_answer": "{('Direct answer to: ' + research_gap) if research_gap else 'null'} — answer this specific question from your search results. null if no knowledge gap was provided."
}}

Rules:
- Be specific with numbers — give a range, not vague language
- Tailor everything to the domain: {negotiation_type}
- tactics must be real techniques adapted to this exact scenario
- If trigger_reason is 'critical_pressure', prioritize counter-tactics to pressure moves
- If trigger_reason is 'ai_uncertainty', prioritize answering the knowledge gap directly
- If no price data found, state the closest relevant benchmark
"""

            logger.info(
                "Running market research",
                extra={
                    "session_id": self.session_id,
                    "research_query": research_query,
                    "trigger_reason": trigger_reason,
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
            
            # Build a rich formatted string from the structured fields
            # so all downstream code that reads market_data as a string still works
            parts = []
            if market_data.get("price_range"):
                parts.append(f"Price Range: {market_data['price_range']}")
            if market_data.get("key_facts"):
                parts.append(f"Key Facts: {market_data['key_facts']}")
            if market_data.get("leverage"):
                parts.append(f"Leverage: {market_data['leverage']}")
            if market_data.get("tactics"):
                parts.append(f"Tactics: {market_data['tactics']}")
            if market_data.get("gap_answer") and market_data["gap_answer"] != "null":
                parts.append(f"Gap Answer: {market_data['gap_answer']}")
            insights = " | ".join(parts) if parts else "No market data found."

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

    def _build_speaker_timeline_hint(self) -> str:
        """
        Build a speaker timeline hint for the current audio window.

        Reads the session's speaker_timeline (list of {speaker, timestamp} entries)
        and produces a human-readable map of who spoke when within the last
        WINDOW_SECONDS. This replaces the single 'primary speaker' hint so Flash
        can attribute prices to the correct person even in mixed-speaker windows.

        Returns a formatted string to prepend to the extraction prompt.
        """
        timeline = getattr(self.session, 'speaker_timeline', [])
        current_speaker = getattr(self.session, 'current_speaker', 'unknown')
        now = time.time()
        window_start = now - WINDOW_SECONDS

        # Filter to entries within the current audio window
        window_entries = [e for e in timeline if e.get("timestamp", 0) >= window_start]

        if not window_entries:
            # No timeline data yet — use current_speaker as fallback
            if current_speaker == "unknown":
                return (
                    "SPEAKER CONTEXT: Speaker identity not yet confirmed. "
                    "Use conversation content and context to infer who is making each statement. "
                    "Do not assume any price belongs to a specific role — infer from language cues "
                    "(e.g. 'I want', 'my price', 'I can offer' = likely the person speaking; "
                    "'they want', 'asking for' = referencing the other party).\n\n"
                )
            elif current_speaker == "user":
                return (
                    "SPEAKER CONTEXT: The most recently identified speaker is the USER. "
                    "Attribute price statements to user fields unless language clearly indicates "
                    "they are referencing the counterparty's price.\n\n"
                )
            else:
                return (
                    "SPEAKER CONTEXT: The most recently identified speaker is the COUNTERPARTY. "
                    "Attribute price statements to seller_price unless language clearly indicates "
                    "they are referencing the user's offer.\n\n"
                )

        # Build a relative-time timeline for the window
        lines = ["SPEAKER TIMELINE for this audio window (use this to attribute who said what):"]
        prev_ts = window_start
        for i, entry in enumerate(window_entries):
            ts = entry.get("timestamp", prev_ts)
            speaker = entry.get("speaker", "unknown")
            rel_start = max(0.0, ts - window_start)
            # End of this speaker's turn = start of next entry or end of window
            if i + 1 < len(window_entries):
                rel_end = min(WINDOW_SECONDS, window_entries[i + 1].get("timestamp", now) - window_start)
            else:
                rel_end = WINDOW_SECONDS
            lines.append(f"  {rel_start:.1f}s – {rel_end:.1f}s : {speaker.upper()}")
            prev_ts = ts

        lines.append(
            "Use this timeline to determine who said each price or statement. "
            "A price mentioned during a USER turn → user fields. "
            "A price mentioned during a COUNTERPARTY turn → seller_price. "
            "If someone quotes the other party's price (e.g. 'you said $800'), "
            "do NOT assign it to their own fields — it is a reference, not an offer."
        )
        return "\n".join(lines) + "\n\n"

    async def _process_diarization(self, diarization: list) -> None:
        """
        Process diarization results from Gemini Pro.
        
        If enrollment audio was provided, Gemini labels speakers as "USER" or "COUNTERPARTY" directly.
        If no enrollment, Gemini uses "Speaker 1" and "Speaker 2" - we need manual mapping.
        """
        if not diarization:
            return
        
        current_time = time.time()
        enrollment_audio = getattr(self.session, 'enrollment_audio', None)
        
        for turn in diarization:
            speaker_label = turn.get("speaker", "")  # "USER", "COUNTERPARTY", "Speaker 1", or "Speaker 2"
            text = turn.get("text", "")
            start_time = turn.get("start_time", 0.0)
            
            if not speaker_label or not text:
                continue
            
            # Map speaker label to our internal format
            if speaker_label in ("USER", "COUNTERPARTY"):
                # Gemini already labeled it correctly (enrollment audio was used)
                our_speaker = speaker_label.lower()
            elif speaker_label in ("Speaker 1", "Speaker 2"):
                # No enrollment - need to map generic labels
                # Initialize mapping if needed
                if not hasattr(self.session, 'speaker_mapping'):
                    self.session.speaker_mapping = {}
                
                if speaker_label not in self.session.speaker_mapping:
                    # Wait for manual identification via SPEAKER_IDENTIFIED message
                    logger.info(
                        f"[Diarization] {speaker_label} detected but no mapping yet - "
                        f"waiting for manual identification"
                    )
                    continue
                
                our_speaker = self.session.speaker_mapping[speaker_label]
            else:
                logger.warning(f"[Diarization] Unknown speaker label: {speaker_label}")
                continue
            
            # Update session state
            self.session.current_speaker = our_speaker
            self.session.speaker_last_updated = current_time
            
            # Add to timeline
            self.session.speaker_timeline.append({
                "speaker": our_speaker,
                "timestamp": current_time - WINDOW_SECONDS + start_time,
            })
            
            # Send transcript with speaker label to frontend
            await self.websocket.send_json({
                "type": "TRANSCRIPT_UPDATE",
                "payload": {
                    "speaker": our_speaker,
                    "text": text,
                    "timestamp": current_time - WINDOW_SECONDS + start_time,
                }
            })
            
            logger.info(f"[Diarization] {our_speaker.upper()}: {text[:80]}...")
        
        # Keep timeline manageable
        if len(self.session.speaker_timeline) > 300:
            self.session.speaker_timeline = self.session.speaker_timeline[-300:]

    def _call_flash(self, audio_bytes: bytes, segments: list = None) -> Optional[dict]:
        """
        Synchronous call to Gemini Flash (run in executor so it doesn't
        block the event loop).  Returns parsed context dict or None.

        Solution 1: If segments are provided, sends each speaker's audio chunk
        separately with a label so Flash knows exactly who said what.
        Solution 2: Also injects a speaker timeline hint for handling overlaps.
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

            # Convert current audio to WAV
            wav_bytes = pcm_to_wav(audio_bytes)
            audio_b64 = base64.b64encode(wav_bytes).decode("utf-8")

            # Check if we have enrollment audio for speaker matching
            enrollment_audio = getattr(self.session, 'enrollment_audio', None)
            
            # Build parts list
            parts = []
            
            if enrollment_audio:
                # Convert enrollment audio to WAV
                enrollment_wav = pcm_to_wav(enrollment_audio)
                enrollment_b64 = base64.b64encode(enrollment_wav).decode("utf-8")
                
                # Add enrollment audio as reference
                enrollment_part = genai_types.Part(
                    inline_data=genai_types.Blob(
                        mime_type="audio/wav",
                        data=enrollment_b64,
                    )
                )
                parts.append(enrollment_part)
                
                # Add instruction about reference audio
                reference_instruction = genai_types.Part(
                    text="☝️ REFERENCE AUDIO ABOVE: This is the USER's voice. Remember these voice characteristics.\n\n"
                )
                parts.append(reference_instruction)

            # Solution 1: Add per-speaker audio segments with labels if available
            # Solution 2: Fall back to full audio + timeline hint if only one segment
            if segments and len(segments) > 1:
                # Multiple segments — send each chunk labeled with speaker
                for seg in segments:
                    speaker_label = seg["speaker"].upper()
                    seg_wav = pcm_to_wav(seg["audio"])
                    seg_b64 = base64.b64encode(seg_wav).decode("utf-8")
                    # Label before each audio chunk
                    parts.append(genai_types.Part(text=f"[{speaker_label} speaking — {seg['start_ago']:.1f}s to {seg['end_ago']:.1f}s ago]\n"))
                    parts.append(genai_types.Part(
                        inline_data=genai_types.Blob(mime_type="audio/wav", data=seg_b64)
                    ))
                timeline_hint = "SPEAKER SEGMENTS (authoritative — use these to attribute prices and statements):\n"
                for seg in segments:
                    timeline_hint += f"  {seg['start_ago']:.1f}s–{seg['end_ago']:.1f}s ago: {seg['speaker'].upper()}\n"
                timeline_hint += "Each audio chunk above is labeled with its speaker. Attribute all statements accordingly.\n\n"
                parts.append(genai_types.Part(text=timeline_hint))
            else:
                # Single segment or no timeline — send full audio with timeline hint (Solution 2)
                audio_part = genai_types.Part(
                    inline_data=genai_types.Blob(mime_type="audio/wav", data=audio_b64)
                )
                parts.append(audio_part)
                if segments:
                    speaker_label = segments[0]["speaker"].upper()
                    parts.append(genai_types.Part(
                        text=f"SPEAKER CONTEXT: The speaker in this audio is {speaker_label}.\n\n"
                    ))

            # Build prompt
            known_item = self.last_context.get("item")
            if known_item:
                prompt_with_item = f"""The negotiation is about: {known_item}.
Extract the following in strict JSON (no markdown, no extra text):
{{
  "item": "{known_item}",
  "negotiation_type": "one of: buying_goods | selling_goods | renting | salary | service | contract | other | unknown — ALWAYS from the USER's perspective. If the COUNTERPARTY is selling, the USER is buying → use buying_goods. If the COUNTERPARTY is buying, the USER is selling → use selling_goods.",
  "buyer_offer": <number or null - what price has the BUYER offered?>,
  "counterparty_price": <number or null - what price is the COUNTERPARTY asking for or offering?>,
  "user_price": <number or null - what price has the USER stated?>,
  "user_target_price": <number or null - what price does the USER ultimately want to achieve?>,
  "user_walk_away_price": <number or null - the USER's absolute limit>,
  "counterparty_goal": "one sentence — what the counterparty is trying to achieve beyond just price. null if unknown.",
  "key_moments": ["one-sentence each — notable things said that shift the negotiation"],
  "leverage_points": ["one-sentence each, max 3 — time pressure, information asymmetry, alternatives, weaknesses, or advantages"],
  "counterparty_sentiment": "positive|neutral|negative|unknown",
  "research_query": "A precise search query to find current fair market value or benchmarks for {known_item}. Tailor to the domain. Include the year. Return null if not enough specifics.",
  "transcript_snippet": "verbatim excerpt of the most important exchange (max 400 chars)"
}}
If audio is silent/unclear return all nulls. Prices should be numbers only (no currency symbols).
IMPORTANT: Keep the item as "{known_item}" — do not replace it with generic terms."""
            else:
                prompt_with_item = EXTRACTION_PROMPT

            # Add diarization instruction
            if enrollment_audio:
                diarization_prompt = """
CRITICAL SPEAKER IDENTIFICATION:
Compare the voices in the CURRENT AUDIO (above) to the REFERENCE AUDIO (at the top).
- The voice that MATCHES the reference = label as "USER"
- The OTHER voice = label as "COUNTERPARTY"

Add a "diarization" field to your JSON response:
"diarization": [
  {"speaker": "USER" or "COUNTERPARTY", "text": "exact words spoken", "start_time": 0.0},
  {"speaker": "USER" or "COUNTERPARTY", "text": "exact words spoken", "start_time": 2.5}
]

Use voice characteristics (pitch, tone, speaking style) to match against the reference.

"""
            else:
                diarization_prompt = """
SPEAKER IDENTIFICATION (No reference available):
Distinguish between two speakers based on voice characteristics.
Label them as "Speaker 1" and "Speaker 2" consistently.

Add a "diarization" field to your JSON response:
"diarization": [
  {"speaker": "Speaker 1" or "Speaker 2", "text": "exact words spoken", "start_time": 0.0},
  {"speaker": "Speaker 1" or "Speaker 2", "text": "exact words spoken", "start_time": 2.5}
]

"""
            
            full_prompt = diarization_prompt + prompt_with_item
            text_part = genai_types.Part(text=full_prompt)
            parts.append(text_part)

            logger.info(
                "Calling Flash model for speaker matching + context extraction",
                extra={
                    "session_id": self.session_id,
                    "has_enrollment": enrollment_audio is not None,
                    "audio_duration_seconds": len(audio_bytes) / 32000,
                },
            )

            response = self._client.models.generate_content(
                model=self._flash_model,
                contents=[genai_types.Content(parts=parts)],
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
                "Flash model returned extracted context with diarization",
                extra={"session_id": self.session_id, "extracted_context": parsed},
            )
            return parsed

        except Exception as exc:
            logger.warning(f"[ListenerAgent] Flash call failed: {exc}")
            return None

    def _merge_context(self, context: dict) -> None:
        """Merge new context into accumulated state (non-destructive)."""
        # Option 1 (role-agnostic) + Option 3 (role-specific) field names
        for key in ("seller_asking_price", "buyer_offer", "counterparty_price", "user_price", "user_target_price", "user_walk_away_price", "counterparty_sentiment", "research_query", "negotiation_type", "counterparty_goal"):
            if context.get(key) is not None:
                self.last_context[key] = context[key]

        # Contamination guard: if buyer_offer equals seller_asking_price, this might be
        # legitimate (they agreed on price) OR contamination (someone referenced the other's price).
        # We'll allow it but log a warning for monitoring.
        seller_price = self.last_context.get("seller_asking_price")
        buyer_price = self.last_context.get("buyer_offer")
        if seller_price is not None and buyer_price is not None and seller_price == buyer_price:
            logger.warning(
                f"[ListenerAgent] buyer_offer={buyer_price} matches seller_asking_price={seller_price}. "
                f"This could be agreement or contamination. Keeping both for now."
            )

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
            # FIX: Use speaker_timeline to determine who spoke during this audio window
            # instead of just using current_speaker (which might have changed)
            
            # Get the time range for this audio window
            current_time = time.time()
            window_start = current_time - WINDOW_SECONDS
            
            # Find the most recent speaker identification within this window
            speaker_timeline = getattr(self.session, 'speaker_timeline', [])
            
            # Default to current speaker if no timeline data
            speaker = getattr(self.session, 'current_speaker', 'unknown')
            
            if speaker_timeline:
                # Find who was speaking at the START of the audio window.
                # Check within the window first; if the button was pressed before the window
                # started, look backward in the timeline so we don't fall back to the CURRENT
                # speaker (which may have changed since the audio was captured).
                speakers_in_window = [
                    entry for entry in speaker_timeline
                    if entry['timestamp'] >= window_start and entry['timestamp'] <= current_time
                ]

                if speakers_in_window:
                    # Use the FIRST speaker entry in the window
                    speaker = speakers_in_window[0]['speaker']
                else:
                    # Button press was before window_start — find the last entry before the window
                    pre_window = [e for e in speaker_timeline if e['timestamp'] < window_start]
                    if pre_window:
                        speaker = pre_window[-1]['speaker']  # most recent entry before window

                logger.debug(
                    f"[ListenerAgent] Speaker timeline attribution: "
                    f"window={window_start:.1f}-{current_time:.1f}, "
                    f"in_window={len(speakers_in_window)}, selected={speaker}"
                )
            
            label = "User" if speaker == "user" else "Counterparty"
            labeled = f"{label}: {snippet}"
            
            logger.info(
                f"[ListenerAgent] Labeled transcript: speaker={label}, "
                f"snippet='{snippet[:80]}...'"
            )
            
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
            "negotiation_type": context.get("negotiation_type"),
            "seller_price": context.get("seller_price"),
            "user_offer": context.get("user_offer"),
            "user_target_price": context.get("user_target_price"),
            "user_max_price": context.get("user_max_price"),
            "counterparty_sentiment": context.get("counterparty_sentiment"),
            "counterparty_goal": context.get("counterparty_goal"),
            "key_moments": context.get("key_moments", []),
            "leverage_points": context.get("leverage_points", []),
            "transcript_snippet": context.get("transcript_snippet", ""),
        }

    async def _send_context_update(self, context: dict) -> None:
        """Send CONTEXT_UPDATE to the frontend WebSocket."""
        try:
            # Resolve counterparty price: prefer counterparty_price, fall back to seller_asking_price
            counterparty_price = (
                self.last_context.get("counterparty_price")
                or self.last_context.get("seller_asking_price")
            )
            # Resolve user price: prefer user_price, fall back to buyer_offer
            user_price = (
                self.last_context.get("user_price")
                or self.last_context.get("buyer_offer")
            )

            payload = {
                "type": "CONTEXT_UPDATE",
                "payload": {
                    "item": self.last_context.get("item"),
                    "negotiation_type": self.last_context.get("negotiation_type"),
                    "seller_price": counterparty_price,
                    "user_offer": user_price,
                    "user_target_price": self.last_context.get("user_target_price"),
                    "user_max_price": self.last_context.get("user_walk_away_price"),
                    "sentiment": self.last_context.get("counterparty_sentiment", "unknown"),
                    "counterparty_goal": self.last_context.get("counterparty_goal"),
                    "key_moments": self.last_context.get("key_moments", []),
                    "leverage_points": self.last_context.get("leverage_points", []),
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
        counterparty_price = (
            self.last_context.get("counterparty_price")
            or self.last_context.get("seller_asking_price")
        )
        if counterparty_price:
            parts.append(f"Counterparty is asking/offering: {counterparty_price}")
        user_price = (
            self.last_context.get("user_price")
            or self.last_context.get("buyer_offer")
        )
        if user_price:
            parts.append(f"User has offered/stated: {user_price}")
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

    def force_reextraction(self) -> None:
        """
        Force the next extraction cycle to run immediately, ignoring the
        MIN_NEW_AUDIO threshold. Used when manual speaker identification
        occurs to re-extract the last audio window with correct speaker context.
        """
        self._force_next_extraction = True
        logger.info(
            f"[ListenerAgent] Force re-extraction flag set - "
            f"next cycle will re-extract last {WINDOW_SECONDS}s with updated speaker"
        )

    def force_immediate_cycle(self) -> None:
        """
        Trigger an out-of-band extraction cycle right now, bypassing the poll interval
        and MIN_NEW_AUDIO gate. Call this when the user requests advice/command so they
        get fresh context immediately instead of waiting for the next scheduled cycle.
        """
        if self._running:
            self._force_next_extraction = True
            asyncio.create_task(
                self._run_cycle(), name=f"listener-immediate-{self.session_id[:8]}"
            )
            logger.info(f"[ListenerAgent] Immediate extraction cycle triggered [{self.session_id}]")
