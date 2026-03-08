"""
Pytest configuration for test suite.

Sets up environment variables before tests run.
"""

import os
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Set up test environment variables before any imports
os.environ["GEMINI_API_KEY"] = "test-api-key"
os.environ["GEMINI_MODEL"] = "gemini-live-2.5-flash-native-audio"
os.environ["GEMINI_MODEL_FALLBACK"] = "gemini-2.0-flash-live-001"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["LOG_LEVEL"] = "INFO"
