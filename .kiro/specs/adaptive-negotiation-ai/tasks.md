# Implementation Plan: Adaptive Negotiation AI

## Overview

This implementation plan transforms the negotiation advisor from providing generic advice to delivering intelligent, data-backed guidance. The system will analyze conversation context, identify missing information, research market data from online sources, and provide strategic negotiation advice based on actual data.

The implementation follows a logical progression: first establishing core infrastructure (market research and information extraction), then building context assembly, enhancing the AI prompt, integrating everything into the advice flow, and finally validating with comprehensive property-based tests.

## Tasks

- [ ] 1. Implement Market Research Service
  - [ ] 1.1 Create market_research.py service file with search functions
    - Implement async search_market_data() function that coordinates marketplace and forum searches
    - Implement async search_marketplaces() function for searching online marketplaces (OLX, Facebook, etc.)
    - Implement async search_forums() function for searching discussion forums (Reddit, etc.)
    - Implement calculate_price_range() function to compute min/max/avg/median prices from results
    - Add error handling for search failures (graceful degradation with partial results)
    - _Requirements: 2.1, 2.2, 2.3, 9.1, 9.2, 9.3, 9.4_

  - [ ]* 1.2 Write property test for graceful search failure
    - **Property 20: Graceful Search Failure**
    - **Validates: Requirements 9.4**

  - [ ]* 1.3 Write property test for price range calculation
    - **Property 6: Price Range Calculation**
    - **Validates: Requirements 2.3**

  - [ ]* 1.4 Write property test for search result structure
    - **Property 19: Search Result Structure**
    - **Validates: Requirements 9.3**

- [ ] 2. Implement Information Extraction Service
  - [ ] 2.1 Add information extraction functions to negotiation_engine.py
    - Implement extract_facts() to identify key facts from conversation (condition, age, location, etc.)
    - Implement extract_questions() to track questions asked by user or counterparty
    - Implement extract_answers() to track answers given to questions
    - Implement extract_moves() to recognize negotiation moves (offers, counter-offers, etc.)
    - _Requirements: 8.1_

  - [ ]* 2.2 Write property test for basic information extraction
    - **Property 17: Basic Information Extraction**
    - **Validates: Requirements 8.1**

- [ ] 3. Implement Context Builder
  - [ ] 3.1 Add build_adaptive_context() function to negotiation_engine.py
    - Extract negotiation metadata (item, prices, message count)
    - Generate structured summary for messages beyond last 10 using extraction functions
    - Preserve full detail for last 10 messages with timestamps
    - Include market research results in context
    - Add advisor_trigger field to signal advice request
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 7.5, 8.2, 8.3, 8.4, 9.5_

  - [ ]* 3.2 Write property test for required metadata fields
    - **Property 10: Required Metadata Fields**
    - **Validates: Requirements 3.1**

  - [ ]* 3.3 Write property test for structured summary generation
    - **Property 11: Structured Summary Generation**
    - **Validates: Requirements 3.2, 3.4, 8.2**

  - [ ]* 3.4 Write property test for recent message preservation
    - **Property 12: Recent Message Preservation**
    - **Validates: Requirements 3.3, 8.3, 8.4**

  - [ ]* 3.5 Write property test for message count accuracy
    - **Property 18: Message Count Accuracy**
    - **Validates: Requirements 8.5**

  - [ ]* 3.6 Write property test for advisor trigger inclusion
    - **Property 16: Advisor Trigger Inclusion**
    - **Validates: Requirements 7.5**

  - [ ]* 3.7 Write property test for market research in context
    - **Property 21: Market Research in Context**
    - **Validates: Requirements 9.5**

- [ ]*4. Checkpoint
  -ask user if any questions 

- [ ] 5. Enhance Master Prompt
  - [ ] 5.1 Update master_prompt.py with enhanced negotiation advisor prompt
    - Create product-agnostic framework (no hardcoded examples)
    - Add information gathering guidelines for identifying missing information
    - Add market research usage instructions for citing sources and comparing prices
    - Add strategic advice patterns for negotiation tactics
    - Add natural response guidelines (no artificial truncation, always provide value)
    - Include context structure documentation
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 6. Enhance Gemini Client
  - [ ] 6.1 Add send_advisor_context() function to gemini_client.py
    - Format complete context for Gemini Live API
    - Send context via WebSocket with proper message structure
    - Handle API errors and connection failures
    - _Requirements: 2.6_

  - [ ]* 6.2 Write property test for research before context
    - **Property 9: Research Before Context**
    - **Validates: Requirements 2.6**

- [ ] 7. Implement Advice Request Handler
  - [ ] 7.1 Enhance handle_ask_advice() in websocket.py
    - Extract negotiation context from state
    - Call market research service with item and prices
    - Build adaptive context using context builder
    - Send complete context to Gemini client
    - Stream audio response back to user
    - Add error handling for each step
    - _Requirements: 7.1, 7.2, 7.3_

  - [ ]* 7.2 Write unit tests for advice request handler
    - Test full flow from request to response
    - Test error handling for search failures
    - Test error handling for invalid state
    - _Requirements: 7.1_

- [ ] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Implement AI Behavior Property Tests
  - [ ]* 9.1 Write property test for information gap identification
    - **Property 1: Information Gap Identification**
    - **Validates: Requirements 1.1**

  - [ ]* 9.2 Write property test for question recommendation
    - **Property 2: Question Recommendation for Gaps**
    - **Validates: Requirements 1.2**

  - [ ]* 9.3 Write property test for product-specific adaptation
    - **Property 3: Product-Specific Adaptation**
    - **Validates: Requirements 1.3, 1.5, 5.2, 5.5**

  - [ ]* 9.4 Write property test for no repeated questions
    - **Property 4: No Repeated Questions**
    - **Validates: Requirements 1.4**

  - [ ]* 9.5 Write property test for market research execution
    - **Property 5: Market Research Execution**
    - **Validates: Requirements 2.1, 2.2**

  - [ ]* 9.6 Write property test for source citation
    - **Property 7: Source Citation**
    - **Validates: Requirements 2.4**

  - [ ]* 9.7 Write property test for item-specific price comparison
    - **Property 8: Item-Specific Price Comparison**
    - **Validates: Requirements 2.5, 10.3**

  - [ ]* 9.8 Write property test for red flag warning
    - **Property 13: Red Flag Warning**
    - **Validates: Requirements 4.4**

  - [ ]* 9.9 Write property test for immediate response
    - **Property 14: Immediate Response**
    - **Validates: Requirements 7.1**

  - [ ]* 9.10 Write property test for no empty responses
    - **Property 15: No Empty Responses**
    - **Validates: Requirements 7.4**

  - [ ]* 9.11 Write property test for price reasoning
    - **Property 22: Price Reasoning**
    - **Validates: Requirements 10.2**

  - [ ]* 9.12 Write property test for confidence indication
    - **Property 23: Confidence Indication**
    - **Validates: Requirements 10.4**

  - [ ]* 9.13 Write property test for insufficient data acknowledgment
    - **Property 24: Insufficient Data Acknowledgment**
    - **Validates: Requirements 10.5**

- [ ] 10. Add Integration Tests
  - [ ]* 10.1 Write integration test for full advice request flow
    - Test end-to-end flow from ASK_ADVICE event to audio response
    - Verify market research is performed
    - Verify context is built correctly
    - Verify response is received
    - _Requirements: 7.1, 2.1, 2.2_

  - [ ]* 10.2 Write integration test for AI behavior with market data
    - Test that AI cites sources when market data is provided
    - Test that AI compares prices based on condition and location
    - _Requirements: 2.4, 2.5_

  - [ ]* 10.3 Write integration test for AI behavior with red flags
    - Test that AI warns about suspicious patterns in conversation
    - _Requirements: 4.4_

- [ ]*11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests should use hypothesis library with minimum 100 iterations each
- All property tests follow the format: "Feature: adaptive-negotiation-ai, Property {number}: {title}"
- The implementation uses Python and integrates with existing FastAPI backend
- Market research service is a new file, other enhancements modify existing files
- Context builder creates hybrid history: structured summary for old messages, full detail for last 10
- Enhanced master prompt is product-agnostic and guides AI to adapt to any negotiation scenario
