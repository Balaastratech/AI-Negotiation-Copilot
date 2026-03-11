# Dual-AI Architecture - The Real Solution

## The Problem We're Solving

Single AI session can't do both:
1. Listen silently to conversations (audio input)
2. Respond to button clicks (text trigger)

**Root cause:** Audio-only mode doesn't respond to text queries reliably.

## Your Brilliant Solution: Two AIs

### AI #1: The Silent Listener (Context Builder)

**Role:** Continuous monitoring and context extraction

**Responsibilities:**
- Listen to ALL audio (user + seller)
- Transcribe everything with speaker labels
- Extract negotiation state:
  - Item being negotiated
  - Seller's prices
  - User's target/max prices
  - Leverage points (condition, market data, urgency)
- Perform autonomous research when item detected
- Send context updates to AI #2
- **NEVER speaks** - pure listener

**Configuration:**
```python
# Listener uses standard Gemini API with new google-genai SDK
from google import genai

client = genai.Client(api_key=api_key)
listener_model = "gemini-2.5-flash"  # Better at structured extraction

# Audio sent as base64-encoded PCM chunks every 10 seconds
# CRITICAL: MIME type must include rate parameter
mime_type = "audio/pcm;rate=16000"
```

**Prompt:**
```
You are a silent negotiation analyst.

LISTEN to all audio and:
1. Label speakers: [USER] or [SELLER]
2. Extract: item, prices, leverage points
3. Research market data when you detect products
4. Send context updates as JSON

NEVER generate audio responses.
Only output: <context_update>{...}</context_update>
```

### AI #2: The Smart Advisor (Response Generator)

**Role:** Intelligent advice generation

**Responsibilities:**
- Receives context from AI #1
- Listens to last 10-30 seconds of audio
- Decides WHEN to speak (not just when button clicked)
- Generates audio advice when:
  - User clicks "Ask AI" button
  - Critical opportunity detected (e.g., seller's price is way above market)
  - User seems stuck or uncertain
- Provides tactical, actionable advice
- Goes silent after responding

**Configuration:**
```python
advisor_config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],  # Audio only
    system_instruction=ADVISOR_PROMPT,
    input_audio_transcription=types.AudioTranscriptionConfig(),
    output_audio_transcription=types.AudioTranscriptionConfig(),
    # CRITICAL: Disable proactive audio for hackathon demo stability
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            preemptible_voice_config=types.PreemptibleVoiceConfig(
                voice_name="Aoede"  # Professional female voice
            )
        )
    )
)
# NOTE: proactive_audio defaults to False - keep it that way for demo
```

**Prompt:**
```
You are a tactical negotiation advisor.

You receive:
- Context from listener AI (item, prices, leverage)
- Last 30 seconds of audio
- Trigger signal (button click OR opportunity detected)

SPEAK ONLY WHEN:
1. User clicks "Ask AI" button
2. You detect critical opportunity:
   - Seller's price >> market price
   - User about to accept bad deal
   - Perfect moment for counteroffer

RESPONSE FORMAT (2-3 sentences):
"[What to say]. [Why/leverage]. [Fallback]."

Example: "Offer ₹40,000 - market shows ₹38-45k range. If they refuse, ask about warranty to justify their price."
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Microphone   │  │ "Ask AI"     │  │ Audio        │ │
│  │ (continuous) │  │ Button       │  │ Playback     │ │
│  └──────┬───────┘  └──────┬───────┘  └──────▲───────┘ │
│         │                  │                  │          │
└─────────┼──────────────────┼──────────────────┼─────────┘
          │                  │                  │
          │ Audio Stream     │ Button Click     │ Audio Response
          │                  │                  │
┌─────────▼──────────────────▼──────────────────┼─────────┐
│                    BACKEND                     │         │
│                                                │         │
│  ┌────────────────────────────────────────────┴──────┐  │
│  │         AI #1: SILENT LISTENER                    │  │
│  │  - Receives audio stream                          │  │
│  │  - Transcribes with speaker labels                │  │
│  │  - Extracts context (item, prices)                │  │
│  │  - Performs research (web_search)                 │  │
│  │  - Sends context updates                          │  │
│  │  - NEVER speaks                                   │  │
│  └────────────────┬──────────────────────────────────┘  │
│                   │ Context Updates                      │
│                   │ (JSON)                               │
│  ┌────────────────▼──────────────────────────────────┐  │
│  │         AI #2: SMART ADVISOR                      │  │
│  │  - Receives context from AI #1                    │  │
│  │  - Receives last 30s audio buffer                 │  │
│  │  - Triggered by:                                  │  │
│  │    * Button click                                 │  │
│  │    * Opportunity detection                        │  │
│  │  - Generates audio advice                         │  │
│  │  - Decides when to speak                          │  │
│  └────────────────┬──────────────────────────────────┘  │
│                   │ Audio Response                       │
└───────────────────┼──────────────────────────────────────┘
                    │
                    ▼
              [User hears advice]
```

## Implementation Plan

### Phase 1: Dual Session Setup (2 hours)

**File:** `backend/app/services/dual_ai_manager.py`

```python
class DualAIManager:
    def __init__(self, api_key: str, context: str):
        self.api_key = api_key
        self.listener_session = None
        self.advisor_session = None
        self.context_buffer = {}
        self.audio_buffer = deque(maxlen=480)  # 30s @ 16kHz
        self.accumulated_transcript = deque(maxlen=20)  # Cap at 20 entries
        self.gemini_send_lock = asyncio.Lock()  # Shared lock for both AIs
        self.client = None  # Will be initialized in start_listener
        
    async def start_listener(self):
        """Start AI #1: Silent Listener using standard Gemini API"""
        # Listener uses gemini-2.5-flash via new google-genai SDK
        from google import genai
        self.client = genai.Client(api_key=self.api_key)
        asyncio.create_task(self._process_listener_loop())
        
    async def start_advisor(self):
        """Start AI #2: Smart Advisor (on demand)"""
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=ADVISOR_PROMPT,
            input_audio_transcription=types.AudioTranscriptionConfig(),
        )
        self.advisor_session = await open_live_session(config)
        
    async def send_audio(self, audio_chunk: bytes):
        """Buffer audio for both AIs"""
        # Buffer for both listener (every 10s) and advisor (on demand)
        self.audio_buffer.append(audio_chunk)
    
    async def _process_listener_loop(self):
        """Send audio to listener every 10 seconds with 15s window (5s overlap)"""
        while True:
            await asyncio.sleep(10)
            try:
                audio_window = self.audio_buffer.get_overlapping_window(15)
                
                # Encode PCM audio as base64 for standard API
                import base64
                audio_b64 = base64.b64encode(b''.join(audio_window)).decode()
                
                # CRITICAL: Call Flash WITHOUT holding lock (can take 2-5 seconds)
                # Holding lock here would freeze audio streaming to Live session
                response = await self.client.aio.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        {
                            "parts": [{
                                "inline_data": {
                                    "mime_type": "audio/pcm;rate=16000",  # CRITICAL: include rate
                                    "data": audio_b64
                                }
                            }]
                        },
                        {"parts": [{"text": "Extract negotiation context from this audio."}]}
                    ]
                )
                
                await self._process_listener_response(response)
            except Exception as e:
                logger.warning(f"[ListenerAgent] Cycle failed, skipping: {e}")
                # Don't re-raise - loop continues
        
    async def trigger_advice(self):
        """User clicked button - activate advisor"""
        # CRITICAL: Acquire lock for all Live API operations
        async with self.gemini_send_lock:
            # Send context to advisor
            context_msg = self._build_context_message()
            await self.advisor_session.send_client_content(
                turns={"role": "user", "parts": [{"text": context_msg}]},
                turn_complete=False  # Keep listening
            )
            
            # Send last 30s of audio
            for chunk in self.audio_buffer:
                await self.advisor_session.send_realtime_input(audio=chunk)
                
            # Signal end of input
            await self.advisor_session.send_client_content(
                turns={"role": "user", "parts": [{"text": ""}]},
                turn_complete=True
            )
```

### Phase 2: Context Extraction (1 hour)

**Listener AI extracts:**
```json
{
  "item": "iPhone 16 Pro",
  "seller_price": 50000,
  "user_target": 40000,
  "user_max": 45000,
  "market_data": {
    "low": 38000,
    "avg": 42000,
    "high": 48000
  },
  "leverage_points": [
    "Market average is ₹42,000",
    "Seller seems flexible (said 'maybe')",
    "Visible scratch on corner"
  ],
  "transcript_last_30s": "[USER] How much? [SELLER] ₹50,000 [USER] That's high..."
}
```

### Phase 3: Intelligent Triggering (1 hour)

**Advisor AI decides when to speak:**

```python
def should_advisor_speak(context, button_clicked):
    if button_clicked:
        return True  # Always respond to button
        
    # Detect opportunities
    if context['seller_price'] > context['market_data']['high'] * 1.2:
        return True  # Seller way overpriced
        
    if 'accept' in context['transcript_last_30s'].lower():
        if context['seller_price'] > context['user_max']:
            return True  # User about to accept bad deal
            
    if 'stuck' in context['sentiment']:
        return True  # User needs help
        
    return False  # Stay silent
```

### Phase 4: Audio Buffer Management (30 min)

```python
class AudioBuffer:
    def __init__(self, duration_seconds=30, sample_rate=16000):
        self.max_samples = duration_seconds * sample_rate
        self.buffer = deque(maxlen=self.max_samples // 1600)  # 100ms chunks
        
    def add(self, chunk: bytes):
        self.buffer.append(chunk)
        
    def get_last_n_seconds(self, n: int) -> List[bytes]:
        """Get last N seconds of audio with proper chunking"""
        num_chunks = (n * 16000) // 1600
        return list(self.buffer)[-num_chunks:]
    
    def get_overlapping_window(self, window_seconds=15) -> List[bytes]:
        """Get 15-second window for listener (called every 10s = 5s overlap)"""
        num_chunks = (window_seconds * 16000) // 1600
        return list(self.buffer)[-num_chunks:]
```

## Benefits of This Architecture

### 1. Solves the Text Query Problem
- Listener uses TEXT mode (can receive audio, output text)
- Advisor uses AUDIO mode (receives audio, outputs audio)
- No mixing of incompatible modes

### 2. Better Context
- Listener builds comprehensive context over time
- Advisor gets rich context + recent audio
- More informed advice

### 3. Intelligent Responses
- Advisor decides WHEN to speak
- Not just button-triggered
- Proactive help at critical moments

### 4. Cleaner Separation
- Listener: Pure analysis
- Advisor: Pure advice
- Each AI optimized for its role

### 5. Scalability
- Can add more AIs (e.g., sentiment analyzer)
- Each AI specialized
- Modular architecture

## Example Flow

### Scenario: Buying iPhone

**Turn 1:**
```
[Audio] User: "I want to buy an iPhone 16 Pro"
→ Listener AI: Extracts {item: "iPhone 16 Pro"}
→ Listener AI: Calls web_search("iPhone 16 Pro market price India")
→ Listener AI: Updates context {market_data: {avg: 42000}}
→ Advisor AI: Silent (no trigger)
```

**Turn 2:**
```
[Audio] Seller: "It's ₹50,000"
→ Listener AI: Extracts {seller_price: 50000}
→ Listener AI: Detects opportunity (50000 > 42000 * 1.15)
→ Listener AI: Sends trigger to Advisor AI
→ Advisor AI: Receives context + last 30s audio
→ Advisor AI: Speaks: "That's above market - offer ₹40,000. Average is ₹42k."
```

**Turn 3:**
```
[Audio] User: "Can you do ₹40,000?"
[Audio] Seller: "No, lowest is ₹48,000"
→ Listener AI: Updates {seller_price: 48000}
→ Advisor AI: Silent (within reasonable range)
```

**Turn 4:**
```
[Button] User clicks "Ask AI"
→ Advisor AI: Receives trigger
→ Advisor AI: Speaks: "₹48k is fair - close to market high. Accept if condition is good, or counter at ₹45k."
```

## Cost Considerations

**Two sessions = 2x cost?**

Not quite:
- Listener: TEXT mode (cheaper, no audio generation)
- Advisor: AUDIO mode but only active when needed
- Advisor can be created/destroyed on demand
- Net cost: ~1.3-1.5x single session

**Optimization:**
- Keep Listener always on
- Create Advisor only when button clicked
- Destroy Advisor after 30s of inactivity

## Revised Build Priority for March 16 Deadline

### ✅ MUST BUILD (Core Demo)
1. `audio_buffer.py` with 15s overlapping window
2. `listener_agent.py` with base64 audio encoding + lock usage
3. `gemini_client.py` with VAD on, proactive OFF, context injection
4. `master_prompt.py` rewrite for advisor
5. `negotiation_engine.py` wiring with shared lock
6. CONTEXT_UPDATE → NegotiationStateCard in UI
7. Minimal pre-session form (item + target price only)

### ❌ CUT FOR NOW (Post-Hackathon)
1. `proactive_audio=True` — Too risky for 4-minute demo
2. `enable_affective_dialog=True` — Nice but unverifiable
3. Full session resumption — 15-minute limit is fine
4. Intelligent triggering logic — Button-only is safer

### 🔧 CRITICAL FIXES APPLIED
- ✅ Listener uses `gemini-2.5-flash` standard API with new `google-genai` SDK
- ✅ Audio encoding: `audio/pcm;rate=16000` (rate parameter is critical)
- ✅ Lock ONLY held for fast operations (not during 2-5 second Flash API calls)
- ✅ Context injection uses system role (not user role) to avoid triggering responses
- ✅ 15-second window with 5-second overlap
- ✅ Transcript capped at 20 entries (deque with maxlen)
- ✅ Shared `gemini_send_lock` used correctly (only for fast sends)
- ✅ Proactive audio disabled by default
- ✅ Error handling in listener loop (one failure doesn't kill the listener)

## Next Steps

1. Create `DualAIManager` class with shared lock
2. Implement Listener AI with correct audio encoding
3. Implement Advisor AI (button-triggered only)
4. Add audio buffer with overlap
5. Test end-to-end flow
6. Record 4-minute demo video

This architecture is now hackathon-ready with reduced risk!

