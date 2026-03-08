# Testing Guide - Latency & UX Improvements

## Quick Start

### 1. Restart the Application

**Backend:**
```bash
cd backend
# Stop the current server (Ctrl+C)
# Restart
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Frontend:**
```bash
cd frontend
# Stop the current dev server (Ctrl+C)
# Restart
npm run dev
```

### 2. Open the Application
Navigate to: `http://localhost:3000`

### 3. Start a Session
1. Accept privacy consent
2. Click "Start Session"
3. Allow microphone access

## What to Test

### Test 1: Visual Feedback Appears
**Expected:**
- Blue "🎤 Listening..." indicator appears at top of screen
- Indicator has pulsing animation
- Text reads "AI is listening to you speak"

**Pass Criteria:** ✅ Indicator is visible and animated

---

### Test 2: Speaking Detection
**Action:** Speak into microphone for 3-5 seconds

**Expected:**
- Indicator stays blue "🎤 Listening..."
- No state change while speaking

**Pass Criteria:** ✅ Indicator remains in listening state

---

### Test 3: Silence Detection → Thinking State
**Action:** Stop speaking and wait

**Expected:**
- After ~1.5 seconds of silence
- Indicator changes to purple "🧠 Processing..."
- Text reads "AI is analyzing and preparing response"

**Pass Criteria:** ✅ State changes to thinking after silence

---

### Test 4: AI Response → Speaking State
**Action:** Wait for AI to respond (10-20 seconds)

**Expected:**
- Indicator changes to green "🔊 Speaking..."
- Text reads "AI is responding"
- Audio plays smoothly without choppiness
- All words are audible (no missing pieces)

**Pass Criteria:** 
- ✅ State changes to speaking
- ✅ Audio is smooth and complete

---

### Test 5: Return to Listening
**Action:** Wait for AI to finish speaking

**Expected:**
- Indicator returns to blue "🎤 Listening..."
- Ready for next user input

**Pass Criteria:** ✅ State returns to listening

---

### Test 6: Multi-Turn Conversation
**Action:** Have a 3-turn conversation:
1. "Hello, can you hear me?"
2. Wait for response
3. "I want to negotiate a price for a laptop"
4. Wait for response
5. "What's your best offer?"
6. Wait for response

**Expected:**
- Each turn follows the cycle: Listening → Thinking → Speaking → Listening
- Audio quality remains good throughout
- No state indicator glitches
- Smooth transitions

**Pass Criteria:** 
- ✅ All 3 turns complete successfully
- ✅ State transitions are correct
- ✅ Audio quality is consistent

---

## Detailed Test Scenarios

### Scenario A: Quick Back-and-Forth
**Purpose:** Test rapid state transitions

**Steps:**
1. Speak for 2 seconds
2. Stop
3. Wait for "Thinking" state
4. Wait for AI response
5. Immediately speak again when AI finishes
6. Repeat 3 times

**Expected:** Smooth state transitions, no lag or freezing

---

### Scenario B: Long User Input
**Purpose:** Test sustained listening state

**Steps:**
1. Speak continuously for 15-20 seconds
2. Describe a complex negotiation scenario

**Expected:** 
- Indicator stays "Listening" throughout
- No premature "Thinking" state
- Audio captured completely

---

### Scenario C: Background Noise
**Purpose:** Test silence detection robustness

**Steps:**
1. Speak with background noise (music, typing, etc.)
2. Stop speaking but keep background noise

**Expected:**
- Should transition to "Thinking" after silence
- Background noise shouldn't prevent state change
- May need to adjust RMS threshold if too sensitive

---

### Scenario D: Interruption
**Purpose:** Test state recovery

**Steps:**
1. Start speaking
2. Stop mid-sentence
3. Wait for "Thinking" state
4. Start speaking again before AI responds

**Expected:**
- State should return to "Listening"
- System should handle interruption gracefully

---

## Troubleshooting

### Issue: Indicator doesn't appear
**Check:**
- Browser console for errors
- Network tab for WebSocket connection
- Microphone permissions granted

**Fix:**
- Refresh page
- Check browser console logs
- Verify backend is running

---

### Issue: State stuck on "Listening"
**Possible Causes:**
- Silence detection threshold too high
- Background noise too loud
- RMS calculation not working

**Fix:**
```typescript
// Lower the RMS threshold in audio-worklet-manager.ts
return rms > 300; // Instead of 500
```

---

### Issue: State changes too quickly to "Thinking"
**Possible Causes:**
- Silence threshold too short
- User speaks with pauses

**Fix:**
```typescript
// Increase silence threshold in audio-worklet-manager.ts
private readonly SILENCE_THRESHOLD_MS = 2500; // Instead of 1500
```

---

### Issue: Audio still choppy
**Check:**
- Browser console for audio errors
- Network connection stability
- Backend logs for audio chunk sizes

**Fix:**
- Verify playback processor changes applied
- Check `_minBufferSamples` is 1200
- Check `_maxSilenceFrames` is 240

---

### Issue: "Thinking" state lasts too long
**This is normal!**
- Gemini's VAD takes 10-20 seconds
- Cannot be reduced (server-side)
- The indicator is working correctly by showing this delay

---

## Success Criteria

All tests pass if:

✅ Visual indicator appears and is clearly visible
✅ State transitions happen at appropriate times
✅ "Thinking" state explains the 10-20 second delay
✅ Audio playback is smooth without choppiness
✅ No missing words in AI responses
✅ Multi-turn conversations work correctly
✅ No console errors
✅ Professional, polished user experience

## Performance Checks

### Browser Console
Should see:
- WebSocket connection established
- No audio worklet errors
- State transition logs (if debugging enabled)

### Network Tab
Should see:
- WebSocket connection active
- Binary frames (audio) flowing both directions
- JSON frames (state updates) from server

### Backend Logs
Should see:
- Session started
- Turn completions
- No audio format errors
- State signals sent

## Known Behaviors

### Normal:
- 10-20 second delay in "Thinking" state (Gemini VAD)
- Slight delay before "Thinking" appears (1.5s silence detection)
- Occasional state flicker if user speaks in short bursts

### Not Normal:
- No indicator appearing at all
- State stuck in one position
- Choppy audio playback
- Missing words in responses
- Console errors

## Reporting Issues

If you find issues, provide:
1. Which test scenario failed
2. Browser console logs
3. Backend logs
4. Description of unexpected behavior
5. Steps to reproduce

## Next Steps After Testing

Once all tests pass:
1. Document any threshold adjustments made
2. Note any edge cases discovered
3. Consider additional UX enhancements
4. Deploy to production environment
