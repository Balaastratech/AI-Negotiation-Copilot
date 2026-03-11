# AI Response Fix - No Response After ADVISOR_QUERY

## Problem Identified

The AI was receiving the ADVISOR_QUERY but not generating any response. The logs showed:
- ✓ User transcript captured correctly
- ✓ ADVISOR_QUERY sent successfully  
- ✗ Turn completed with NO model_turn content (no audio or text generated)

## Root Causes

### 1. Response Modalities Misconfiguration
**Initial Issue**: Tried to use `response_modalities=["AUDIO", "TEXT"]`
- **API Error**: "At most one response modality can be specified in the setup request"
- The Gemini Live API only supports ONE modality at a time
- Cannot have both AUDIO and TEXT simultaneously

**Correct Configuration**: `response_modalities=["AUDIO"]` only
- Audio-only mode is the correct configuration for voice conversations
- Transcription is enabled separately via `input_audio_transcription` and `output_audio_transcription`
- Added `response_mime_type="audio/pcm"` to explicitly request audio output

### 2. Text Input in Audio-Only Mode
**Issue**: Sending text queries to an AUDIO-only session may not trigger responses
- The API expects audio input when configured for audio output
- Text inputs might be ignored or not processed correctly

**Fix**: Multiple fallback approaches in `trigger_advice_response()`
1. Try `send(query, end_of_turn=True)` - standard text send
2. Try `send_realtime_input(text=query, end_of_turn=True)` - realtime text input
3. Fallback to `send_client_content()` - legacy method

### 3. System Prompt Not Optimized for Audio Mode
**Issue**: Prompt didn't emphasize audio-only responses
- Didn't make it clear the AI is in audio-only mode
- Lacked urgency for responding to ADVISOR_QUERY

**Fix**: Rewrote prompt with audio-specific instructions
- Emphasized "AUDIO MODE" and "respond with AUDIO"
- Made it clear user can only hear voice, not see text
- Added explicit instruction to never stay silent on ADVISOR_QUERY

## Changes Made

### File: `backend/app/services/gemini_client.py`

1. **Line ~378**: Fixed response modalities configuration
```python
response_modalities=["AUDIO"],  # AUDIO only - API doesn't support multiple
```

2. **Line ~383**: Added explicit MIME type
```python
response_mime_type="audio/pcm"  # Explicitly request audio output
```

3. **Line ~104-150**: Rewrote `trigger_advice_response()` with multiple fallback methods
- Primary: `send(query, end_of_turn=True)`
- Secondary: `send_realtime_input(text=query, end_of_turn=True)`
- Fallback: `send_client_content()`
- Comprehensive error logging

### File: `backend/app/services/master_prompt.py`

4. **Complete rewrite**: Audio-optimized system prompt
- Clear "AUDIO MODE" designation
- Explicit instructions for ADVISOR_QUERY handling
- Emphasis on immediate audio responses
- Reminder that user can only hear, not see text

## Expected Behavior After Fix

1. User speaks: "I want to buy iPhone 14 Pro Max for 50,000"
2. Transcript captured ✓
3. User clicks "Ask AI" button
4. ADVISOR_QUERY sent to Gemini ✓
5. **AI generates audio response** ✓ (THIS WAS MISSING)
6. Audio streamed back to frontend ✓
7. User hears advice through speakers ✓

## Testing Steps

1. Restart the backend server:
```bash
cd backend
uvicorn app.main:app --reload
```

2. Open the frontend and start a negotiation session

3. Speak into the microphone: "I want to buy iPhone 14 Pro Max for 50,000"

4. Click the "Ask AI" button

5. Watch the logs for:
```
INFO:app.services.gemini_client:ADVISOR_QUERY sent via send() method
INFO:app.services.gemini_client:Response #X: model_turn=True  # <-- Should see this
```

6. Listen for audio response from the AI

## Why This Fix Works

1. **Correct API configuration**: Single AUDIO modality with explicit MIME type
2. **Multiple send methods**: Tries different API methods to ensure delivery
3. **Audio-optimized prompt**: Makes it crystal clear the AI must respond with audio
4. **Proper transcription setup**: Separate from response modalities, enables text visibility of audio

## Troubleshooting

If AI still doesn't respond:

1. **Check logs for send method used**: Look for which method succeeded
2. **Verify turn_complete**: Should see `turn_complete=True` after response
3. **Check for model_turn**: Should have `model_turn=True` with audio data
4. **Test with direct audio input**: Speak after clicking "Ask AI" to see if audio triggers response

## Alternative Approach (If Still Not Working)

If text-based ADVISOR_QUERY continues to fail, we may need to:
1. Generate a brief audio tone/beep to trigger the AI
2. Use function calling to explicitly request advice
3. Switch to a dual-session architecture (one for listening, one for advice)
