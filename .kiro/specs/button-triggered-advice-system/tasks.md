# Implementation Plan: Button-Triggered Advice System (Phase 1)

## Overview

This implementation plan covers Phase 1 of the Button-Triggered Advice System, which transforms the AI Negotiation Copilot from a slow turn-based conversation into a fast, on-demand advisory system. The implementation focuses on five core components: VAD disable with button-tap control, local MFCC-based voice fingerprinting, client-side state management, function calling for market research, and the "Ask AI" button UI.

The system will eliminate the 10-20 second latency by disabling automatic Voice Activity Detection and implementing manual activity control, enabling 3-5 second response times when the user taps the "Ask AI" button.

## Tasks

- [x] 1. Set up testing infrastructure
  - Install hypothesis for Python property-based testing
  - Install fast-check for TypeScript property-based testing
  - Configure pytest for backend tests
  - Configure Jest/Vitest for frontend tests
  - _Requirements: Testing Strategy_

- [x] 2. Implement VAD disable and activity control (Backend)
  - [x] 2.1 Update Gemini Live API configuration to disable VAD
    - Modify `backend/app/services/gemini_client.py`
    - Set `automatic_activity_detection` to `disabled` in `LiveConnectConfig`
    - Enable input and output audio transcription
    - Configure response modality to audio only
    - Set generation config (temperature=0.7, max_tokens=150)
    - _Requirements: 1.1, 10.1, 10.2, 10.3, 10.5, 10.6_
  
  - [ ]* 2.2 Write property test for VAD configuration
    - **Property 3: Activity Control Message Sequence**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.6**
  
  - [x] 2.3 Implement manual activity control sequence
    - Create `trigger_advice_response()` function in `gemini_client.py`
    - Send activityStart message
    - Send ADVISOR_QUERY with state
    - Send activityEnd message
    - _Requirements: 2.1, 2.2, 2.3, 2.6_
  
  - [ ]* 2.4 Write unit tests for activity control timing
    - Test response within 5 seconds
    - Test message sequence order
    - _Requirements: 2.4, 2.6_

- [x] 3. Implement voice fingerprinting (Frontend)
  - [x] 3.1 Create voice fingerprint module
    - Create new file `frontend/lib/voice-fingerprint.ts`
    - Define `VoiceFingerprint` interface
    - Define `MFCCConfig` interface
    - _Requirements: 3.2, 3.3, 3.4_
  
  - [x] 3.2 Implement MFCC extraction
    - Implement `extractMFCC()` function with frame windowing
    - Implement `applyHammingWindow()` helper
    - Implement FFT processing
    - Implement Mel filterbank application
    - Implement DCT for final MFCC coefficients
    - Extract 13 coefficients per frame
    - _Requirements: 3.2, 3.4, 4.1_
  
  - [ ]* 3.3 Write property test for MFCC extraction
    - **Property 5: MFCC Feature Extraction**
    - **Validates: Requirements 3.2, 3.4, 4.1**
  
  - [x] 3.4 Implement voice enrollment
    - Implement `enrollUserVoice()` function
    - Calculate mean and variance vectors
    - Store voice fingerprint with 13 coefficients
    - _Requirements: 3.1, 3.2, 3.3, 3.5_
  
  - [ ]* 3.5 Write property test for voice fingerprint structure
    - **Property 6: Voice Fingerprint Structure**
    - **Validates: Requirements 3.3, 3.4**
  
  - [x] 3.6 Implement real-time speaker identification
    - Implement `identifySpeaker()` function
    - Calculate cosine similarity with threshold 0.7
    - Return 'USER' or 'COUNTERPARTY' label
    - _Requirements: 4.2, 4.3, 4.4_
  
  - [ ]* 3.7 Write property test for speaker classification
    - **Property 7: Speaker Classification**
    - **Validates: Requirements 4.2, 4.3, 4.4**
  
  - [ ]* 3.8 Write unit tests for enrollment flow
    - Test enrollment prompt display
    - Test enrollment confirmation
    - Test MFCC extraction timing (within 2 seconds)
    - _Requirements: 3.1, 3.5, 3.6_

- [x] 3.9 Create voice enrollment UI component
  - [x] 3.9.1 Create VoiceEnrollmentScreen component
    - Create file `frontend/components/enrollment/VoiceEnrollmentScreen.tsx`
    - Implement enrollment states (ready, recording, processing, success, error)
    - Display "Voice Setup" heading
    - Show "Speak for 3 seconds..." instruction
    - Implement recording indicator (red dot + countdown)
    - Implement processing spinner
    - Implement success confirmation with checkmark
    - Auto-transition to negotiation screen
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8_
  
  - [ ]* 3.9.2 Write unit tests for enrollment UI
    - Test state transitions
    - Test countdown timer
    - Test auto-transition timing
    - Test error handling
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement client-side state manager (Frontend)
  - [x] 5.1 Create negotiation state hook
    - Create new file `frontend/hooks/useNegotiationState.ts`
    - Define `NegotiationState` and `TranscriptEntry` interfaces
    - Implement transcript management with 90-second window
    - Implement updateStateFromAI function for AI-driven state updates
    - Implement price extraction from transcript
    - _Requirements: 5.1, 5.2, 5.5, 9.1, 9.2_
  
  - [ ]* 5.2 Write property test for transcript time window
    - **Property 14: Transcript Time Window**
    - **Validates: Requirements 5.5, 9.2**
  
  - [ ]* 5.3 Write property test for state serialization
    - **Property 15: State Serialization Round-Trip**
    - **Validates: Requirements 5.6**
  
  - [x] 5.4 AI-driven state extraction (Already implemented via updateStateFromAI)
    - AI extracts item, seller_price, target_price, max_price from transcript
    - Frontend provides updateStateFromAI() hook for AI to update state
    - Note: extractPriceFromText() exists as fallback but AI extraction is primary mechanism
    - _Requirements: 5.2_
  
  - [ ]* 5.5 Write property test for AI state extraction
    - **Property 11: AI State Extraction and Update**
    - **Validates: Requirements 5.2**
  
  - [x] 5.6 Implement state validation
    - Validate target_price ≤ max_price
    - Display validation errors
    - _Requirements: 12.4, 12.5_
  
  - [ ]* 5.7 Write property test for price validation
    - **Property 26: Price Validation**
    - **Validates: Requirements 12.4, 12.5**
  
  - [ ]* 5.8 Write unit tests for state manager
    - Test state initialization
    - Test transcript entry addition
    - Test market data update
    - _Requirements: 5.1, 5.3, 5.4, 12.6_

- [x] 6. Implement autonomous research function calling (Backend)
  - [x] 6.1 Register web_search function with Gemini
    - Modify `backend/app/services/gemini_client.py`
    - Add function declaration to tools array
    - Define function parameter (query only - AI constructs the query)
    - Description should emphasize AI decides what to search
    - _Requirements: 6.1, 6.3, 10.4_
  
  - [ ]* 6.2 Write property test for function parameters
    - **Property 16: Function Call Parameters**
    - **Validates: Requirements 6.3**
  
  - [x] 6.3 Implement function call handler
    - Create `handle_function_call()` in `gemini_client.py`
    - Implement `perform_web_search()` function
    - Send RESEARCH_STARTED notification with query
    - Send RESEARCH_COMPLETE notification with results
    - _Requirements: 6.2, 6.4_
  
  - [ ]* 6.4 Write property test for function return value
    - **Property 17: Function Return Value**
    - **Validates: Requirements 6.4**
  
  - [ ]* 6.5 Write unit tests for function calling
    - Test function registration
    - Test function execution timing (within 3 seconds)
    - Test autonomous triggering (AI decides what to search)
    - Test graceful failure handling
    - _Requirements: 6.5, 6.6, 14.4_

- [x] 7. Implement "Ask AI" button UI (Frontend)
  - [x] 7.1 Create AskAIButton component
    - Create new file `frontend/components/negotiation/AskAIButton.tsx`
    - Implement button with loading states
    - Add visual feedback (spinner, icons)
    - Ensure accessibility (aria-label)
    - _Requirements: 8.1, 8.2_
  
  - [ ]* 7.2 Write property test for UI state machine
    - **Property 19: UI State Machine**
    - **Validates: Requirements 8.3, 8.4, 8.5**
  
  - [x] 7.3 Implement useAskAI hook
    - Create hook in `frontend/hooks/useAskAI.ts`
    - Handle button tap event
    - Bundle state and send ASK_ADVICE message
    - Manage loading state
    - _Requirements: 5.3, 13.1, 13.2_
  
  - [ ]* 7.4 Write property test for button accessibility
    - **Property 20: Button Accessibility**
    - **Validates: Requirements 8.6**
  
  - [ ]* 7.5 Write unit tests for button UI
    - Test button display
    - Test visual feedback timing (within 100ms)
    - Test loading indicator display
    - Test state transitions
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 8. Implement backend WebSocket handler for ASK_ADVICE (Backend)
  - [x] 8.1 Add ASK_ADVICE message handler
    - Modify `backend/app/api/websocket.py`
    - Implement `handle_ask_advice()` function
    - Extract state from payload
    - Build ADVISOR_QUERY from state
    - _Requirements: 5.3, 9.3_
  
  - [ ]* 8.2 Write property test for complete state in query
    - **Property 12: Complete State in Query**
    - **Validates: Requirements 5.3, 9.3**
  
  - [x] 8.3 Implement ADVISOR_QUERY builder
    - Create `build_advisor_query()` function
    - Format state fields into query text
    - Include labeled transcript
    - Add question prompt
    - _Requirements: 5.3, 9.3, 9.4_
  
  - [x] 8.4 Implement activity control sequence
    - Send activityStart message to Gemini
    - Send ADVISOR_QUERY text
    - Send activityEnd message
    - Handle errors gracefully
    - _Requirements: 2.1, 2.2, 2.3, 2.6, 13.3_
  
  - [ ]* 8.5 Write property test for activity control sequence
    - **Property 3: Activity Control Message Sequence**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.6**
  
  - [ ]* 8.6 Write unit tests for WebSocket handler
    - Test ASK_ADVICE message handling
    - Test ADVISOR_QUERY format
    - Test activity control timing (within 300ms)
    - Test error handling
    - _Requirements: 2.6, 13.3_

- [x] 9. Update system prompt for button-tap model (Backend)
  - [x] 9.1 Modify system prompt in master_prompt.py
    - Update `backend/app/services/master_prompt.py`
    - Add instructions for ADVISOR_QUERY format
    - Specify response structure (what to say, why, fallback)
    - Set response length limit (150 tokens)
    - Emphasize concise, actionable advice
    - _Requirements: 7.1, 7.2, 7.5_
  
  - [ ]* 9.2 Write unit tests for system prompt
    - Test prompt includes ADVISOR_QUERY instructions
    - Test prompt specifies response structure
    - Test prompt sets token limit
    - _Requirements: 7.1, 7.2_

- [x] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Integration testing
  - [x] 11.1 Test end-to-end button tap flow
    - Test complete flow: button tap → state bundle → WebSocket → activity control → AI response → audio playback
    - Verify total latency under 5 seconds
    - _Requirements: 2.4, 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_
  
  - [x] 11.2 Test voice enrollment to classification pipeline
    - Test enrollment → fingerprint creation → real-time classification
    - Verify speaker labels are correct
    - _Requirements: 3.1, 3.2, 3.3, 3.5, 4.2, 4.3, 4.4_
  
  - [x] 11.3 Test AI extraction to query generation
    - Test AI extraction → state update → ADVISOR_QUERY generation
    - Verify all state fields included in query
    - _Requirements: 5.3, 9.3_
  
  - [x] 11.4 Test function calling integration
    - Test AI autonomously triggers research (decides what to search)
    - Verify function execution and result return
    - Verify state update with research data
    - Test various scenarios: prices, reviews, specs, location data
    - _Requirements: 6.2, 6.4, 5.4, 6.6_
  
  - [x] 11.5 Test silent listening mode
    - Test continuous audio streaming without AI responses
    - Verify connection stability for 10 minutes
    - Verify transcript updates without response generation
    - _Requirements: 1.2, 1.3, 1.4, 1.5_
  
  - [x] 11.6 Test multi-turn conversation
    - Test multiple button taps in single session
    - Verify state continuity across requests
    - Verify return to silent mode after each response
    - _Requirements: 15.1, 15.2, 15.3, 2.5_
  
  - [x] 11.7 Test error recovery scenarios
    - Test connection failure and reconnection
    - Test low voice fingerprint accuracy warning
    - Test market research failure graceful handling
    - Test audio interruption recovery
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

- [x] 12. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end flows
- Phase 1 focuses on core functionality: VAD disable, voice fingerprinting, state management, function calling, and "Ask AI" button