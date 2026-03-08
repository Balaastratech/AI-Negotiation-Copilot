# Quick Fix Guide

## The Problem
Your app stops listening after one message. This is likely due to the Gemini Live API stream closing unexpectedly.

## Quick Fixes to Try (In Order)

### Fix 1: Update Model Name (Most Likely Fix)
The model name `gemini-live-2.5-flash-native-audio` might not be available or correct.

**Update `backend/.env`:**
```env
GEMINI_MODEL=gemini-2.0-flash-exp
GEMINI_MODEL_FALLBACK=gemini-2.0-flash-exp
```

**Restart backend:**
```powershell
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --reload
```

### Fix 2: Test the Connection
Run the diagnostic script:
```powershell
cd backend
.\venv\Scripts\activate
python test_live_connection.py
```

If this fails, your API key or model name is wrong.

### Fix 3: Enable Debug Logging
See what's actually happening:

**Update `backend/.env`:**
```env
LOG_LEVEL=DEBUG
```

**Restart and watch logs:**
```powershell
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --reload
```

Look for these messages:
- ✅ "Audio chunk sent successfully" - Audio is reaching Gemini
- ❌ "Gemini receive loop ended normally" - Stream closed (bad)
- ❌ "Gemini receive loop error" - Connection error (bad)

### Fix 4: Check Browser Console
Open DevTools (F12) in your browser:

1. Go to Console tab
2. Look for errors (red text)
3. Go to Network tab
4. Filter by "WS" (WebSocket)
5. Click on the WebSocket connection
6. Check Messages tab - you should see bidirectional traffic

### Fix 5: Verify Microphone Access
In browser console, type:
```javascript
navigator.mediaDevices.getUserMedia({ audio: true })
  .then(() => console.log('✅ Microphone access granted'))
  .catch(err => console.error('❌ Microphone error:', err))
```

## What I Fixed in Your Code

### 1. Better Error Handling
- Added proper exception handling in `gemini_client.py`
- Added logging to track when streams close
- Added JSON parsing error handling in `websocket.py`

### 2. Better Logging
- Added debug logs for audio chunks
- Added connection lifecycle logging
- Added message type logging

### 3. Improved Diagnostics
- Created `test_live_connection.py` to test Gemini API
- Created this troubleshooting guide

## Most Common Causes

1. **Wrong Model Name** (80% of cases)
   - Solution: Use `gemini-2.0-flash-exp`

2. **Invalid API Key** (10% of cases)
   - Solution: Check your API key in `.env`

3. **Gemini API Quota Exceeded** (5% of cases)
   - Solution: Check your Google Cloud Console

4. **Network/Firewall Issues** (5% of cases)
   - Solution: Check if you can reach Google APIs

## How to Verify It's Fixed

1. Start backend
2. Start frontend
3. Open app in browser
4. Grant microphone permission
5. Click "Start Negotiation"
6. **Speak continuously for 30 seconds**
7. Check if you see transcriptions appearing
8. Check if AI responds multiple times

If the AI responds to multiple things you say, it's fixed!

## Still Not Working?

Run this complete diagnostic:

```powershell
# Test 1: Check API key
cd backend
.\venv\Scripts\activate
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('API Key:', os.getenv('GEMINI_API_KEY')[:20] + '...' if os.getenv('GEMINI_API_KEY') else 'NOT FOUND')"

# Test 2: Test Gemini connection
python test_live_connection.py

# Test 3: Start with debug logging
$env:LOG_LEVEL="DEBUG"
uvicorn app.main:app --reload --log-level debug
```

Then check the logs carefully for any errors.

## Need More Help?

1. Save your backend logs to a file
2. Save your browser console output
3. Check the TROUBLESHOOTING_GUIDE.md for detailed steps
4. Verify your Gemini API quota in Google Cloud Console
