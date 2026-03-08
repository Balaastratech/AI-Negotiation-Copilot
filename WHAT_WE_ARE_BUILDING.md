# What We Are Building - AI Negotiation Copilot Redesign

## PROJECT GOAL
Transform the AI Negotiation Copilot from a slow turn-based system into a fast button-triggered advice system for hackathon demo.

---

## THE CORE PROBLEM WE'RE SOLVING

**Current System:**
- User speaks → 10-20 second wait → AI responds
- Too slow for real-time negotiation
- Connection timeouts during long waits

**Target System:**
- AI listens silently to entire negotiation
- User taps button when they need advice
- AI responds instantly (3-5 seconds)
- Goes back to silent listening

---

## WHAT WE DECIDED TO BUILD

### Architecture: 4 Components

**Component 1: Gemini Live API Session (Silent Listener)**
- VAD DISABLED via `automaticActivityDetection: { disabled: true }`
- Receives continuous audio stream (user + seller both speaking)
- Receives 1fps video stream (optional, add later)
- AI stays SILENT by default
- Only speaks when triggered by button tap

**Component 2: Button-Tap Trigger System**
- User presses "Ask AI" button
- App sends: `activityStart` + `ADVISOR_QUERY` text + `activityEnd`
- Gemini responds with voice advice
- Returns to silent mode after response

**Component 3: Local Voice Fingerprinting (Speaker Diarization)**

- **Enrollment Phase**: User speaks 2-3 sentences during setup
- **Extract Voice Features**: MFCC (Mel-Frequency Cepstral Coefficients) from user's voice
- **Real-Time Matching**: Compare each audio chunk to user's voiceprint
- **Label Transcript**: Tag each sentence as [USER] or [COUNTERPARTY]
- **Send to Gemini**: Labeled transcript in `ADVISOR_QUERY`

**Component 4: Client-Side State Manager**
- Tracks negotiation context in JavaScript object
- Updated from: transcript, button taps, research results
- Injected into every `ADVISOR_QUERY`
- This is how AI "remembers" context

---

## KEY FEATURES CONFIRMED FROM GOOGLE DOCS

### ✅ VAD Disable (CONFIRMED)
```javascript
realtimeInputConfig: {
  automaticActivityDetection: { disabled: true }
}
```
**Source:** Official Google AI documentation
**What it does:** AI won't auto-respond after silence detection
**Why critical:** Solves the 10-20 second latency problem

### ✅ Manual Activity Control (CONFIRMED)
```javascript
// Button tap triggers this sequence:
await session.send({ activityStart: {} });
await session.send("ADVISOR_QUERY: [state] What should I say?");
await session.send({ activityEnd: {} });
```
**What it does:** Tells AI when to speak
**Why critical:** User controls when AI responds

### ✅ Function Calling (CONFIRMED)
```javascript
tools: [{
  functionDeclarations: [{
    name: "search_market_price",
    description: "Search current market price for item",
    parameters: { item: "string", location: "string" }
  }]
}]
```
**What it does:** AI autonomously triggers research when needed
**Why critical:** No timer-based polling, intent-driven research

### ✅ Google Search Grounding (CONFIRMED)
```javascript
tools: [{ googleSearch: {} }]
```
**What it does:** Built-in web search for market data
**Why critical:** Real-time pricing without separate API

### ❌ Voice Enrollment (NOT CONFIRMED)
**Status:** No documentation for real-time voice matching in Live API
**Decision:** We'll implement local voice fingerprinting instead

---

## WHAT WE'RE IMPLEMENTING

### Phase 1: Core System (Priority 1)

**1. VAD Disable + Button-Tap Control**
- Disable automatic VAD in Gemini config
- Add "Ask AI" button to UI
- Implement `activityStart` + `ADVISOR_QUERY` + `activityEnd` flow
- **Time:** 2 hours
- **Risk:** Low (confirmed feature)

**2. Local Voice Fingerprinting**
- Enrollment: Extract MFCC features from user's voice during setup
- Real-time: Compare each audio chunk to voiceprint
- Label: Tag transcript as [USER] or [COUNTERPARTY]
- **Time:** 3-4 hours
- **Risk:** Medium (accuracy depends on noise)

**3. Client-Side State Manager**
- Simple JavaScript object tracking negotiation
- Fields: item, seller_price, target_price, max_price, market_data, transcript
- Updated from transcript and button taps
- **Time:** 1 hour
- **Risk:** Low

**4. Function Calling for Research**
- Define `search_market_price` function
- AI triggers when it hears product mentioned
- Returns market price range
- **Time:** 2 hours
- **Risk:** Low (confirmed feature)

**Total Phase 1: 8-9 hours**

---

### Phase 2: Enhancements (If Time Permits)

**5. 1fps Video Stream**
- Capture video frame every 1 second
- Send as base64 JPEG to Gemini
- AI builds visual context
- **Time:** 2 hours
- **Risk:** Medium (bandwidth concerns)

**6. Advanced State Object**
- Add leverage_points, counterparty_signals, negotiation_stage
- More sophisticated tracking
- **Time:** 2 hours
- **Risk:** Low

**7. Visual Improvements**
- Better UI for button
- State indicators
- Transcript styling
- **Time:** 2 hours
- **Risk:** Low

**Total Phase 2: 6 hours**

---

## TECHNICAL IMPLEMENTATION DETAILS

### Voice Fingerprinting Algorithm

**Step 1: Enrollment (Setup Phase)**
```javascript
// User speaks 2-3 sentences
const audioSamples = recordUserVoice(3000); // 3 seconds

// Extract MFCC features (voice fingerprint)
const mfcc = extractMFCC(audioSamples, {
  sampleRate: 16000,
  numCoefficients: 13,
  frameSize: 512,
  hopSize: 256
});

// Store as user voiceprint
const userVoiceprint = {
  mfcc: mfcc,
  mean: calculateMean(mfcc),
  variance: calculateVariance(mfcc)
};
```

**Step 2: Real-Time Matching (During Negotiation)**
```javascript
// For each audio chunk received
const chunkMFCC = extractMFCC(audioChunk);

// Calculate similarity to user voiceprint
const similarity = cosineSimilarity(chunkMFCC, userVoiceprint.mean);

// Threshold-based classification
if (similarity > 0.7) {
  label = "[USER]";
} else {
  label = "[COUNTERPARTY]";
}

// Add to transcript
transcript.push({ speaker: label, text: transcribedText });
```

**Libraries Needed:**
- `mfcc` npm package for MFCC extraction
- Or implement basic MFCC ourselves (FFT + Mel filterbank)

---

### Button-Tap Flow

**Frontend:**
```typescript
// User clicks "Ask AI" button
async function askAI() {
  // 1. Get current state
  const state = {
    item: "Used MacBook Pro",
    seller_price: 500,
    target_price: 400,
    max_price: 450,
    transcript: last90SecondsTranscript
  };

  // 2. Send to backend
  websocket.sendControl('ASK_ADVICE', { state });
}
```

**Backend:**
```python
# Receive ASK_ADVICE message
async def handle_ask_advice(session, state):
    # Build ADVISOR_QUERY text
    query = f"""
    ADVISOR_QUERY:
    STATE: {json.dumps(state)}
    TRANSCRIPT: {state['transcript']}
    QUESTION: What should I say right now?
    """
    
    # Send to Gemini with activity control
    await session.send({"activityStart": {}})
    await session.send(query)
    await session.send({"activityEnd": {}})
    
    # Gemini responds with voice
    # After response, goes back to silent mode
```

---

### Gemini Configuration

**New Config (With VAD Disabled):**
```python
config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    
    # DISABLE VAD - Manual control
    realtime_input_config=types.RealtimeInputConfig(
        automatic_activity_detection=types.AutomaticActivityDetection(
            disabled=True
        )
    ),
    
    # Function calling for research
    tools=[
        types.Tool(google_search=types.GoogleSearch()),
        types.Tool(function_declarations=[
            types.FunctionDeclaration(
                name="search_market_price",
                description="Search current market price for item",
                parameters={
                    "type": "object",
                    "properties": {
                        "item": {"type": "string"},
                        "location": {"type": "string"}
                    }
                }
            )
        ])
    ],
    
    # Short responses for speed
    generation_config=types.GenerationConfig(
        temperature=0.7,
        max_output_tokens=150
    ),
    
    # Transcription
    input_audio_transcription=types.AudioTranscriptionConfig(),
    output_audio_transcription=types.AudioTranscriptionConfig(),
    
    system_instruction=build_system_prompt(context)
)
```

---

## STATE OBJECT STRUCTURE

### Simple Version (Phase 1):
```javascript
{
  item: "Used MacBook Pro 2020",
  seller_price: 500,
  target_price: 400,
  max_price: 450,
  market_low: 380,
  market_high: 520,
  transcript: "[USER] How much? [COUNTERPARTY] ₹500..."
}
```

### Advanced Version (Phase 2):
```javascript
{
  item: "Used MacBook Pro 2020",
  context: "marketplace",
  counterparty_latest_offer: 500,
  user_ideal_price: 400,
  user_walkaway_price: 450,
  market_range: { low: 380, mid: 450, high: 520 },
  research_notes: "Found 3 listings at ₹420-480",
  transcript_summary: "Seller started at ₹500, user countered ₹400",
  leverage_points: ["Visible scratch on corner", "Market average is ₹450"],
  counterparty_signals: ["flexibility", "urgency"],
  negotiation_stage: "countering"
}
```

---

## SYSTEM PROMPT (Final Version)

**Key Sections:**

**1. Operating States:**
- STATE 1: PASSIVE (default) - Listen silently, never speak
- STATE 2: ACTIVE (button tap) - Respond instantly with advice

**2. Voice Recognition:**
- User voice learned during enrollment
- All other voices = COUNTERPARTY
- Label all transcript entries

**3. Response Format:**
```
[What to say - one sentence]
[Why - the leverage - one sentence]
[Fallback if they resist - optional]
```

**4. Video Intelligence:**
- Continuous 1fps stream (optional)
- Convert observations to leverage
- Never describe, always advise

**5. Interruption Handling:**
- Stop mid-sentence if interrupted
- Adapt to new context
- Never say "as I was saying"

---

## USER EXPERIENCE FLOW

### Setup Phase:
1. User accepts privacy consent
2. System: "Please speak 2-3 sentences so I can learn your voice"
3. User speaks: "Hi, I'm here to negotiate. I want a good deal on this laptop."
4. System extracts voiceprint, stores it
5. System: "Got it. What are you negotiating and what's your target price?"
6. User: "Used MacBook Pro, I want to pay ₹40,000 max"
7. System: "Perfect. I'll stay silent. Tap 'Ask AI' when you need advice."
8. **Negotiation begins**

### During Negotiation:
```
[Seller speaks]: "This MacBook is ₹50,000"
[System silently labels]: [COUNTERPARTY] ₹50,000
[System silently updates]: seller_price = 50000

[User speaks]: "That seems high"
[System silently labels]: [USER] That seems high

[User taps "Ask AI" button]
[System sends]: ADVISOR_QUERY with full state
[AI responds in 3-5s]: "Offer ₹38,000. Market range is ₹38-45k. 
                        Point to any visible wear to justify."
[System returns to silent mode]

[User speaks to seller]: "I can offer ₹38,000"
[System silently labels]: [USER] ₹38,000

[Seller speaks]: "I can do ₹45,000"
[System silently labels]: [COUNTERPARTY] ₹45,000
[System updates]: seller_price = 45000

[User taps button again]
[AI responds]: "That's within market range. Accept if condition is good, 
                or counter at ₹42,000 if you see any issues."
```

---

## WHAT MAKES THIS WORK

### 1. No VAD Latency
- VAD disabled = no 10-20s wait
- Manual control = instant response
- Button tap = user decides when

### 2. Pre-Built Context
- AI has been listening the whole time
- Transcript already captured
- State already updated
- No cold start when button tapped

### 3. Voice Fingerprinting
- Separates user from seller
- Hands-free operation
- No need for headset or manual labeling

### 4. Function Calling
- AI autonomously researches when needed
- No timer-based polling
- Intent-driven, efficient

---

## IMPLEMENTATION PRIORITY

### MUST HAVE (Phase 1 - 8 hours):
1. VAD disable + button-tap control
2. Voice fingerprinting for diarization
3. Simple state object (6 fields)
4. Function calling for market research
5. Basic UI with "Ask AI" button

### NICE TO HAVE (Phase 2 - 6 hours):
6. 1fps video streaming
7. Advanced state object
8. Visual state indicators
9. Better UI/UX

### POLISH (Phase 3 - 2 hours):
10. Error handling
11. Demo script
12. Backup scenarios

---

## TECHNICAL DECISIONS MADE

### Voice Fingerprinting Approach:
**Method:** MFCC (Mel-Frequency Cepstral Coefficients)
**Why:** Industry standard for voice recognition
**Threshold:** 0.7 cosine similarity
**Fallback:** If accuracy poor, user can manually label or use headset

### Audio Streaming:
**Chunk Size:** 100ms (1600 samples @ 16kHz)
**Format:** Int16 PCM, little-endian
**Why:** Balance between latency and stability

### Video Streaming:
**Frame Rate:** 1fps (optional, Phase 2)
**Resolution:** 640x480
**Format:** JPEG base64
**Why:** Enough for context, not overwhelming

### Research Strategy:
**Trigger:** Function calling (AI decides)
**Not:** Timer-based polling
**Why:** More efficient, intent-driven

### State Management:
**Location:** Client-side (frontend)
**Not:** Server-side or Gemini memory
**Why:** Fast, reliable, we control it

---

## WHAT WE'RE NOT DOING

### ❌ Continuous Video (Initially)
- Too much bandwidth
- Adds latency
- Not critical for demo
- Can add later

### ❌ Timer-Based Research Polling
- Wasteful API calls
- Adds complexity
- Function calling is better

### ❌ Complex State Object (Initially)
- Start simple (6 fields)
- Add complexity later if needed

### ❌ Server-Side Voice Matching
- Gemini doesn't support it
- We do it client-side instead

---

## EXPECTED LATENCY

### Current System:
- User speaks → 10-20s wait → AI responds
- **Total: 11-22 seconds**

### New System:
- User taps button → 3-5s → AI responds
- **Total: 3-5 seconds**

### Breakdown:
1. Button tap → Bundle state (100ms)
2. Send to backend (200ms)
3. activityStart + ADVISOR_QUERY + activityEnd (300ms)
4. Gemini processes (2-3s)
5. Audio generation (1s)
6. Stream back (500ms)
**Total: 4-5 seconds**

---

## FILES TO MODIFY

### Backend (Python):
1. `backend/app/services/gemini_client.py`
   - Add VAD disable config
   - Add activityStart/End handling
   - Add function calling setup

2. `backend/app/services/master_prompt.py`
   - Update prompt for button-tap model
   - Add ADVISOR_QUERY format
   - Add voice recognition instructions

3. `backend/app/api/websocket.py`
   - Add ASK_ADVICE message handler

4. `backend/app/services/negotiation_engine.py`
   - Add handle_ask_advice method

### Frontend (TypeScript/React):
1. `frontend/lib/audio-worklet-manager.ts`
   - Add voice fingerprinting logic
   - Add MFCC extraction
   - Add similarity matching

2. `frontend/hooks/useNegotiation.ts`
   - Add askAdvice function
   - Add state management
   - Add voiceprint storage

3. `frontend/components/negotiation/ControlBar.tsx`
   - Add "Ask AI" button

4. `frontend/lib/types.ts`
   - Add ASK_ADVICE message type
   - Add voiceprint types

5. `frontend/lib/websocket.ts`
   - Add sendAskAdvice method

### New Files:
1. `frontend/lib/voice-fingerprint.ts`
   - MFCC extraction
   - Similarity calculation
   - Voiceprint matching

---

## TESTING STRATEGY

### Test 1: VAD Disable
**Goal:** Verify AI stays silent
**Steps:**
1. Start session with VAD disabled
2. Speak into mic for 5 seconds
3. Wait 30 seconds
4. Verify AI doesn't respond
**Pass:** No AI response

### Test 2: Button-Tap Response
**Goal:** Verify button triggers AI
**Steps:**
1. Speak: "How much for this laptop?"
2. Tap "Ask AI" button
3. Measure time to first audio
**Pass:** Response in 3-5 seconds

### Test 3: Voice Fingerprinting
**Goal:** Verify speaker separation
**Steps:**
1. Complete enrollment
2. User speaks: "Hello"
3. Different person speaks: "Hi there"
4. Check transcript labels
**Pass:** Correctly labeled [USER] and [COUNTERPARTY]

### Test 4: Function Calling
**Goal:** Verify autonomous research
**Steps:**
1. Speak: "This iPhone 14 Pro is ₹85,000"
2. Tap button
3. Check if AI mentions market data
**Pass:** AI references market prices

### Test 5: Multi-Turn
**Goal:** Verify continuous operation
**Steps:**
1. Complete 5 button-tap cycles
2. Verify state persists
3. Verify no connection drops
**Pass:** All 5 cycles work

---

## RISK MITIGATION

### Risk 1: Voice Fingerprinting Accuracy
**Mitigation:**
- Test with different noise levels
- Adjust similarity threshold (0.7 → 0.6 or 0.8)
- Fallback: Manual labeling or headset

### Risk 2: Connection Timeouts
**Mitigation:**
- Keep audio streaming continuous
- Add WebSocket keepalive pings
- Reconnection logic

### Risk 3: Latency Still Too High
**Mitigation:**
- Remove video if needed
- Reduce state object size
- Optimize prompt length

### Risk 4: Demo Day Internet Issues
**Mitigation:**
- Pre-record demo video
- Have offline fallback
- Test on mobile hotspot

---

## SUCCESS CRITERIA

### Must Work:
- ✅ AI stays silent until button tapped
- ✅ Button tap → response in under 5 seconds
- ✅ Speaker labels are mostly accurate (>80%)
- ✅ AI gives relevant advice based on context
- ✅ No connection drops during demo

### Nice to Have:
- ✅ Video context working
- ✅ Function calling triggers automatically
- ✅ Advanced state tracking
- ✅ Polished UI

---

## DEMO SCRIPT (For Hackathon)

**Scenario:** Buying a used laptop

**Setup:**
1. Show privacy consent screen
2. Voice enrollment: "Hi, I'm here to negotiate a good deal on a laptop"
3. Context input: "Used MacBook Pro, target ₹40,000"

**Negotiation:**
1. **Seller:** "This MacBook Pro is ₹50,000"
2. **User taps button**
3. **AI:** "Offer ₹38,000. Market range is ₹38-45k for this model."
4. **User to seller:** "I can offer ₹38,000"
5. **Seller:** "Too low. I can do ₹47,000"
6. **User taps button**
7. **AI:** "Counter at ₹42,000. That's fair market value. Mention any visible wear."
8. **User to seller:** "₹42,000 final, I see some scratches here"
9. **Seller:** "Okay, ₹42,000 deal"
10. **Done**

**Demo Time:** 2-3 minutes
**Shows:** Button-tap control, speaker separation, market research, adaptive advice

---

## NEXT STEPS

1. **Read this document completely**
2. **Confirm understanding of architecture**
3. **Start with Phase 1 implementation**
4. **Test each component as we build**
5. **Add Phase 2 features if time permits**

---

## QUESTIONS TO RESOLVE BEFORE CODING

### Q1: Voice Fingerprinting Library
**Options:**
- A: Use `mfcc` npm package (easier, 1 hour)
- B: Implement MFCC ourselves (harder, 3 hours)
- C: Use Web Audio API's AnalyserNode (simpler, less accurate)

**Decision needed:** Which approach?

### Q2: Video Streaming
**Options:**
- A: Skip video entirely (Phase 1)
- B: Add 1fps streaming (Phase 2)
- C: Snapshot on button tap only

**Decision needed:** Which approach?

### Q3: State Object Complexity
**Options:**
- A: Simple (6 fields) - Phase 1
- B: Advanced (12 fields) - Phase 2

**Decision needed:** Start simple or go full?

### Q4: Testing Priority
**Options:**
- A: Test each component individually
- B: Build everything, test at end
- C: Build MVP, test, then iterate

**Decision needed:** Testing strategy?

---

## ESTIMATED TIMELINE

**Day 1 (8 hours):**
- VAD disable + button control (2h)
- Voice fingerprinting (4h)
- State management (1h)
- Function calling (1h)

**Day 2 (6 hours):**
- Testing + bug fixes (3h)
- UI improvements (2h)
- Demo preparation (1h)

**Day 3 (Optional - 4 hours):**
- Video streaming (2h)
- Advanced features (2h)

**Total: 14-18 hours**

---

## THIS DOCUMENT IS YOUR REFERENCE

Before writing any code:
1. Re-read this document
2. Confirm which phase we're in
3. Check what's already implemented
4. Verify dependencies are ready
5. Then start coding

**This ensures we don't forget decisions or duplicate work.**
