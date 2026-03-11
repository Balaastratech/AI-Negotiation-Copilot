import asyncio
from google import genai
from google.genai import types
from app.config import settings

async def test():
    client = genai.Client(api_key=settings.GEMINI_API_KEY, http_options=types.HttpOptions(api_version='v1alpha'))
    config = types.LiveConnectConfig()
    try:
        async with client.aio.live.connect(model=settings.GEMINI_MODEL, config=config) as session:
            print('Connected to', settings.GEMINI_MODEL)
    except Exception as e:
        print('Error on primary:', str(e))
        
    try:
        async with client.aio.live.connect(model=settings.GEMINI_MODEL_FALLBACK, config=config) as session:
            print('Connected to', settings.GEMINI_MODEL_FALLBACK)
    except Exception as e:
        print('Error on fallback:', str(e))

asyncio.run(test())
