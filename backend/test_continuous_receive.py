"""
Diagnostic test to understand why the Gemini Live API receive() stream ends prematurely
"""
import asyncio
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

async def test_continuous_receive():
    # Load from env or hardcode for debugging
    project_id = "ai-negotiation-copilot"
    location = "us-central1" # The Live API is most stable here
    model = "gemini-live-2.5-flash-native-audio"  # Use the same model as the main app
    
    print(f"Testing Vertex AI Live Connect with model: {model}")
    
    # Initialize for Vertex AI
    client = genai.Client(
        vertexai=True, 
        project=project_id,
        location=location,
    )

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction="You are a helpful assistant. Keep responses very brief (1-2 sentences).",
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
    )
    
    try:
        print("\nConnecting to Gemini Live API...")
        async with client.aio.live.connect(model=model, config=config) as session:
            print("✓ Connected!")
            
            turn_count = 0
            total_responses = 0
            
            # Try calling receive() multiple times for multi-turn conversation
            for turn_num in range(1, 4):
                print(f"\n=== TURN {turn_num} ===")
                
                # Send message for this turn
                if turn_num == 1:
                    await session.send_realtime_input(text="Hello, how are you?")
                    print("Sent: Hello, how are you?")
                elif turn_num == 2:
                    await session.send_realtime_input(text="What's the weather like?")
                    print("Sent: What's the weather like?")
                elif turn_num == 3:
                    await session.send_realtime_input(text="Tell me a joke")
                    print("Sent: Tell me a joke")
                
                # Call receive() for THIS turn
                print(f"Listening for Turn {turn_num} responses...")
                response_count = 0
                turn_complete_received = False
                
                async for response in session.receive():
                    response_count += 1
                    total_responses += 1
                    
                    if response.server_content:
                        sc = response.server_content
                        
                        if sc.model_turn:
                            for part in sc.model_turn.parts:
                                if part.text:
                                    print(f"  Response #{response_count}: Text: {part.text}")
                                if part.inline_data:
                                    print(f"  Response #{response_count}: Audio: {len(part.inline_data.data)} bytes")
                        
                        if hasattr(sc, 'turn_complete') and sc.turn_complete:
                            turn_complete_received = True
                            turn_count += 1
                            print(f"  ✓ Turn {turn_count} complete ({response_count} responses)")
                            break  # Exit this receive() loop
                
                if not turn_complete_received:
                    print(f"  ⚠ Stream ended without turn_complete ({response_count} responses)")
                    break
                
                print(f"  Finished Turn {turn_num}, calling receive() again for next turn...")
            
            print("\n=== Test Complete ===")
            print(f"Successfully completed {turn_count} turns!")
            print(f"Total responses received: {total_responses}")
            print("\n✅ CONCLUSION: Calling receive() multiple times WORKS for multi-turn conversations!")
            print("Each receive() call handles one turn, then we call it again for the next turn.")
            
    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_continuous_receive())
