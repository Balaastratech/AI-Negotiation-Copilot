import asyncio
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_vertex_live_connect():
    project = os.getenv("GOOGLE_CLOUD_PROJECT", "ai-negotiation-copilot")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "False").lower() == "true"
    model_id = os.getenv("GEMINI_MODEL", "gemini-live-2.5-flash-native-audio")
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if creds_path:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
    if project:
        os.environ["GOOGLE_CLOUD_PROJECT"] = project

    print(f"\n--- Testing Vertex AI Live Connect ---")
    print(f"Project: {project}")
    print(f"Location: {location}")
    print(f"Use Vertex AI: {use_vertex}")
    print(f"Model: {model_id}")

    if not project and use_vertex:
        print("ERROR: GOOGLE_CLOUD_PROJECT is required for Vertex AI")
        return False

    client = genai.Client(
        vertexai=use_vertex,
        project=project,
        location=location
    )

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        tools=[types.Tool(google_search=types.GoogleSearch())],
        enable_affective_dialog=True,
        proactivity=types.ProactivityConfig(proactive_audio=True)
    )

    try:
        print(f"Attempting to connect to {model_id}...")
        async with asyncio.timeout(15):
            async with client.aio.live.connect(model=model_id, config=config) as session:
                print(f"SUCCESS: Connected to {model_id} on Vertex AI")
                
                # Test sending a simple message
                print("Sending: 'Hello, what is the current weather in Tokyo?'")
                await session.send_client_content(
                    turns=[types.Content(role="user", parts=[types.Part(text="Hello, what is the current weather in Tokyo?")])]
                )
                
                print("Waiting for response...")
                async for message in session.receive():
                    if message.server_content:
                        if message.server_content.model_turn:
                            print("Received model response parts.")
                            return True
    except asyncio.TimeoutError:
        print(f"TIMEOUT: Connection to {model_id} timed out.")
    except Exception as e:
        print(f"FAILED: {e}")
    
    return False

if __name__ == "__main__":
    asyncio.run(test_vertex_live_connect())
