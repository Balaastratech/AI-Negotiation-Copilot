# Bugfix Requirements Document

## Introduction

The Gemini Live API integration currently fails to maintain continuous bidirectional conversation during negotiation sessions. After the AI provides its first response, the `receive_responses` loop exits when the stream ends, causing the session to stop listening and responding. This breaks the core functionality of a live negotiation copilot that should continuously monitor the conversation and provide real-time guidance with interruption handling.

This bug affects the multimodal real-time negotiation assistant's ability to act as a persistent copilot throughout the entire negotiation session.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a negotiation session starts and the user speaks THEN the system processes the first audio input and provides one AI response

1.2 WHEN the AI finishes its first response THEN the `receive_responses` async loop exits because the Gemini Live stream ends

1.3 WHEN the receive loop exits THEN the system stops listening to subsequent user audio input and stops providing AI responses

1.4 WHEN the user continues speaking after the first AI response THEN the system does not process or respond to the audio

1.5 WHEN the user attempts to interrupt the AI mid-response THEN the interruption is not handled because the bidirectional streaming is not properly maintained

1.6 WHEN the session handoff mechanism triggers after 540 seconds THEN it attempts to create a new session but the receive loop still exits prematurely

### Expected Behavior (Correct)

2.1 WHEN a negotiation session starts and the user speaks THEN the system SHALL continuously process all audio input throughout the entire session

2.2 WHEN the AI finishes a response THEN the system SHALL continue listening for the next user input without exiting the receive loop

2.3 WHEN the receive loop processes responses THEN the system SHALL maintain the bidirectional stream connection until the user explicitly ends the negotiation

2.4 WHEN the user continues speaking after an AI response THEN the system SHALL process the audio and provide appropriate AI guidance

2.5 WHEN the user interrupts the AI mid-response THEN the system SHALL handle the interruption gracefully by clearing the audio queue and processing the new user input

2.6 WHEN the session handoff mechanism triggers THEN the system SHALL seamlessly transition to a new Gemini Live session while maintaining continuous conversation flow

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the user explicitly sends an END_NEGOTIATION message THEN the system SHALL CONTINUE TO properly close the Gemini Live session and transition to ENDING state

3.2 WHEN audio chunks are sent to the Gemini Live API THEN the system SHALL CONTINUE TO encode them as 16kHz PCM format

3.3 WHEN the AI generates audio responses THEN the system SHALL CONTINUE TO send them as binary frames through the WebSocket to the frontend

3.4 WHEN transcription data is received from Gemini THEN the system SHALL CONTINUE TO send TRANSCRIPT_UPDATE messages to the frontend

3.5 WHEN strategy updates are detected in AI text responses THEN the system SHALL CONTINUE TO parse and send STRATEGY_UPDATE messages

3.6 WHEN vision frames are sent during an active session THEN the system SHALL CONTINUE TO process them through the Gemini Live API

3.7 WHEN the WebSocket connection is lost THEN the system SHALL CONTINUE TO handle cleanup and state transitions appropriately

3.8 WHEN privacy consent is granted THEN the system SHALL CONTINUE TO transition from IDLE to CONSENTED state correctly
