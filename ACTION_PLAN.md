# Action Plan - Fix Continuous Conversation

## Current Situation

✅ **Fixed**: Audio format corruption (no more 1007 errors)
❌ **Active Bug**: Stream ends after first turn (AI responds once, then stops)
⏳ **Pending**: High latency (20-25 seconds)

## Immediate Next Steps

### Step 1: Run Diagnostic Test (5 minutes)

```bash
cd backend
python test_continuous_receive.py
```

**What to look for**:
- Does the stream continue after Turn 1?
- Does it complete all 3 turns?
- Or does it end after the first `turn_complete`?

**Expected**: Stream should continue for all 3 turns
**If it fails**: Confirms the SDK/API issue

### Step 2: Check SDK Version (2 minutes)

```bash
pip show google-genai
```

**Current version**: Check what you have
**Latest version**: Update if needed

```bash
pip install --upgrade google-genai
```

Then retest with the diagnostic script.

### Step 3: Research SDK Documentation (15 minutes)

Search for:
- Multi-turn conversation examples
- Session lifecycle documentation
- `turn_complete` handling
- Continuous listening mode

Check:
- https://github.com/googleapis/python-genai
- https://ai.google.dev/gemini-api/docs
- GitHub issues for similar problems

### Step 4: Try Configuration Changes (10 minutes)

If SDK update doesn't help, try different configurations in `gemini_client.py`:

```python
config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    tools=[types.Tool(google_search=types.GoogleSearch())],
    system_instruction=build_system_prompt(context),
    enable_affective_dialog=settings.ENABLE_AFFECTIVE_DIALOG,
    proactivity=types.ProactivityConfig(proactive_audio=settings.ENABLE_PROACTIVE_AUDIO),
    input_audio_transcription=types.AudioTranscriptionConfig(),
    output_audio_transcription=types.AudioTranscriptionConfig(),
    
    # Try adding these:
    # speech_config=types.SpeechConfig(...),
    # turn_detection_config=types.TurnDetectionConfig(...),
)
```

### Step 5: Report Issue or Implement Workaround (30 minutes)

**If SDK issue confirmed**:
1. Create minimal reproduction case
2. Report to Google's GitHub
3. Implement temporary workaround

**Workaround options**:
- Recreate session after each turn (not ideal)
- Use session handoff mechanism more aggressively
- Switch to text-based API temporarily

## Testing Checklist

After any fix:

- [ ] Run `python test_continuous_receive.py` - should complete 3 turns
- [ ] Start frontend and backend
- [ ] Have a 3+ turn conversation
- [ ] Verify no "stream ended" warnings
- [ ] Verify no 1011 keepalive errors
- [ ] Check audio quality remains good
- [ ] Test interruption handling
- [ ] Test 5+ minute conversation

## Success Criteria

✅ AI responds to multiple questions in sequence
✅ No page refresh needed between questions
✅ No "stream ended" warnings in logs
✅ No 1011 keepalive timeout errors
✅ Conversation continues for 10+ minutes

## If All Else Fails

**Nuclear option**: Recreate session after each turn

```python
# After turn_complete, close and reopen session
if hasattr(sc, 'turn_complete') and sc.turn_complete:
    logger.info(f"Turn complete, recreating session [{session_id}]")
    # Close current session
    # Open new session with same context
    # Restart receive loop
```

This is not ideal but would work as a temporary solution.

## Timeline Estimate

- **Best case**: SDK update fixes it (30 minutes)
- **Medium case**: Configuration change fixes it (2 hours)
- **Worst case**: Need workaround or SDK bug fix (1 day)

## Priority

**HIGH** - This is the blocker for continuous conversation functionality.

The audio format fix was necessary but this is the core issue preventing the feature from working.
