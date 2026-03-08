#!/usr/bin/env python3
"""
Quick test script to verify the fix for "stops listening" issue
"""
import os
import sys
from pathlib import Path

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def print_success(text):
    print(f"✓ {text}")

def print_error(text):
    print(f"✗ {text}")

def print_warning(text):
    print(f"⚠ {text}")

def print_info(text):
    print(f"ℹ {text}")

def check_env_file():
    """Check if .env file exists and has required variables"""
    print_header("Checking Configuration")
    
    env_path = Path("backend/.env")
    if not env_path.exists():
        print_error(".env file not found!")
        print_info("Please create backend/.env from backend/.env.example")
        return False
    
    print_success(".env file found")
    
    # Load and check .env
    from dotenv import load_dotenv
    load_dotenv(env_path)
    
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL")
    log_level = os.getenv("LOG_LEVEL", "INFO")
    
    if api_key:
        print_success(f"API Key found ({api_key[:20]}...)")
    else:
        print_error("GEMINI_API_KEY not found in .env")
        return False
    
    if model:
        print_success(f"Model: {model}")
        if model == "gemini-live-2.5-flash-native-audio":
            print_warning("This model name might not be available")
            print_info("Recommended: gemini-2.0-flash-exp")
    else:
        print_warning("GEMINI_MODEL not set (will use default)")
    
    print_success(f"Log Level: {log_level}")
    
    return True

def check_venv():
    """Check if virtual environment exists"""
    print_header("Checking Python Environment")
    
    venv_path = Path("backend/venv")
    if not venv_path.exists():
        print_error("Virtual environment not found")
        print_info("Run: cd backend && python -m venv venv")
        return False
    
    print_success("Virtual environment found")
    return True

def test_gemini_connection():
    """Test Gemini Live API connection"""
    print_header("Testing Gemini Live API Connection")
    print_info("This may take a few seconds...")
    print()
    
    # Change to backend directory
    os.chdir("backend")
    
    # Run the test
    import subprocess
    result = subprocess.run(
        [sys.executable, "test_live_connection.py"],
        capture_output=False
    )
    
    os.chdir("..")
    
    return result.returncode == 0

def main():
    print_header("AI Negotiation Copilot - Fix Verification")
    
    # Check if we're in the right directory
    if not Path("backend").exists():
        print_error("backend directory not found!")
        print_info("Please run this script from the project root directory")
        sys.exit(1)
    
    # Run checks
    if not check_env_file():
        sys.exit(1)
    
    if not check_venv():
        sys.exit(1)
    
    # Test connection
    success = test_gemini_connection()
    
    print_header("Verification Complete")
    
    if success:
        print_success("All checks passed!")
        print()
        print("Next steps:")
        print("1. Start backend:  cd backend && .\\venv\\Scripts\\activate && uvicorn app.main:app --reload")
        print("2. Start frontend: cd frontend && npm run dev")
        print("3. Open http://localhost:3000 in your browser")
        print("4. Test by speaking continuously for 30 seconds")
    else:
        print_error("Issues detected!")
        print()
        print("Please check:")
        print("1. Your GEMINI_API_KEY is valid")
        print("2. Your model name is correct")
        print("3. You have internet connectivity")
        print("4. Your API quota hasn't been exceeded")
        print()
        print("See QUICK_FIX.md for detailed troubleshooting steps")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
