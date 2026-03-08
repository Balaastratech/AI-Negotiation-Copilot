import asyncio
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

async def test_connect(model_name):
    api_key = os.getenv("GEMINI_API_KEY")
    print(f"\nTesting model: {model_name}")
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(api_version='v1alpha')
    )
    
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
    )
    
    try:
        # 10 second timeout for the connection
        async with asyncio.timeout(10):
            async with client.aio.live.connect(model=model_name, config=config) as session:
                print(f"SUCCESS: Connected to {model_name}")
                return True
    except asyncio.TimeoutError:
        print(f"TIMEOUT: {model_name} took too long to connect")
        return False
    except Exception as e:
        print(f"FAILED: {model_name} -> {e}")
        return False

async def main():
    models = [
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash-live",
        "gemini-2.0-flash-live-001",
        "gemini-2.5-flash-native-audio-preview-12-2025",
        "gemini-live-2.5-flash-native-audio"
    ]
    
    for m in models:
        await test_connect(m)

if __name__ == "__main__":
    asyncio.run(main())
