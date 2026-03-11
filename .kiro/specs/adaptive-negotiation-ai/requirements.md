# Requirements Document

## Introduction

The Adaptive Negotiation AI feature transforms the negotiation advisor from providing random, generic advice to delivering intelligent, data-backed guidance. The system will analyze conversation context, identify missing critical information, research market data from online sources, and provide strategic negotiation advice based on actual data rather than arbitrary suggestions.

## Glossary

- **Negotiation_Advisor**: The AI system that provides real-time negotiation guidance to users
- **USER**: The person using the negotiation advisor system who is negotiating with a counterparty
- **COUNTERPARTY**: The person the USER is negotiating with (cannot hear the advisor)
- **Conversation_Context**: The complete negotiation history including transcript, prices, and extracted information
- **Market_Data**: Price information and insights gathered from online marketplaces and forums
- **Master_Prompt**: The system prompt that defines the AI advisor's behavior and capabilities
- **Advisor_Query**: The trigger event when the USER requests advice from the system
- **Backend**: The server-side system that manages state, performs searches, and coordinates AI interactions
- **Information_Gap**: Critical missing information that affects negotiation decisions

## Requirements

### Requirement 1: Intelligent Information Gathering

**User Story:** As a USER, I want the Negotiation_Advisor to identify what information is missing and guide me to ask relevant questions, so that I can make informed negotiation decisions.

#### Acceptance Criteria

1. WHEN an Advisor_Query is received, THE Negotiation_Advisor SHALL analyze the Conversation_Context to identify Information_Gaps
2. WHEN Information_Gaps are identified, THE Negotiation_Advisor SHALL recommend specific questions for the USER to ask the COUNTERPARTY
3. THE Negotiation_Advisor SHALL adapt information gathering strategies based on the product type being negotiated
4. IF the COUNTERPARTY has already stated they do not know specific information, THEN THE Negotiation_Advisor SHALL NOT recommend asking for that information again
5. THE Negotiation_Advisor SHALL determine which information factors are relevant based on the product category

### Requirement 2: Market Data Research

**User Story:** As a USER, I want the Negotiation_Advisor to research current market prices and comparable listings, so that I receive data-backed price recommendations instead of random numbers.

#### Acceptance Criteria

1. WHEN an Advisor_Query is received, THE Backend SHALL search online marketplaces for comparable listings
2. WHEN an Advisor_Query is received, THE Backend SHALL search discussion forums for price insights
3. THE Backend SHALL calculate price ranges from search results
4. THE Negotiation_Advisor SHALL cite sources when providing price guidance
5. THE Negotiation_Advisor SHALL compare prices based on condition, location, and other relevant factors
6. THE Backend SHALL complete market research before sending context to the Negotiation_Advisor

### Requirement 3: Context-Aware Conversation Analysis

**User Story:** As a USER, I want the Negotiation_Advisor to understand the full negotiation history and recent conversation details, so that advice is relevant to the current situation.

#### Acceptance Criteria

1. THE Backend SHALL provide the Negotiation_Advisor with negotiation metadata including item name, prices, and message count
2. THE Backend SHALL generate structured summaries of conversation history beyond the last 10 messages
3. THE Backend SHALL provide full message details for the last 10 messages in the Conversation_Context
4. THE structured summary SHALL include key facts discovered, questions asked, answers given, and negotiation moves made
5. THE Negotiation_Advisor SHALL analyze both historical summary and recent messages to provide contextual advice

### Requirement 4: Strategic Negotiation Guidance

**User Story:** As a USER, I want the Negotiation_Advisor to provide strategic negotiation tactics based on conversation dynamics, so that I can negotiate more effectively.

#### Acceptance Criteria

1. WHEN providing advice, THE Negotiation_Advisor SHALL base recommendations on Market_Data and Conversation_Context
2. THE Negotiation_Advisor SHALL identify negotiation dynamics including leverage, urgency, and relationship factors
3. THE Negotiation_Advisor SHALL suggest specific tactics such as counter-offers or walking away when appropriate
4. THE Negotiation_Advisor SHALL warn about red flags or potential issues identified in the conversation
5. THE Negotiation_Advisor SHALL provide actionable advice that the USER can immediately apply

### Requirement 5: Product-Agnostic Adaptation

**User Story:** As a USER, I want the Negotiation_Advisor to work for any type of product or service, so that I can use it for diverse negotiation scenarios.

#### Acceptance Criteria

1. THE Negotiation_Advisor SHALL analyze any product type without requiring hardcoded product-specific logic
2. THE Negotiation_Advisor SHALL determine relevant value factors based on the product category
3. FOR physical items, THE Negotiation_Advisor SHALL consider condition, age, authenticity, and functionality
4. FOR services, THE Negotiation_Advisor SHALL consider scope, timeline, and quality guarantees
5. THE Negotiation_Advisor SHALL adapt questioning and research strategies to the specific product being negotiated

### Requirement 6: Enhanced Master Prompt

**User Story:** As a developer, I want the Master_Prompt to provide comprehensive guidance to the AI, so that the Negotiation_Advisor can deliver intelligent advice consistently.

#### Acceptance Criteria

1. THE Master_Prompt SHALL define the Negotiation_Advisor's role and capabilities
2. THE Master_Prompt SHALL provide a framework for analyzing negotiation situations
3. THE Master_Prompt SHALL include guidelines for information gathering, market research, and strategic advice
4. THE Master_Prompt SHALL instruct the Negotiation_Advisor to respond naturally without artificial length constraints
5. THE Master_Prompt SHALL be product-agnostic and avoid hardcoded examples

### Requirement 7: Immediate Response to Advisor Queries

**User Story:** As a USER, I want the Negotiation_Advisor to respond immediately when I request advice, so that I can continue the negotiation without delays.

#### Acceptance Criteria

1. WHEN an Advisor_Query trigger is detected, THE Negotiation_Advisor SHALL respond immediately with audio advice
2. THE Negotiation_Advisor SHALL provide complete advice without artificially truncating information
3. THE Negotiation_Advisor SHALL speak naturally as if advising a friend
4. THE Negotiation_Advisor SHALL always provide value and SHALL NOT respond with "I don't know" without attempting to help
5. THE Backend SHALL pass the Advisor_Query trigger in the Conversation_Context

### Requirement 8: Conversation History Management

**User Story:** As a developer, I want the Backend to efficiently manage conversation history, so that the Negotiation_Advisor has relevant context without overwhelming token limits.

#### Acceptance Criteria

1. THE Backend SHALL extract basic information including item name, prices, and known facts from the conversation
2. THE Backend SHALL create structured summaries for messages beyond the last 10 messages
3. THE Backend SHALL preserve full detail for the last 10 messages
4. THE Backend SHALL include timestamps for recent messages
5. THE Backend SHALL track the total number of messages in the negotiation

### Requirement 9: Market Data Search Integration

**User Story:** As a developer, I want the Backend to integrate with web search capabilities, so that market research can be performed automatically.

#### Acceptance Criteria

1. THE Backend SHALL implement search functions for online marketplaces
2. THE Backend SHALL implement search functions for discussion forums
3. THE Backend SHALL structure search results into marketplace listings and forum discussions
4. THE Backend SHALL handle search failures gracefully and provide partial results when available
5. THE Backend SHALL pass structured search results to the Negotiation_Advisor in the Conversation_Context

### Requirement 10: Data-Backed Price Recommendations

**User Story:** As a USER, I want price recommendations based on actual market data, so that I can negotiate with confidence and realistic expectations.

#### Acceptance Criteria

1. WHEN providing price recommendations, THE Negotiation_Advisor SHALL reference Market_Data
2. THE Negotiation_Advisor SHALL explain the reasoning behind price recommendations
3. THE Negotiation_Advisor SHALL consider the condition and specifics of the item being negotiated
4. THE Negotiation_Advisor SHALL indicate confidence level based on available Market_Data quality
5. IF Market_Data is insufficient, THEN THE Negotiation_Advisor SHALL acknowledge limitations and provide best-effort guidance
