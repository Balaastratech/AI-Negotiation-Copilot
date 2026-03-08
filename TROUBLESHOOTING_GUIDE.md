# Troubleshooting Guide: "Stops Listening After One Message"

## Problem Description
The AI Negotiation Copilot stops responding after the first message, appearing to "stop listening" to audio input.

## Root Causes Identified

### 1. Gemini Live API Session Issues
- The `receive_responses` loop exits when the Gemini API stream ends
- No automatic reconnection when the stream closes
- Model name might be incorrect or unsupported

### 2. WebSocket Connection Issues
- Missing error handling for JSON parsing
- No logging for message flow debugging
- Connection state not properly tracked

### 3. Audio Streaming Issues
- Audio chunks might not be reaching Gemini
- No confirmation that audio is being sent successfully

## Fixes Applied

### Backend Fixes

#### 1. Enhanced Error Handling (`gemini_client.py`)
- Added proper exception handling for `asyncio.CancelledError`
- Added logging when receive loop ends normally
- Added debug logging for audio chunk sends
- Better error messages sent to frontend

#### 2. Improved WebSocket Endpoint (`websocket.py`)
- Added JSON parsing error handling
- Added debug logging for message types
- Better connection lifecycle logging
- Improved cleanup in finally block

### Testing Steps

#### Step 1: Test Gemini Live API Connection
```powershell
cd backend
.\venv\Scripts\activate
python test_live_connection.py
```

This will verify:
- API key is valid
- Model name is correct
- Gemini Live API is responding
- Responses are being received

#### Step 2: Check Backend Logs
Start the backend with verbose logging:
```powershell
cd backend
.\venv\Scripts\activate
$env:LOG_LEVEL="DEBUG"
uvicorn app.main:app --reload --log-level debug
```

Look for:
- "WebSocket connection established"
- "Received message type: START_NEGOTIATION"
- "Audio chunk sent successfully"
- "Gemini receive loop" messages

#### Step 3: Check Frontend Console
Open browser DevTools (F12) and check Console for:
- WebSocket connection status
- Messages being sent/received
- Any JavaScript errors

#### Step 4: Verify Audio Capture
In browser console, check if audio is being captured:
```javascript
// Should see audio chunks being sent
console.log('Audio worklet active:', audioManagerRef.current)
```

## Common Issues & Solutions

### Issue 1: Wrong Model Name
**Symptom**: Connection fails immediately or no responses

**Solution**: Update `.env` file with correct model:
```env
GEMINI_MODEL=gemini-2.0-flash-exp
GEMINI_MODEL_FALLBACK=gemini-2.0-flash-exp
```

### Issue 2: API Key Invalid
**Symptom**: 401 or 403 errors in logs

**Solution**: Verify API key in `.env`:
```powershell
$env:GEMINI_API_KEY="your-key-here"
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Key:', os.getenv('GEMINI_API_KEY')[:20] + '...')"
```

### Issue 3: Audio Not Reaching Backend
**Symptom**: No "Audio chunk sent" logs

**Solution**: Check browser permissions:
1. Ensure microphone permission granted
2. Check if audio worklet is initialized
3. Verify WebSocket is in OPEN state

### Issue 4: Gemini Stream Closes Early
**Symptom**: "Gemini receive loop ended normally" in logs

**Solution**: This might be expected behavior. The session handoff mechanism should create a new session after 9 minutes. Check if handoff is working:
- Look for "Session handoff triggered" logs
- Verify new session is created

### Issue 5: WebSocket Disconnects
**Symptom**: "Client disconnected" in logs

**Solution**: 
1. Check network connectivity
2. Verify CORS settings in backend
3. Check if frontend is properly handling disconnections

## Debugging Checklist

- [ ] Backend server is running
- [ ] Frontend dev server is running
- [ ] Browser console shows no errors
- [ ] WebSocket connection established (check Network tab)
- [ ] Microphone permission granted
- [ ] Audio chunks being sent (check Network tab, WS frames)
- [ ] Backend logs show "Audio chunk sent successfully"
- [ ] Backend logs show Gemini responses
- [ ] No "Gemini receive loop error" in logs

## Additional Monitoring

### Enable Detailed Logging
Add to `backend/.env`:
```env
LOG_LEVEL=DEBUG
```

### Monitor WebSocket Traffic
In Chrome DevTools:
1. Network tab
2. Filter: WS
3. Click on the WebSocket connection
4. View Messages tab
5. Watch for bidirectional traffic

### Check Gemini API Status
Visit: https://status.cloud.google.com/

## Next Steps If Issue Persists

1. **Run the test script**: `python backend/test_live_connection.py`
2. **Capture logs**: Save backend logs to a file
3. **Check browser console**: Save any errors
4. **Verify model availability**: Some models might be region-restricted
5. **Try fallback model**: Temporarily change to `gemini-2.0-flash-exp`

## Model Names Reference

Valid Gemini Live API models (as of March 2026):
- `gemini-2.0-flash-exp` (recommended)
- `gemini-2.0-flash-live-001`
- `gemini-live-2.5-flash-native-audio` (if available in your region)

## Contact & Support

If the issue persists after trying these steps:
1. Check Gemini API documentation for updates
2. Verify your API quota hasn't been exceeded
3. Test with a simple example from Google's documentation
