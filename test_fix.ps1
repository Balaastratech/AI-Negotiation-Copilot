# Quick test script to verify the fix
Write-Host "=== AI Negotiation Copilot - Fix Verification ===" -ForegroundColor Cyan
Write-Host ""

# Check if backend directory exists
if (-not (Test-Path "backend")) {
    Write-Host "ERROR: backend directory not found!" -ForegroundColor Red
    Write-Host "Please run this script from the project root directory." -ForegroundColor Yellow
    exit 1
}

# Check .env file
Write-Host "1. Checking .env configuration..." -ForegroundColor Yellow
if (Test-Path "backend/.env") {
    $envContent = Get-Content "backend/.env" -Raw
    
    if ($envContent -match "GEMINI_API_KEY=(.+)") {
        $apiKey = $matches[1].Trim()
        if ($apiKey.Length -gt 20) {
            Write-Host "   ✓ API Key found (${apiKey.Substring(0,20)}...)" -ForegroundColor Green
        } else {
            Write-Host "   ✗ API Key seems too short" -ForegroundColor Red
        }
    } else {
        Write-Host "   ✗ GEMINI_API_KEY not found in .env" -ForegroundColor Red
    }
    
    if ($envContent -match "GEMINI_MODEL=(.+)") {
        $model = $matches[1].Trim()
        Write-Host "   ✓ Model: $model" -ForegroundColor Green
        
        if ($model -eq "gemini-live-2.5-flash-native-audio") {
            Write-Host "   ⚠ Warning: This model name might not be available" -ForegroundColor Yellow
            Write-Host "   Recommended: gemini-2.0-flash-exp" -ForegroundColor Yellow
        }
    }
    
    if ($envContent -match "LOG_LEVEL=(.+)") {
        $logLevel = $matches[1].Trim()
        Write-Host "   ✓ Log Level: $logLevel" -ForegroundColor Green
    } else {
        Write-Host "   ℹ Log Level not set (will use INFO)" -ForegroundColor Cyan
    }
} else {
    Write-Host "   ✗ .env file not found!" -ForegroundColor Red
    Write-Host "   Please create backend/.env from backend/.env.example" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "2. Checking Python environment..." -ForegroundColor Yellow

# Check if venv exists
if (Test-Path "backend/venv") {
    Write-Host "   ✓ Virtual environment found" -ForegroundColor Green
} else {
    Write-Host "   ✗ Virtual environment not found" -ForegroundColor Red
    Write-Host "   Run: cd backend; python -m venv venv" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "3. Testing Gemini Live API connection..." -ForegroundColor Yellow
Write-Host "   (This may take a few seconds)" -ForegroundColor Cyan

Push-Location backend
& .\venv\Scripts\python.exe test_live_connection.py
$testResult = $LASTEXITCODE
Pop-Location

Write-Host ""
if ($testResult -eq 0) {
    Write-Host "=== VERIFICATION COMPLETE ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Start backend:  cd backend; .\venv\Scripts\activate; uvicorn app.main:app --reload" -ForegroundColor White
    Write-Host "2. Start frontend: cd frontend; npm run dev" -ForegroundColor White
    Write-Host "3. Open http://localhost:3000 in your browser" -ForegroundColor White
    Write-Host "4. Test by speaking continuously for 30 seconds" -ForegroundColor White
} else {
    Write-Host "=== ISSUES DETECTED ===" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please check:" -ForegroundColor Yellow
    Write-Host "1. Your GEMINI_API_KEY is valid" -ForegroundColor White
    Write-Host "2. Your model name is correct" -ForegroundColor White
    Write-Host "3. You have internet connectivity" -ForegroundColor White
    Write-Host "4. Your API quota hasn't been exceeded" -ForegroundColor White
    Write-Host ""
    Write-Host "See QUICK_FIX.md for detailed troubleshooting steps" -ForegroundColor Cyan
}
