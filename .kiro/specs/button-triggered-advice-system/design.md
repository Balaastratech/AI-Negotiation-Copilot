# Design Document: Button-Triggered Advice System

## Overview

The Button-Triggered Advice System redesigns the AI Negotiation Copilot to eliminate the 10-20 second latency caused by Gemini Live API's automatic Voice Activity Detection (VAD). By disabling VAD and implementing manual activity control, the system transforms from a slow turn-based conversation into a fast, on-demand advisory system where the AI listens silently to the entire negotiation and responds instantly (3-5 seconds) when the user taps an "Ask AI" button.

The system enables hands-free negotiation where both the user and counterparty can speak naturally without interruption. The AI maintains full context awareness through continuous audio streaming, local voice fingerprinting for speaker diarization, and client-side state management. When advice is needed, a single button tap triggers an immediate response based on the complete conversation history, market research, and negotiation state.

This Phase 1 implementation focuses on five core components: VAD disable with button-tap control, local MFCC-based voice fingerprinting, client-side state management, function calling for market research, and the "Ask AI" button UI.

## Architecture

### System Architecture

The system follows a client-server architecture with real-time bidirectional communication:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React/TypeScript)              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ "Ask AI"     │  │ Voice        │  │ State        │          │
│  │ Button UI    │  │ Fingerprint  │  │ Manager      │          │
│  │              │  │ (MFCC)       │  │              │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                    │
│         └─────────────────┴─────────────────┘                    │
│                           │                                      │
│                  ┌────────▼────────┐                            │
│                  │  WebSocket      │                            │
│                  │  Client         │                            │
│                  └────────┬────────┘                            │
└───────────────────────────┼─────────────────────────────────────┘
                            │
                    WebSocket Connection
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                    Backend (Python/FastAPI)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ WebSocket    │  │ Negotiation  │  │ Gemini       │          │
│  │ Handler      │  │ Engine       │  │ Client       │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                    │
│         └─────────────────┴─────────────────┘                    │
│                           │                                      │
└───────────────────────────┼─────────────────────────────────────┘
                            │
                    Gemini Live API
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                    Gemini Live API (Google)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  • VAD Disabled (automaticActivityDetection: disabled)          │
│  • Manual Activity Control (activityStart/activityEnd)          │
│  • Function Calling (search_market_price)                       │
│  • Audio Transcription (input/output)                           │
│  • Audio Response Generation                                    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Operating Modes

The system operates in two distinct modes:

**Silent Listening Mode (Default):**
- AI receives continuous audio stream
- Transcribes all audio with speaker labels
- Updates negotiation state
- Does NOT generate responses
- Maintains connection without timeouts

**Active Response Mode (Button-Triggered):**
- User taps "Ask AI" button
- System sends activityStart message
- System sends ADVISOR_QUERY with full state
- System sends activityEnd message
- AI generates and streams audio response
- Returns to Silent Listening Mode after completion

### Data Flow

**Continuous Audio Flow (Silent Listening):**
```
User/Counterparty Speech
    → Web Audio API (16kHz, Int16 PCM)
    → Voice Fingerprinting (MFCC extraction)
    → Speaker Label ([USER] or [COUNTERPARTY])
    → WebSocket → Backend
    → Gemini Live API
    → Transcription
    → State Manager Update
```

**Button-Tap Advice Flow:**
```
User Taps Button
    → State Manager bundles current state
    → WebSocket sends ASK_ADVICE message
    → Backend receives state
    → Backend sends activityStart
    → Backend sends ADVISOR_QUERY (state + transcript)
    → Backend sends activityEnd
    → Gemini processes (2-3s)
    → Gemini generates audio response
    → Backend streams audio → Frontend
    → Audio playback
    → Return to Silent Listening Mode
```

## Components and Interfaces

### Component 1: VAD Disable and Activity Control

**Purpose:** Disable automatic Voice Activity Detection and implement manual control to eliminate 10-20 second latency.

**Location:** `backend/app/services/gemini_client.py`

**Configuration:**
```python
config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    
    # CRITICAL: Disable automatic VAD
    realtime_input_config=types.RealtimeInputConfig(
        automatic_activity_detection=types.AutomaticActivityDetection(
            disabled=True
        )
    ),
    
    # Short responses for speed
    generation_config=types.GenerationConfig(
        temperature=0.7,
        max_output_tokens=150
    ),
    
    # Enable transcription
    input_audio_transcription=types.AudioTranscriptionConfig(),
    output_audio_transcription=types.AudioTranscriptionConfig(),
    
    system_instruction=build_system_prompt(context)
)
```

**Activity Control Interface:**
```python
async def trigger_advice_response(
    live_session,
    state: dict
) -> None:
    """
    Trigger AI advice response using manual activity control.
    
    Args:
        live_session: Active Gemini Live API session
        state: Current negotiation state object
    """
    # Build ADVISOR_QUERY from state
    query = build_advisor_query(state)
    
    # Send activity control sequence
    await live_session.send({"activityStart": {}})
    await live_session.send(query)
    await live_session.send({"activityEnd": {}})
```

**ADVISOR_QUERY Format:**
```
ADVISOR_QUERY:
ITEM: {item}
SELLER_PRICE: {seller_price}
TARGET_PRICE: {target_price}
MAX_PRICE: {max_price}
MARKET_DATA: {market_data}
TRANSCRIPT:
{labeled_transcript}

QUESTION: What should I say right now?
```

### Component 2: Voice Fingerprinting (Speaker Diarization)

**Purpose:** Automatically distinguish user speech from counterparty speech using MFCC-based voice recognition.

**Location:** `frontend/lib/voice-fingerprint.ts` (new file)

**Enrollment Phase:**
```typescript
interface VoiceFingerprint {
  mfcc: number[][];  // MFCC coefficients per frame
  mean: number[];    // Mean MFCC vector
  variance: number[]; // Variance MFCC vector
}

async function enrollUserVoice(
  audioSamples: Float32Array,
  sampleRate: number = 16000
): Promise<VoiceFingerprint> {
  // Extract MFCC features
  const mfccFrames = extractMFCC(audioSamples, {
    sampleRate,
    numCoefficients: 13,
    frameSize: 512,
    hopSize: 256
  });
  
  // Calculate statistics
  const mean = calculateMean(mfccFrames);
  const variance = calculateVariance(mfccFrames);
  
  return {
    mfcc: mfccFrames,
    mean,
    variance
  };
}
```

**Real-Time Speaker Identification:**
```typescript
function identifySpeaker(
  audioChunk: Float32Array,
  userVoiceprint: VoiceFingerprint,
  threshold: number = 0.7
): 'USER' | 'COUNTERPARTY' {
  // Extract MFCC from chunk
  const chunkMFCC = extractMFCC(audioChunk, {
    sampleRate: 16000,
    numCoefficients: 13,
    frameSize: 512,
    hopSize: 256
  });
  
  // Calculate mean MFCC for chunk
  const chunkMean = calculateMean(chunkMFCC);
  
  // Calculate cosine similarity
  const similarity = cosineSimilarity(chunkMean, userVoiceprint.mean);
  
  // Threshold-based classification
  return similarity > threshold ? 'USER' : 'COUNTERPARTY';
}
```

**MFCC Extraction:**
```typescript
interface MFCCConfig {
  sampleRate: number;
  numCoefficients: number;
  frameSize: number;
  hopSize: number;
}

function extractMFCC(
  audioSamples: Float32Array,
  config: MFCCConfig
): number[][] {
  const frames: number[][] = [];
  
  // Frame the signal
  for (let i = 0; i < audioSamples.length - config.frameSize; i += config.hopSize) {
    const frame = audioSamples.slice(i, i + config.frameSize);
    
    // Apply Hamming window
    const windowed = applyHammingWindow(frame);
    
    // FFT
    const spectrum = fft(windowed);
    
    // Mel filterbank
    const melSpectrum = applyMelFilterbank(spectrum, config.sampleRate);
    
    // Log and DCT
    const logMel = melSpectrum.map(x => Math.log(x + 1e-10));
    const mfcc = dct(logMel).slice(0, config.numCoefficients);
    
    frames.push(mfcc);
  }
  
  return frames;
}
```

### Component 3: Client-Side State Manager

**Purpose:** Track negotiation context in a simple JavaScript object, updated from transcript and button taps.

**Location:** `frontend/hooks/useNegotiation.ts`

**State Object Structure:**
```typescript
interface NegotiationState {
  item: string;              // e.g., "Used MacBook Pro 2020"
  seller_price: number | null; // Latest price from counterparty
  target_price: number;      // User's ideal price
  max_price: number;         // User's walk-away price
  market_data: string | null; // Market research results
  transcript: TranscriptEntry[]; // Last 90 seconds
}

interface TranscriptEntry {
  speaker: 'USER' | 'COUNTERPARTY';
  text: string;
  timestamp: number;
}
```

**State Management Hook:**
```typescript
function useNegotiationState() {
  const [state, setState] = useState<NegotiationState>({
    item: '',
    seller_price: null,
    target_price: 0,
    max_price: 0,
    market_data: null,
    transcript: []
  });
  
  // Initialize state from user input
  const initializeState = (
    item: string,
    targetPrice: number,
    maxPrice: number
  ) => {
    setState(prev => ({
      ...prev,
      item,
      target_price: targetPrice,
      max_price: maxPrice
    }));
  };
  
  // Add transcript entry
  const addTranscriptEntry = (
    speaker: 'USER' | 'COUNTERPARTY',
    text: string
  ) => {
    setState(prev => {
      const newEntry: TranscriptEntry = {
        speaker,
        text,
        timestamp: Date.now()
      };
      
      // Keep only last 90 seconds
      const cutoffTime = Date.now() - 90000;
      const recentTranscript = [
        ...prev.transcript.filter(e => e.timestamp > cutoffTime),
        newEntry
      ];
      
      // Extract prices from transcript
      const extractedPrice = extractPriceFromText(text);
      const newSellerPrice = speaker === 'COUNTERPARTY' && extractedPrice
        ? extractedPrice
        : prev.seller_price;
      
      return {
        ...prev,
        transcript: recentTranscript,
        seller_price: newSellerPrice
      };
    });
  };
  
  // Update market data
  const updateMarketData = (data: string) => {
    setState(prev => ({
      ...prev,
      market_data: data
    }));
  };
  
  return {
    state,
    initializeState,
    addTranscriptEntry,
    updateMarketData
  };
}
```

**Price Extraction:**
```typescript
function extractPriceFromText(text: string): number | null {
  // Match common price patterns
  const patterns = [
    /₹\s*(\d+(?:,\d+)*)/,  // ₹50,000
    /\$\s*(\d+(?:,\d+)*)/,  // $500
    /(\d+(?:,\d+)*)\s*(?:rupees|dollars|bucks)/i
  ];
  
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match) {
      const priceStr = match[1].replace(/,/g, '');
      return parseInt(priceStr, 10);
    }
  }
  
  return null;
}
```

### Component 4: Function Calling for Market Research

**Purpose:** Enable AI to autonomously trigger market price research when needed.

**Location:** `backend/app/services/gemini_client.py`

**Function Declaration:**
```python
tools = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="search_market_price",
                description="Search current market price for an item. Use this when you need to know the fair market value to provide data-driven advice.",
                parameters={
                    "type": "object",
                    "properties": {
                        "item": {
                            "type": "string",
                            "description": "The item to search for (e.g., 'Used MacBook Pro 2020')"
                        },
                        "location": {
                            "type": "string",
                            "description": "Location for price search (e.g., 'India', 'USA')"
                        }
                    },
                    "required": ["item"]
                }
            )
        ]
    ),
    types.Tool(google_search=types.GoogleSearch())
]
```

**Function Implementation:**
```python
async def handle_function_call(
    function_name: str,
    args: dict,
    websocket: WebSocket
) -> dict:
    """
    Handle function calls from Gemini.
    
    Args:
        function_name: Name of the function to call
        args: Function arguments
        websocket: WebSocket connection for updates
        
    Returns:
        Function result to send back to Gemini
    """
    if function_name == "search_market_price":
        item = args.get("item", "")
        location = args.get("location", "")
        
        # Notify frontend
        await websocket.send_json({
            "type": "MARKET_RESEARCH_STARTED",
            "payload": {"item": item}
        })
        
        # Perform search (using Google Search grounding)
        result = await search_market_price(item, location)
        
        # Notify frontend with results
        await websocket.send_json({
            "type": "MARKET_RESEARCH_COMPLETE",
            "payload": result
        })
        
        return result
    
    return {"error": "Unknown function"}

async def search_market_price(
    item: str,
    location: str
) -> dict:
    """
    Search market price for an item.
    
    Returns:
        dict: {
            "low": float,
            "mid": float,
            "high": float,
            "sources": list[str]
        }
    """
    # This will be handled by Google Search grounding
    # Return format for Gemini
    return {
        "item": item,
        "location": location,
        "price_range": "Will be populated by Google Search",
        "timestamp": time.time()
    }
```

### Component 5: "Ask AI" Button UI

**Purpose:** Provide clear, accessible button for triggering AI advice.

**Location:** `frontend/components/negotiation/ControlBar.tsx`

**Button Component:**
```typescript
interface AskAIButtonProps {
  onAskAI: () => void;
  isLoading: boolean;
  isDisabled: boolean;
}

function AskAIButton({ onAskAI, isLoading, isDisabled }: AskAIButtonProps) {
  return (
    <button
      onClick={onAskAI}
      disabled={isDisabled || isLoading}
      className="ask-ai-button"
      aria-label="Ask AI for advice"
    >
      {isLoading ? (
        <>
          <Spinner size="sm" />
          <span>AI Thinking...</span>
        </>
      ) : (
        <>
          <SparklesIcon />
          <span>Ask AI</span>
        </>
      )}
    </button>
  );
}
```

**Button Handler:**
```typescript
function useAskAI(
  state: NegotiationState,
  websocket: WebSocket | null
) {
  const [isLoading, setIsLoading] = useState(false);
  
  const askAI = useCallback(async () => {
    if (!websocket || isLoading) return;
    
    setIsLoading(true);
    
    try {
      // Send ASK_ADVICE message with current state
      websocket.send(JSON.stringify({
        type: 'ASK_ADVICE',
        payload: {
          state: {
            item: state.item,
            seller_price: state.seller_price,
            target_price: state.target_price,
            max_price: state.max_price,
            market_data: state.market_data,
            transcript: formatTranscript(state.transcript)
          }
        }
      }));
      
      // Visual feedback
      // Loading state will be cleared when AI response starts
    } catch (error) {
      console.error('Failed to ask AI:', error);
      setIsLoading(false);
    }
  }, [state, websocket, isLoading]);
  
  return { askAI, isLoading };
}

function formatTranscript(entries: TranscriptEntry[]): string {
  return entries
    .map(e => `[${e.speaker}] ${e.text}`)
    .join('\n');
}
```

### Backend WebSocket Handler

**Location:** `backend/app/api/websocket.py`

**ASK_ADVICE Message Handler:**
```python
async def handle_ask_advice(
    websocket: WebSocket,
    session: NegotiationSession,
    payload: dict
) -> None:
    """
    Handle ASK_ADVICE message from frontend.
    
    Args:
        websocket: WebSocket connection
        session: Current negotiation session
        payload: Contains negotiation state
    """
    state = payload.get("state", {})
    
    # Build ADVISOR_QUERY
    query = build_advisor_query(state)
    
    # Send activity control sequence to Gemini
    live_session = session.live_session
    if not live_session:
        await websocket.send_json({
            "type": "ERROR",
            "payload": {"message": "No active Gemini session"}
        })
        return
    
    try:
        # Manual activity control
        await live_session.send({"activityStart": {}})
        await live_session.send(query)
        await live_session.send({"activityEnd": {}})
        
        # Response will be received in receive_responses loop
        # and streamed back to frontend automatically
        
    except Exception as e:
        logger.error(f"Failed to trigger advice: {e}")
        await websocket.send_json({
            "type": "ERROR",
            "payload": {"message": str(e)}
        })

def build_advisor_query(state: dict) -> str:
    """Build ADVISOR_QUERY text from state."""
    return f"""ADVISOR_QUERY:
ITEM: {state.get('item', 'Unknown')}
SELLER_PRICE: {state.get('seller_price', 'Not mentioned')}
TARGET_PRICE: {state.get('target_price', 'Unknown')}
MAX_PRICE: {state.get('max_price', 'Unknown')}
MARKET_DATA: {state.get('market_data', 'Not available')}

TRANSCRIPT:
{state.get('transcript', 'No transcript')}

QUESTION: What should I say right now? Provide concise, actionable advice."""
```

## Data Models

### Negotiation State Model

```typescript
// Frontend state model
interface NegotiationState {
  // Item being negotiated
  item: string;
  
  // Prices
  seller_price: number | null;  // Latest offer from counterparty
  target_price: number;         // User's ideal price
  max_price: number;            // User's walk-away price
  
  // Market research
  market_data: string | null;   // Market price range and sources
  
  // Conversation history (last 90 seconds)
  transcript: TranscriptEntry[];
}

interface TranscriptEntry {
  speaker: 'USER' | 'COUNTERPARTY';
  text: string;
  timestamp: number;  // Unix timestamp in milliseconds
}
```

### Voice Fingerprint Model

```typescript
interface VoiceFingerprint {
  // MFCC coefficients for all frames
  mfcc: number[][];
  
  // Statistical features for matching
  mean: number[];      // Mean MFCC vector (13 coefficients)
  variance: number[];  // Variance MFCC vector (13 coefficients)
  
  // Metadata
  sampleRate: number;  // 16000 Hz
  numCoefficients: number;  // 13
  enrollmentDuration: number;  // Duration in seconds
}
```

### Audio Configuration Model

```typescript
interface AudioConfig {
  sampleRate: 16000;           // Hz
  channelCount: 1;             // Mono
  bitDepth: 16;                // Int16
  chunkDuration: 100;          // milliseconds
  encoding: 'pcm';             // PCM format
  endianness: 'little-endian'; // Byte order
}
```

### WebSocket Message Models

```typescript
// Client → Server messages
type ClientMessage =
  | { type: 'START_SESSION'; payload: { context: string } }
  | { type: 'AUDIO_CHUNK'; payload: ArrayBuffer }
  | { type: 'ASK_ADVICE'; payload: { state: NegotiationState } }
  | { type: 'END_SESSION'; payload: {} };

// Server → Client messages
type ServerMessage =
  | { type: 'SESSION_STARTED'; payload: { session_id: string } }
  | { type: 'TRANSCRIPT_UPDATE'; payload: TranscriptUpdate }
  | { type: 'AI_LISTENING'; payload: {} }
  | { type: 'AI_SPEAKING'; payload: {} }
  | { type: 'MARKET_RESEARCH_STARTED'; payload: { item: string } }
  | { type: 'MARKET_RESEARCH_COMPLETE'; payload: MarketData }
  | { type: 'ERROR'; payload: { message: string } }
  | ArrayBuffer;  // Audio response data

interface TranscriptUpdate {
  speaker: 'user' | 'ai';
  text: string;
  timestamp: number;
}

interface MarketData {
  item: string;
  location: string;
  price_range: string;
  timestamp: number;
}
```

### Gemini API Configuration Model

```python
# Backend configuration model
@dataclass
class GeminiLiveConfig:
    """Configuration for Gemini Live API session."""
    
    # Response settings
    response_modalities: list[str] = field(default_factory=lambda: ["AUDIO"])
    
    # VAD control (CRITICAL)
    vad_disabled: bool = True
    
    # Generation settings
    temperature: float = 0.7
    max_output_tokens: int = 150
    
    # Transcription
    input_transcription_enabled: bool = True
    output_transcription_enabled: bool = True
    
    # Function calling
    tools: list = field(default_factory=list)
    
    # System prompt
    system_instruction: str = ""
```


## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property Reflection

After analyzing all acceptance criteria, I identified several areas of redundancy:

- Requirements 4.3 and 4.4 (speaker labeling based on similarity threshold) can be combined into a single comprehensive property about classification logic
- Requirements 5.6 (valid JSON) is best tested as a serialization round-trip property
- Requirements 9.2 and 5.5 (transcript retention) are duplicates and can be combined
- Requirements 2.1, 2.2, 2.3, and 2.6 (activity control sequence) can be combined into a single property about message ordering
- Requirements 11.1 and 4.5 (audio chunk format) are duplicates and can be combined
- Requirements 8.3, 8.4, and 8.5 (UI state transitions) can be combined into a single property about UI state machine
- Requirements 15.3 and 2.5 (return to silent mode) are duplicates

The following properties represent the unique, non-redundant correctness requirements for the system.

### Property 1: Silent Mode Audio Processing

For any audio chunk received while in Silent_Listening_Mode, the system should transcribe the audio and update the transcript without generating an AI response.

**Validates: Requirements 1.2, 1.4**

### Property 2: Connection Stability

For any sequence of audio chunks sent to the Gemini Live API, the connection should remain active without disconnections, regardless of whether AI responses are generated.

**Validates: Requirements 1.5**

### Property 3: Activity Control Message Sequence

For any button tap event, the system should send messages in the exact sequence: activityStart → ADVISOR_QUERY → activityEnd, and this sequence should complete without errors.

**Validates: Requirements 2.1, 2.2, 2.3, 2.6**

### Property 4: Silent Mode State Transition

For any completed AI response, the system should immediately return to Silent_Listening_Mode where it receives audio without generating responses.

**Validates: Requirements 2.5, 15.3**

### Property 5: MFCC Feature Extraction

For any valid audio sample during enrollment or real-time processing, the system should extract MFCC features with at least 13 coefficients per frame.

**Validates: Requirements 3.2, 3.4, 4.1**

### Property 6: Voice Fingerprint Structure

For any completed voice enrollment, the resulting voice fingerprint should contain mean and variance vectors, each with exactly 13 MFCC coefficients.

**Validates: Requirements 3.3, 3.4**

### Property 7: Speaker Classification

For any audio chunk with extracted MFCC features, the system should label it as "[USER]" if cosine similarity to the user voiceprint exceeds 0.7, and "[COUNTERPARTY]" otherwise.

**Validates: Requirements 4.2, 4.3, 4.4**

### Property 8: Audio Chunk Format Consistency

For any audio chunk sent to the Gemini Live API, it should be 100ms duration at 16kHz sample rate, encoded as Int16 PCM in little-endian format.

**Validates: Requirements 4.5, 11.1, 11.2**

### Property 9: Real-Time Processing Speed

For any audio chunk, speaker identification processing should complete before the next chunk arrives (within 100ms).

**Validates: Requirements 4.6**

### Property 10: State Object Structure Invariant

For any negotiation state object, it should contain all required fields: item, seller_price, target_price, max_price, market_data, and transcript.

**Validates: Requirements 5.1**

### Property 11: Price Extraction and Update

For any transcript entry containing a price pattern and labeled as "[COUNTERPARTY]", the system should extract the price and update the seller_price field in the state object.

**Validates: Requirements 5.2**

### Property 12: Complete State in Query

For any ADVISOR_QUERY generated from a button tap, it should include all fields from the current state object.

**Validates: Requirements 5.3, 9.3**

### Property 13: Market Data State Update

For any completed market research function call, the system should update the market_data field in the state object with the returned price range information.

**Validates: Requirements 5.4**

### Property 14: Transcript Time Window

For any negotiation state object, the transcript array should contain only entries with timestamps within the last 90 seconds.

**Validates: Requirements 5.5, 9.2**

### Property 15: State Serialization Round-Trip

For any negotiation state object, serializing to JSON and then deserializing should produce an equivalent state object with all fields preserved.

**Validates: Requirements 5.6**

### Property 16: Function Call Parameters

For any search_market_price function call triggered by the AI, the call should include the item parameter, and optionally the location parameter.

**Validates: Requirements 6.3**

### Property 17: Function Return Value

For any completed search_market_price function execution, it should return a result object containing item, location, price_range, and timestamp fields.

**Validates: Requirements 6.4**

### Property 18: UI Loading State

For any period when the AI is generating a response (between button tap and response completion), the UI should display a loading indicator.

**Validates: Requirements 8.3**

### Property 19: UI State Machine

For any AI response lifecycle (button tap → generating → playing → complete), the UI should transition through states: ready → loading → playing → ready, in that exact order.

**Validates: Requirements 8.3, 8.4, 8.5**

### Property 20: Button Accessibility

For any point during an active negotiation session, the "Ask AI" button should be accessible and responsive (not disabled except during active loading).

**Validates: Requirements 8.6**

### Property 21: Transcript Entry Format

For any transcribed utterance added to the transcript, it should be formatted as an object with speaker (either "USER" or "COUNTERPARTY"), text, and timestamp fields.

**Validates: Requirements 9.1, 9.4, 9.6**

### Property 22: Transcription Error Recovery

For any transcription error that occurs during audio processing, the system should log the error and continue operating without crashing or stopping audio processing.

**Validates: Requirements 9.5**

### Property 23: Audio Format Consistency

For any audio stream throughout a session, the format (16kHz, Int16 PCM, little-endian, mono) should remain consistent from start to finish.

**Validates: Requirements 11.6**

### Property 24: Audio Chunk Timing

For any sequence of audio chunks sent to the backend, the time interval between chunks should be 100ms ± 10ms.

**Validates: Requirements 11.3**

### Property 25: State Initialization

For any user-provided context input (item, target_price, max_price), the state manager should initialize a state object with these values in the correct fields and data types.

**Validates: Requirements 12.2, 12.6**

### Property 26: Price Validation

For any state initialization with target_price and max_price values, the system should validate that target_price ≤ max_price, and prompt for correction if validation fails.

**Validates: Requirements 12.4, 12.5**

### Property 27: Connection Failure Error Display

For any Gemini Live API connection failure, the system should display an error message to the user.

**Validates: Requirements 14.1**

### Property 28: Automatic Reconnection

For any connection failure, the system should attempt automatic reconnection up to 3 times before giving up.

**Validates: Requirements 14.2**

### Property 29: Low Accuracy Warning

For any voice fingerprinting session where accuracy falls below 60%, the system should display a warning to the user suggesting manual labeling.

**Validates: Requirements 14.3**

### Property 30: Graceful Research Failure

For any market research function call that fails, the system should continue operating and provide advice without market data rather than crashing.

**Validates: Requirements 14.4**

### Property 31: Audio Interruption Recovery

For any audio streaming interruption, the system should resume streaming from the interruption point without losing connection.

**Validates: Requirements 14.5**

### Property 32: Error Logging

For any error that occurs in the system, error details should be logged for debugging purposes.

**Validates: Requirements 14.6**

### Property 33: Unlimited Button Taps

For any number of button tap events during a session, the system should handle each one correctly without degradation or failure.

**Validates: Requirements 15.1**

### Property 34: State Continuity

For any sequence of multiple advice requests in a session, the state object should maintain continuity with updates accumulating correctly across all requests.

**Validates: Requirements 15.2, 15.6**

### Property 35: Request Queuing

For any button tap that occurs while an AI response is actively being generated, the system should queue the request and process it after the current response completes.

**Validates: Requirements 15.4**

### Property 36: Queue Processing Order

For any sequence of queued advice requests, the system should process them in FIFO (first-in-first-out) order.

**Validates: Requirements 15.5**

## Error Handling

### Connection Errors

**Gemini Live API Connection Failure:**
- Display user-friendly error message
- Attempt automatic reconnection (up to 3 attempts)
- Exponential backoff: 1s, 2s, 4s between attempts
- If all attempts fail, prompt user to refresh

**WebSocket Connection Failure:**
- Detect disconnection via ping/pong heartbeat
- Attempt automatic reconnection (up to 3 attempts)
- Preserve state during reconnection
- Notify user of connection status

**Audio Streaming Interruption:**
- Buffer audio to handle temporary network issues
- Resume streaming from interruption point
- Log interruption duration and frequency
- If interruptions exceed threshold, suggest network check

### Voice Fingerprinting Errors

**Low Enrollment Quality:**
- Detect if enrollment audio is too short or noisy
- Prompt user to re-record enrollment
- Provide feedback on audio quality

**Low Classification Accuracy:**
- Track speaker identification accuracy over time
- If accuracy falls below 60%, display warning
- Suggest manual speaker labeling as fallback
- Offer re-enrollment option

**MFCC Extraction Failure:**
- Log error details
- Skip speaker labeling for failed chunk
- Label as "UNKNOWN" temporarily
- Continue processing subsequent chunks

### State Management Errors

**Invalid Price Input:**
- Validate target_price ≤ max_price
- Display validation error message
- Prompt user to correct values
- Prevent state initialization until valid

**Transcript Overflow:**
- Continuously trim transcript to 90-second window
- Use timestamp-based filtering
- Ensure no memory leaks from unbounded growth

**State Serialization Failure:**
- Catch JSON serialization errors
- Log problematic state fields
- Use fallback state with minimal fields
- Continue operation with degraded state

### Market Research Errors

**Function Call Timeout:**
- Set 3-second timeout for search_market_price
- If timeout occurs, return empty result
- AI provides advice without market data
- Log timeout for monitoring

**Invalid Search Results:**
- Validate returned price range format
- If invalid, discard and continue
- AI provides advice without market data
- Log validation failure

### Audio Processing Errors

**Invalid Audio Format:**
- Validate chunk size, sample rate, encoding
- Reject malformed chunks
- Log format error details
- Continue processing valid chunks

**Transcription Failure:**
- Catch transcription errors from Gemini API
- Log error details
- Skip transcript update for failed chunk
- Continue processing subsequent audio

### UI Errors

**Button Tap During Invalid State:**
- Disable button during loading state
- Ignore taps if no active session
- Display appropriate error message
- Prevent duplicate requests

**Audio Playback Failure:**
- Catch audio playback errors
- Display error message to user
- Offer retry option
- Log error for debugging

## Testing Strategy

### Dual Testing Approach

The system requires both unit tests and property-based tests for comprehensive coverage:

**Unit Tests:** Verify specific examples, edge cases, error conditions, and integration points between components. Unit tests should focus on concrete scenarios and boundary conditions.

**Property Tests:** Verify universal properties across all inputs using randomized testing. Property tests should run a minimum of 100 iterations per property to ensure comprehensive input coverage.

Together, these approaches provide complementary coverage: unit tests catch concrete bugs in specific scenarios, while property tests verify general correctness across the input space.

### Property-Based Testing Configuration

**Library Selection:**
- Frontend (TypeScript): Use `fast-check` library for property-based testing
- Backend (Python): Use `hypothesis` library for property-based testing

**Test Configuration:**
- Minimum 100 iterations per property test
- Each property test must reference its design document property
- Tag format: `Feature: button-triggered-advice-system, Property {number}: {property_text}`

**Example Property Test (TypeScript):**
```typescript
import fc from 'fast-check';

// Feature: button-triggered-advice-system, Property 7: Speaker Classification
test('speaker classification based on similarity threshold', () => {
  fc.assert(
    fc.property(
      fc.float({ min: 0, max: 1 }), // similarity score
      (similarity) => {
        const label = classifySpeaker(similarity, 0.7);
        if (similarity > 0.7) {
          expect(label).toBe('USER');
        } else {
          expect(label).toBe('COUNTERPARTY');
        }
      }
    ),
    { numRuns: 100 }
  );
});
```

**Example Property Test (Python):**
```python
from hypothesis import given, strategies as st

# Feature: button-triggered-advice-system, Property 15: State Serialization Round-Trip
@given(st.builds(NegotiationState))
def test_state_serialization_roundtrip(state):
    """For any state object, serialize then deserialize should preserve all fields."""
    serialized = json.dumps(state.dict())
    deserialized = NegotiationState(**json.loads(serialized))
    assert deserialized == state
```

### Unit Testing Strategy

**Configuration Tests:**
- Verify VAD is disabled in Gemini config (Requirement 1.1, 10.1)
- Verify transcription is enabled (Requirements 10.2, 10.3)
- Verify function is registered (Requirements 6.1, 10.4)
- Verify response modality is audio (Requirement 10.5)
- Verify generation config (Requirement 10.6, 7.2, 7.3)

**Timing Tests:**
- Connection maintains for 10 minutes (Requirement 1.3)
- AI response within 5 seconds (Requirement 2.4)
- MFCC extraction within 2 seconds (Requirement 3.6)
- Function call within 3 seconds (Requirement 6.5)
- Advice generation within 5 seconds (Requirement 7.4)
- Button feedback within 100ms (Requirement 8.2)
- End-to-end latency under 5 seconds (Requirements 13.1-13.6)
- Audio buffering during network issues (Requirement 11.4)
- Reconnection within 2 seconds (Requirement 11.5)

**UI Flow Tests:**
- Enrollment prompt (Requirement 3.1)
- Enrollment confirmation (Requirement 3.5)
- Ask AI button exists (Requirement 8.1)
- Context prompt after enrollment (Requirement 12.1)
- Readiness confirmation (Requirement 12.3)

**Integration Tests:**
- End-to-end button tap flow
- Voice enrollment to classification pipeline
- State initialization to query generation
- Function calling integration
- Error recovery scenarios

### Test Data Generators

**Audio Sample Generator:**
```typescript
// Generate random audio samples for testing
function generateAudioSample(
  duration: number,
  sampleRate: number = 16000
): Float32Array {
  const numSamples = duration * sampleRate;
  const samples = new Float32Array(numSamples);
  for (let i = 0; i < numSamples; i++) {
    samples[i] = Math.random() * 2 - 1; // Random values between -1 and 1
  }
  return samples;
}
```

**State Object Generator:**
```python
from hypothesis import strategies as st

negotiation_state_strategy = st.builds(
    NegotiationState,
    item=st.text(min_size=1, max_size=100),
    seller_price=st.one_of(st.none(), st.integers(min_value=0, max_value=1000000)),
    target_price=st.integers(min_value=0, max_value=1000000),
    max_price=st.integers(min_value=0, max_value=1000000),
    market_data=st.one_of(st.none(), st.text()),
    transcript=st.lists(
        st.builds(
            TranscriptEntry,
            speaker=st.sampled_from(['USER', 'COUNTERPARTY']),
            text=st.text(min_size=1, max_size=200),
            timestamp=st.integers(min_value=0)
        ),
        max_size=50
    )
)
```

### Coverage Goals

- Unit test coverage: >80% of code paths
- Property test coverage: All 36 correctness properties
- Integration test coverage: All critical user flows
- Error handling coverage: All error scenarios in Error Handling section

### Continuous Testing

- Run unit tests on every commit
- Run property tests nightly (due to longer execution time)
- Run integration tests before deployment
- Monitor test execution time and optimize slow tests
