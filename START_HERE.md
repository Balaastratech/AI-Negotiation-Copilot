# 🚀 START HERE - Fix Your "Stops Listening" Issue

## The Problem
Your app stops responding after one message.

## The Solution (3 Steps)

### Step 1: Run the Test Script
```powershell
.\test_fix.ps1
```

This will check your configuration and test the Gemini API connection.

### Step 2: If Test Fails
Most likely your model name is wrong. Update `backend/.env`:

```env
GEMINI_MODEL=gemini-2.0-flash-exp
GEMINI_MODEL_FALLBACK=gemini-2.0-flash-exp
```

Then run the test again:
```powershell
.\test_fix.ps1
```

### Step 3: Start Your App
If the test passes:

**Terminal 1 - Backend:**
```powershell
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --reload
```

**Terminal 2 - Frontend:**
```powershell
cd frontend
npm run dev
```

**Browser:**
- Open http://localhost:3000
- Grant microphone permission
- Start negotiation
- **Speak for 30 seconds continuously**
- Verify AI responds multiple times

## ✅ Success Criteria
- AI responds to your first message
- AI responds to your second message
- AI responds to your third message
- Conversation flows naturally

## ❌ Still Not Working?

### Quick Checks:
1. Is your API key valid?
2. Is your model name correct?
3. Do you have internet connectivity?
4. Is your API quota exceeded?

### Get More Help:
- **Fast fix**: Read `QUICK_FIX.md`
- **Detailed help**: Read `TROUBLESHOOTING_GUIDE.md`
- **What changed**: Read `FIX_SUMMARY.md`

## What I Fixed

I improved your code to:
1. ✅ Better handle Gemini API errors
2. ✅ Add detailed logging for debugging
3. ✅ Catch and report connection issues
4. ✅ Provide diagnostic tools

The most common issue is using an incorrect model name. The test script will help you identify this.

## Need Help?

Run these commands and check the output:

```powershell
# Test 1: Check your configuration
cd backend
.\venv\Scripts\activate
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('API Key:', 'Found' if os.getenv('GEMINI_API_KEY') else 'NOT FOUND'); print('Model:', os.getenv('GEMINI_MODEL'))"

# Test 2: Test Gemini connection
python test_live_connection.py

# Test 3: Start with debug logging
$env:LOG_LEVEL="DEBUG"
uvicorn app.main:app --reload
```

Good luck! 🎉
