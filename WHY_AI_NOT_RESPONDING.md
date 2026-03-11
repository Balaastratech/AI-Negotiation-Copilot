# Why AI Is Not Responding to ADVISOR_QUERY

## The Core Problem

When you click "Ask AI", the system sends an ADVISOR_QUERY text message to the Gemini Live API, but the AI completes the turn WITHOUT generating any audio response (`model_turn=None`).

## Understanding Gemini Live API Configuration

### Input vs Output Modalities

**IMPORTANT CLARIFICATION:**
- `response_modalities` controls what the AI **OUTPUTS** (what it responds with)
- The AI can **ACCEPT** any input type (audio, text, images) regardless of this setting

So `response_modalities=["AUDIO"]` means:
- ✓ AI can receive: audio, text, images
- ✓ AI will respond with: audio only
- ✗ AI will NOT respond with: text

### Why Only One Modality?

The API enforces: **"At most one response modality can be specified"**

This is a design choice by Google - you must pick either:
- `["AUDIO"]` - AI responds with voice
- `["TEXT"]` - AI responds with text

You cannot have both simultaneously.

## Why Isn't the AI Responding?

The AI is receiving your text ADVISOR_QUERY (we know because the turn completes), but it's choosing NOT to generate a response. Possible reasons:

### 1. Silent Listening Mode (Most Likely)
The Gemini Live API is designed for natural conversations. By default, it might be in "listening mode" where it:
- Listens to audio input
- Waits for natural conversation cues
- Doesn't respond to every input

When you send a text query, the AI might interpret it as "context" rather than a "question requiring response".

### 2. System Prompt Not Directive Enough
The AI needs VERY explicit instructions to respond to text inputs when in audio mode. Generic prompts like "provide advice when asked" aren't strong enough.

### 3. Temperature/Sampling Settings
Lower temperature = more conservative = less likely to respond
Higher temperature = more creative = more likely to respond

### 4. Turn Completion Signal
The AI might need a specific signal that it's "its turn to speak". Just sending text might not be enough.

## Solutions Implemented

### 1. Simplified System Prompt
Changed from verbose instructions to direct, simple commands:
```python
"When you see '🔔 ADVISOR_QUERY' - RESPOND IMMEDIATELY with audio advice"
"ALWAYS respond when asked - never stay silent"
```

### 2. Simplified ADVISOR_QUERY
Reduced from verbose formatted query to simple, direct question:
```
🔔 ADVISOR_QUERY: USER NEEDS ADVICE NOW 🔔
Item: iPhone 14 Pro Max
What should the user say or do right now?
```

### 3. Increased Temperature
Changed from 0.9 to 1.0 (maximum) to make AI more responsive and less conservative.

### 4. Added Sampling Parameters
```python
top_p=0.95  # Nucleus sampling
top_k=40    # Consider more token options
```

### 5. Multiple Send Methods
Try 3 different ways to send the query:
1. `send(query, end_of_turn=True)`
2. `send_realtime_input(text=query, end_of_turn=True)`
3. `send_client_content()` (fallback)

## Alternative Solutions (If Still Not Working)

### Option A: Audio Trigger
Instead of sending text, generate a brief audio tone or beep to "wake up" the AI before sending the query.

### Option B: Function Calling
Use Gemini's function calling feature to explicitly request advice:
```python
function_call = {
    "name": "provide_advice",
    "parameters": {"context": state}
}
```

### Option C: Dual Session Architecture
- Session 1: Silent listening (current behavior)
- Session 2: Active advisor (responds to queries)

Switch between sessions based on user action.

### Option D: Remove response_modalities Restriction
Try removing the `response_modalities` parameter entirely and let the API decide:
```python
config = types.LiveConnectConfig(
    # No response_modalities specified
    system_instruction=build_system_prompt(context),
    ...
)
```

## Testing the Current Fix

1. Restart backend server
2. Start a negotiation session
3. Speak: "I want to buy iPhone 14 Pro Max"
4. Click "Ask AI"
5. Check logs for:
   - `ADVISOR_QUERY sent via send() method`
   - `Response #X: model_turn=True` ← THIS is what we need
   - Audio data being sent to frontend

## Next Steps If Still Failing

1. **Test without response_modalities**: Remove the restriction entirely
2. **Try TEXT mode**: Change to `response_modalities=["TEXT"]` to see if AI responds with text
3. **Check API version**: Ensure using latest SDK version
4. **Contact Google Support**: This might be a known limitation or bug

## Key Insight

The Gemini Live API is optimized for natural voice conversations, not programmatic text-based triggers. We're trying to use it in a hybrid way (listen to audio, respond to text commands), which might not be the intended use case.

The most reliable solution might be to fully embrace the audio paradigm: have the user SPEAK "I need advice" instead of clicking a button.
