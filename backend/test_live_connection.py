"""
Test script to diagnose Gemini Live API connection issues
"""
import asyncio
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

async def test_gemini_live():
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
    
    print(f"Testing Gemini Live API with model: {model}")
    print(f"API Key present: {bool(api_key)}")
    
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(api_version='v1alpha'),
    )
    
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction="You are a helpful assistant. Respond briefly.",
    )
    
    try:
        print("\nAttempting to connect to Gemini Live API...")
        async with client.aio.live.connect(model=model, config=config) as session:
            print("✓ Connection established successfully!")
            
            # Send a test message
            print("\nSending test audio input...")
            test_text = "Hello, can you hear me?"
            await session.send(test_text, end_of_turn=True)
            print(f"✓ Sent: {test_text}")
            
            # Listen for responses
            print("\nListening for responses...")
            response_count = 0
            timeout = 10  # seconds
            
            try:
                async with asyncio.timeout(timeout):
                    async for response in session.receive():
                        response_count += 1
                        print(f"\n--- Response {response_count} ---")
                        
                        if response.server_content:
                            sc = response.server_content
                            
                            if sc.model_turn:
                                for part in sc.model_turn.parts:
                                    if part.text:
                                        print(f"Text: {part.text}")
                                    if part.inline_data:
                                        print(f"Audio data: {len(part.inline_data.data)} bytes")
                            
                            if sc.turn_complete:
                                print("✓ Turn complete")
                                break
                        
                        if response_count >= 5:
                            print("Received 5 responses, stopping test")
                            break
                            
            except asyncio.TimeoutError:
                print(f"\n⚠ Timeout after {timeout} seconds")
                if response_count == 0:
                    print("ERROR: No responses received from Gemini!")
                else:
                    print(f"Received {response_count} responses before timeout")
            
            print(f"\n✓ Test completed. Total responses: {response_count}")
            
    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_gemini_live())
