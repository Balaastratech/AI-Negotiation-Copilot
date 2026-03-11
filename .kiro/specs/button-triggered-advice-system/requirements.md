# Requirements Document

## Introduction

The Button-Triggered Advice System transforms the AI Negotiation Copilot from an automatic turn-based conversation system into a fast, on-demand advisory system. The current system suffers from 10-20 second latency due to Gemini Live API's automatic Voice Activity Detection (VAD), making it impractical for real-time negotiations. This feature disables VAD and implements manual activity control, allowing the AI to listen silently to the entire negotiation and respond instantly (3-5 seconds) only when the user taps an "Ask AI" button.

The system enables hands-free negotiation where both the user and counterparty can speak naturally without interruption, while the AI maintains full context awareness. When advice is needed, a single button tap triggers an immediate response based on the complete conversation history, market research, and negotiation state.

## Glossary

- **Gemini_Live_API**: Google's real-time multimodal AI API that supports audio, video, and text streaming
- **VAD**: Voice Activity Detection - automatic detection of when speech starts and stops
- **Activity_Control**: Manual mechanism to signal when the AI should start and stop processing user input
- **ADVISOR_QUERY**: A structured text message containing negotiation state and context sent to trigger AI advice
- **Voice_Fingerprint**: MFCC-based audio features extracted from a user's voice for speaker identification
- **MFCC**: Mel-Frequency Cepstral Coefficients - audio features used for voice recognition
- **Speaker_Diarization**: The process of identifying and labeling who is speaking in an audio stream
- **State_Manager**: Client-side component that tracks negotiation context including items, prices, and transcript
- **Function_Calling**: Gemini API feature allowing the AI to autonomously trigger predefined functions
- **Negotiation_Copilot**: The AI system that provides real-time advice during negotiations
- **Counterparty**: The other person in the negotiation (seller, buyer, or other party)
- **Enrollment_Phase**: Initial setup where the user's voice is recorded to create their voice fingerprint
- **Silent_Listening_Mode**: Operating state where the AI receives audio but does not respond
- **Active_Response_Mode**: Operating state where the AI generates and delivers advice
- **Research_Function**: Function callable by AI to search for any information it determines is needed for negotiation advice
- **Transcript**: Text record of the conversation with speaker labels

## Requirements

### Requirement 1: Voice Activity Detection Control

**User Story:** As a negotiator, I want the AI to stay silent during my conversation, so that it doesn't interrupt the natural flow of negotiation.

#### Acceptance Criteria

1. WHEN the Gemini_Live_API session is initialized, THE Negotiation_Copilot SHALL disable automatic Voice Activity Detection
2. WHILE in Silent_Listening_Mode, THE Negotiation_Copilot SHALL receive continuous audio streams without generating responses
3. THE Negotiation_Copilot SHALL maintain the audio connection for at least 10 minutes without timing out
4. WHEN audio is received in Silent_Listening_Mode, THE Negotiation_Copilot SHALL transcribe the audio without triggering response generation
5. FOR ALL audio received, the connection state SHALL remain stable (no disconnections due to lack of AI responses)

### Requirement 2: Manual Activity Trigger

**User Story:** As a negotiator, I want to tap a button to get instant AI advice, so that I can control when I receive guidance without disrupting the conversation.

#### Acceptance Criteria

1. WHEN the user taps the "Ask AI" button, THE Negotiation_Copilot SHALL send an activityStart message to Gemini_Live_API
2. WHEN activityStart is sent, THE Negotiation_Copilot SHALL immediately send an ADVISOR_QUERY containing current negotiation state
3. WHEN ADVISOR_QUERY is sent, THE Negotiation_Copilot SHALL send an activityEnd message
4. WHEN activityEnd is sent, THE Negotiation_Copilot SHALL receive an AI response within 5 seconds
5. WHEN the AI response is complete, THE Negotiation_Copilot SHALL return to Silent_Listening_Mode
6. FOR ALL button taps, the sequence activityStart → ADVISOR_QUERY → activityEnd SHALL complete without errors

### Requirement 3: Voice Enrollment and Fingerprinting

**User Story:** As a negotiator, I want the system to learn my voice during setup, so that it can automatically distinguish my speech from the counterparty's speech.

#### Acceptance Criteria

1. WHEN the Enrollment_Phase begins, THE Negotiation_Copilot SHALL prompt the user to speak for 3 seconds
2. WHEN the user speaks during enrollment, THE Negotiation_Copilot SHALL extract MFCC features from the audio samples
3. WHEN MFCC extraction completes, THE Negotiation_Copilot SHALL calculate and store the mean and variance of the features as the Voice_Fingerprint
4. THE Voice_Fingerprint SHALL contain at least 13 MFCC coefficients per frame
5. WHEN enrollment completes, THE Negotiation_Copilot SHALL confirm successful voice capture to the user
6. WHEN voice capture is confirmed, THE Negotiation_Copilot SHALL transition directly to Silent_Listening_Mode
7. FOR ALL valid audio samples during enrollment, MFCC extraction SHALL complete within 2 seconds

### Requirement 4: Real-Time Speaker Identification

**User Story:** As a negotiator, I want the system to automatically label who is speaking, so that the AI understands the conversation context without manual input.

#### Acceptance Criteria

1. WHEN audio is received during negotiation, THE Negotiation_Copilot SHALL extract MFCC features from each audio chunk
2. WHEN MFCC features are extracted, THE Negotiation_Copilot SHALL calculate cosine similarity between the chunk and the stored Voice_Fingerprint
3. WHEN similarity exceeds 0.7, THE Negotiation_Copilot SHALL label the transcript segment as "[USER]"
4. WHEN similarity is below 0.7, THE Negotiation_Copilot SHALL label the transcript segment as "[COUNTERPARTY]"
5. THE Negotiation_Copilot SHALL process audio chunks of 100ms duration at 16kHz sample rate
6. FOR ALL audio chunks, speaker identification SHALL complete before the next chunk arrives

### Requirement 5: Negotiation State Management

**User Story:** As a negotiator, I want the system to track key negotiation details extracted from the conversation, so that the AI can provide contextually relevant advice.

#### Acceptance Criteria

1. THE State_Manager SHALL maintain a state object containing item, seller_price, target_price, max_price, market_data, and transcript fields
2. WHEN the AI analyzes the transcript, THE State_Manager SHALL extract and update item details and prices from the conversation
3. WHEN the "Ask AI" button is tapped, THE State_Manager SHALL include the complete state object in the ADVISOR_QUERY
4. WHEN market research completes, THE State_Manager SHALL update the market_data field with price ranges
5. THE State_Manager SHALL retain the last 90 seconds of transcript in the state object
6. FOR ALL state updates, the state object SHALL remain valid JSON

### Requirement 6: Autonomous Research Function Calling

**User Story:** As a negotiator, I want the AI to autonomously research any information it needs, so that I receive data-driven advice without manual lookups.

#### Acceptance Criteria

1. THE Negotiation_Copilot SHALL register a web_search function with Gemini_Live_API
2. WHEN the AI determines research is needed, THE Negotiation_Copilot SHALL execute the web_search function with a self-constructed query
3. WHEN web_search is called, THE Negotiation_Copilot SHALL pass the search query as a parameter
4. WHEN research completes, THE Negotiation_Copilot SHALL return search results to the AI
5. THE web_search function SHALL complete within 3 seconds
6. FOR ALL function calls, the AI SHALL autonomously decide what to search for and when to trigger research based on conversation context

### Requirement 7: Structured Advice Response

**User Story:** As a negotiator, I want to receive concise, actionable advice, so that I can quickly understand what to say and why.

#### Acceptance Criteria

1. WHEN the AI generates advice, THE Negotiation_Copilot SHALL structure the response as: what to say, why (leverage), and optional fallback
2. WHEN generating advice, THE Negotiation_Copilot SHALL limit responses to 150 tokens maximum
3. WHEN advice is delivered, THE Negotiation_Copilot SHALL use audio output modality
4. THE Negotiation_Copilot SHALL generate advice responses within 5 seconds of receiving ADVISOR_QUERY
5. WHEN advice includes research data, THE Negotiation_Copilot SHALL cite specific findings
6. FOR ALL advice responses, the content SHALL be relevant to the current negotiation state

### Requirement 8: User Interface Controls

**User Story:** As a negotiator, I want a clear button to request AI advice, so that I can easily trigger guidance during the conversation.

#### Acceptance Criteria

1. THE Negotiation_Copilot SHALL display an "Ask AI" button in the user interface
2. WHEN the button is tapped, THE Negotiation_Copilot SHALL provide visual feedback within 100ms
3. WHILE the AI is generating a response, THE Negotiation_Copilot SHALL display a loading indicator
4. WHEN the AI response begins playing, THE Negotiation_Copilot SHALL update the UI to show active response state
5. WHEN the AI response completes, THE Negotiation_Copilot SHALL return the button to ready state
6. THE "Ask AI" button SHALL remain accessible and responsive throughout the negotiation session

### Requirement 9: Transcript Management

**User Story:** As a negotiator, I want the system to maintain a labeled conversation history, so that the AI has full context when providing advice.

#### Acceptance Criteria

1. THE Negotiation_Copilot SHALL append each transcribed utterance to the transcript with speaker label
2. WHEN transcript length exceeds 90 seconds of conversation, THE Negotiation_Copilot SHALL retain only the most recent 90 seconds
3. WHEN building ADVISOR_QUERY, THE Negotiation_Copilot SHALL include the complete labeled transcript
4. THE Negotiation_Copilot SHALL format transcript entries as "[SPEAKER] text"
5. WHEN transcription errors occur, THE Negotiation_Copilot SHALL log the error and continue operation
6. FOR ALL transcript entries, speaker labels SHALL be either "[USER]" or "[COUNTERPARTY]"

### Requirement 10: Session Initialization and Configuration

**User Story:** As a negotiator, I want the system to properly configure the AI session, so that all features work correctly from the start.

#### Acceptance Criteria

1. WHEN initializing a session, THE Negotiation_Copilot SHALL configure Gemini_Live_API with VAD disabled
2. WHEN initializing a session, THE Negotiation_Copilot SHALL enable audio input transcription
3. WHEN initializing a session, THE Negotiation_Copilot SHALL enable audio output transcription
4. WHEN initializing a session, THE Negotiation_Copilot SHALL register the search_market_price function
5. WHEN initializing a session, THE Negotiation_Copilot SHALL set response modality to audio only
6. WHEN initializing a session, THE Negotiation_Copilot SHALL set generation temperature to 0.7 and max tokens to 150

### Requirement 11: Audio Streaming Configuration

**User Story:** As a negotiator, I want continuous audio streaming to work reliably, so that the AI never misses parts of the conversation.

#### Acceptance Criteria

1. THE Negotiation_Copilot SHALL stream audio in 100ms chunks at 16kHz sample rate
2. THE Negotiation_Copilot SHALL encode audio as Int16 PCM in little-endian format
3. WHEN audio chunks are sent, THE Negotiation_Copilot SHALL maintain chunk timing within 10ms tolerance
4. THE Negotiation_Copilot SHALL buffer audio to prevent gaps during network fluctuations
5. WHEN audio streaming errors occur, THE Negotiation_Copilot SHALL attempt reconnection within 2 seconds
6. FOR ALL audio streams, the format SHALL remain consistent throughout the session

### Requirement 12: Voice Enrollment User Interface

**User Story:** As a negotiator, I want a clear and guided voice enrollment experience, so that I can quickly set up the system and start negotiating.

#### Acceptance Criteria

1. WHEN the user opens the app, THE Negotiation_Copilot SHALL display a "Voice Setup" screen
2. THE "Voice Setup" screen SHALL display the instruction "Speak for 3 seconds so I can learn your voice"
3. WHEN recording begins, THE Negotiation_Copilot SHALL display a red recording indicator dot
4. WHILE recording, THE Negotiation_Copilot SHALL display a countdown timer showing "3...2...1"
5. WHEN recording completes, THE Negotiation_Copilot SHALL display a "Processing..." spinner
6. WHEN voice fingerprint is successfully created, THE Negotiation_Copilot SHALL display "✓ Voice captured!" confirmation
7. WHEN confirmation is displayed, THE Negotiation_Copilot SHALL transition to the negotiation screen within 1 second
8. FOR ALL enrollment sessions, the UI SHALL provide clear visual feedback at each step

### Requirement 13: Response Latency Optimization

**User Story:** As a negotiator, I want instant AI responses, so that I don't lose momentum during the conversation.

#### Acceptance Criteria

1. WHEN the "Ask AI" button is tapped, THE Negotiation_Copilot SHALL bundle the state object within 100ms
2. WHEN state is bundled, THE Negotiation_Copilot SHALL send the ADVISOR_QUERY to the backend within 200ms
3. WHEN ADVISOR_QUERY is received by backend, THE Negotiation_Copilot SHALL send activity control messages within 300ms
4. THE Negotiation_Copilot SHALL receive first audio bytes from Gemini_Live_API within 3 seconds
5. WHEN audio is received, THE Negotiation_Copilot SHALL begin playback within 500ms
6. FOR ALL button-tap-to-audio-playback sequences, total latency SHALL be under 5 seconds

### Requirement 14: Error Handling and Recovery

**User Story:** As a negotiator, I want the system to handle errors gracefully, so that technical issues don't disrupt my negotiation.

#### Acceptance Criteria

1. WHEN Gemini_Live_API connection fails, THE Negotiation_Copilot SHALL display an error message to the user
2. WHEN connection fails, THE Negotiation_Copilot SHALL attempt automatic reconnection up to 3 times
3. WHEN voice fingerprinting accuracy is below 60%, THE Negotiation_Copilot SHALL warn the user and suggest manual labeling
4. WHEN research fails, THE Negotiation_Copilot SHALL provide advice without research data
5. WHEN audio streaming is interrupted, THE Negotiation_Copilot SHALL resume from the interruption point
6. FOR ALL errors, THE Negotiation_Copilot SHALL log error details for debugging

### Requirement 15: Multi-Turn Conversation Support

**User Story:** As a negotiator, I want to request advice multiple times during a single negotiation, so that I can get guidance at each critical decision point.

#### Acceptance Criteria

1. THE Negotiation_Copilot SHALL support unlimited button taps during a single session
2. WHEN multiple advice requests occur, THE State_Manager SHALL maintain state continuity between requests
3. WHEN the AI completes a response, THE Negotiation_Copilot SHALL immediately return to Silent_Listening_Mode
4. WHEN a new button tap occurs during AI response, THE Negotiation_Copilot SHALL queue the request
5. THE Negotiation_Copilot SHALL process queued requests in order after the current response completes
6. FOR ALL multi-turn sessions, state updates SHALL accumulate correctly across all turns

