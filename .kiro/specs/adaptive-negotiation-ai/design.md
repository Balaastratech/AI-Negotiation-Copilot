# Design Document: Adaptive Negotiation AI

## Overview

The Adaptive Negotiation AI feature transforms the negotiation advisor from a generic advice system into an intelligent, data-driven negotiation assistant. The system analyzes conversation context, identifies missing critical information, researches market data from online sources, and provides strategic negotiation advice based on actual data rather than arbitrary suggestions.

### Core Capabilities

1. **Intelligent Information Gathering**: Identifies missing critical information and guides users to ask relevant questions
2. **Market Data Research**: Searches online marketplaces and forums for comparable listings and price insights
3. **Context-Aware Analysis**: Understands full negotiation history and recent conversation dynamics
4. **Strategic Guidance**: Provides data-backed negotiation tactics based on conversation context
5. **Product-Agnostic Adaptation**: Works for any product or service without hardcoded logic

### Key Design Principles

- **AI-Driven Intelligence**: The AI determines what information matters based on product type and context
- **Data-Backed Recommendations**: All price recommendations are based on actual market research
- **Natural Interaction**: Responses are conversational and complete, not artificially truncated
- **Immediate Response**: Advice is provided instantly when requested by the user
- **Adaptive Strategy**: The system adapts to conversation flow and negotiation dynamics

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Audio Input  │  │ Transcript   │  │ Ask Advice   │     │
│  │ (User/CP)    │  │ Display      │  │ Button       │     │
│  └──────┬───────┘  └──────────────┘  └──────┬───────┘     │
│         │                                     │              │
└─────────┼─────────────────────────────────────┼─────────────┘
          │                                     │
          │ WebSocket                           │ ASK_ADVICE
          │                                     │
┌─────────▼─────────────────────────────────────▼─────────────┐
│                    Backend (FastAPI)                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Negotiation Engine                            │  │
│  │  • Manages conversation state                         │  │
│  │  • Extracts basic information (item, prices, facts)   │  │
│  │  • Creates structured summaries                       │  │
│  │  • Coordinates market research                        │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                            │
│  ┌──────────────▼───────────────────────────────────────┐  │
│  │         Market Research Service                       │  │
│  │  • Searches online marketplaces (OLX, Facebook, etc.) │  │
│  │  • Searches discussion forums (Reddit, etc.)          │  │
│  │  • Calculates price ranges                            │  │
│  │  • Structures search results                          │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                            │
│  ┌──────────────▼───────────────────────────────────────┐  │
│  │         Context Builder                               │  │
│  │  • Builds negotiation metadata                        │  │
│  │  • Creates conversation summary (old messages)        │  │
│  │  • Provides full detail (last 10 messages)            │  │
│  │  • Includes market research results                   │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                            │
└─────────────────┼────────────────────────────────────────────┘
                  │ Complete Context
                  │
┌─────────────────▼────────────────────────────────────────────┐
│              Gemini Live API (AI Advisor)                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Enhanced Master Prompt                        │  │
│  │  • Product-agnostic framework                         │  │
│  │  • Information gathering guidelines                   │  │
│  │  • Market research instructions                       │  │
│  │  • Strategic advice patterns                          │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                            │
│  ┌──────────────▼───────────────────────────────────────┐  │
│  │         AI Analysis & Response                        │  │
│  │  • Identifies information gaps                        │  │
│  │  • Analyzes market data                               │  │
│  │  • Determines negotiation dynamics                    │  │
│  │  • Generates strategic advice                         │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                            │
└─────────────────┼────────────────────────────────────────────┘
                  │ Audio Advice
                  │
┌─────────────────▼────────────────────────────────────────────┐
│                    Frontend (Audio Output)                   │
└──────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Conversation Capture**: User and counterparty audio is transcribed in real-time
2. **Advice Request**: User clicks "Ask Advice" button, triggering ASK_ADVICE event
3. **Backend Processing**:
   - Extract basic information (item, prices, known facts)
   - Perform market research (marketplaces + forums)
   - Build structured conversation summary (old messages)
   - Prepare full detail for recent messages (last 10)
4. **Context Assembly**: Combine all information into comprehensive context
5. **AI Analysis**: Gemini Live receives context and analyzes:
   - Information gaps
   - Market data
   - Negotiation dynamics
   - Strategic opportunities
6. **Advice Delivery**: AI provides audio advice immediately to user

### Conversation History Strategy

The system uses a **hybrid approach** to manage conversation history efficiently:

- **Structured Summary**: Messages 1 to N-10 are summarized with:
  - Key facts discovered
  - Questions asked and answers given
  - Negotiation moves made
- **Full Detail**: Last 10 messages are provided in complete form with timestamps
- **Metadata**: Item name, prices, message count always included

This approach balances token efficiency with context richness, ensuring the AI has both historical awareness and recent precision.



## Components and Interfaces

### 1. Enhanced Master Prompt

**Location**: `backend/app/services/master_prompt.py`

**Purpose**: Provides comprehensive guidance to the AI advisor for analyzing negotiation situations and delivering intelligent advice.

**Key Features**:
- Product-agnostic framework (no hardcoded examples)
- Information gathering guidelines
- Market research instructions
- Strategic advice patterns
- Natural response guidelines

**Interface**:
```python
MASTER_NEGOTIATION_PROMPT: str
# Template string with {context} placeholder
# Defines AI advisor role, analysis framework, and response guidelines
```

**Responsibilities**:
- Define AI advisor's role and capabilities
- Provide framework for analyzing any product type
- Guide information gathering strategies
- Instruct on market research usage
- Set response tone and completeness expectations

### 2. Context Builder

**Location**: `backend/app/services/negotiation_engine.py` (new function)

**Purpose**: Assembles comprehensive negotiation context from conversation state and market research.

**Interface**:
```python
def build_adaptive_context(
    state: dict,
    search_results: dict
) -> dict:
    """
    Build complete negotiation context for AI awareness.
    
    Args:
        state: Current negotiation state including transcript, prices, item
        search_results: Market research results from search service
        
    Returns:
        Dictionary containing:
        - negotiation_metadata: item, prices, message count
        - conversation_summary: structured summary of old messages
        - recent_conversation: full detail of last 10 messages
        - market_research: search results from marketplaces and forums
        - advisor_trigger: signal that user needs advice
    """
```

**Responsibilities**:
- Extract negotiation metadata (item, prices, message count)
- Create structured summaries for messages beyond last 10
- Preserve full detail for last 10 messages with timestamps
- Include market research results
- Format advisor query trigger

### 3. Market Research Service

**Location**: `backend/app/services/market_research.py` (new file)

**Purpose**: Searches online sources for market data and price insights.

**Interface**:
```python
async def search_market_data(
    item: str,
    user_price: float,
    counterparty_price: float
) -> dict:
    """
    Search for market data on marketplaces and forums.
    
    Args:
        item: Name/description of item being negotiated
        user_price: User's asking price
        counterparty_price: Counterparty's offer
        
    Returns:
        Dictionary containing:
        - marketplace_listings: List of comparable listings
        - forum_discussions: List of relevant forum posts
        - price_range: Calculated min/max/avg prices
    """

async def search_marketplaces(item: str) -> list:
    """Search online marketplaces (OLX, Facebook, etc.)"""

async def search_forums(item: str) -> list:
    """Search discussion forums (Reddit, etc.)"""

def calculate_price_range(results: dict) -> dict:
    """Calculate price statistics from search results"""
```

**Responsibilities**:
- Search online marketplaces for comparable listings
- Search discussion forums for price insights
- Calculate price ranges (min, max, average)
- Structure results for AI consumption
- Handle search failures gracefully

### 4. Information Extraction Service

**Location**: `backend/app/services/negotiation_engine.py` (new functions)

**Purpose**: Extracts structured information from conversation transcript.

**Interface**:
```python
def extract_facts(messages: list) -> list:
    """Extract key facts discovered in conversation"""

def extract_questions(messages: list) -> list:
    """Extract questions asked by user or counterparty"""

def extract_answers(messages: list) -> list:
    """Extract answers given to questions"""

def extract_moves(messages: list) -> list:
    """Extract negotiation moves (offers, counter-offers, etc.)"""
```

**Responsibilities**:
- Parse conversation transcript
- Identify key facts (condition, age, location, etc.)
- Track questions and answers
- Recognize negotiation moves
- Structure information for summary

### 5. Advice Request Handler

**Location**: `backend/app/api/websocket.py` (enhanced)

**Purpose**: Handles ASK_ADVICE events and coordinates advice generation.

**Interface**:
```python
async def handle_ask_advice(
    websocket: WebSocket,
    state: dict
) -> None:
    """
    Handle user request for advice with market research.
    
    Flow:
    1. Extract negotiation context from state
    2. Perform market research
    3. Build adaptive context
    4. Send to AI advisor
    5. Stream audio response to user
    """
```

**Responsibilities**:
- Receive ASK_ADVICE trigger from frontend
- Coordinate market research
- Build complete context
- Send context to Gemini Live API
- Stream audio response back to user

### 6. Gemini Client Enhancement

**Location**: `backend/app/services/gemini_client.py` (enhanced)

**Purpose**: Manages communication with Gemini Live API.

**Interface**:
```python
async def send_advisor_context(
    context: dict
) -> None:
    """
    Send complete context to Gemini Live for advice generation.
    
    Formats context as structured message including:
    - Negotiation metadata
    - Conversation summary
    - Recent messages
    - Market research results
    - Advisor query trigger
    """
```

**Responsibilities**:
- Format context for Gemini Live API
- Send context via WebSocket
- Receive audio response
- Handle API errors

### Component Interactions

```
ASK_ADVICE Event
    ↓
Advice Request Handler
    ↓
    ├─→ Market Research Service
    │   ├─→ search_marketplaces()
    │   ├─→ search_forums()
    │   └─→ calculate_price_range()
    │
    └─→ Context Builder
        ├─→ extract_facts()
        ├─→ extract_questions()
        ├─→ extract_answers()
        ├─→ extract_moves()
        └─→ build_adaptive_context()
            ↓
        Gemini Client
            ↓
        Gemini Live API (with Enhanced Master Prompt)
            ↓
        Audio Advice Response
```



## Data Models

### NegotiationContext

Complete context provided to AI advisor for analysis.

```python
{
    "negotiation_metadata": {
        "item": str,                    # Item being negotiated
        "user_asking_price": float,     # User's asking price
        "counterparty_offer": float,    # Counterparty's current offer
        "total_messages": int           # Total message count
    },
    
    "conversation_summary": {
        "key_facts": [                  # Facts discovered in old messages
            {
                "fact": str,            # e.g., "iPhone 12, 128GB"
                "source": str           # "user" or "counterparty"
            }
        ],
        "questions_asked": [            # Questions from old messages
            {
                "question": str,
                "asker": str,           # "user" or "counterparty"
                "answered": bool
            }
        ],
        "answers_given": [              # Answers from old messages
            {
                "question": str,
                "answer": str,
                "responder": str
            }
        ],
        "negotiation_moves": [          # Negotiation actions
            {
                "move": str,            # "offer", "counter", "accept", "reject"
                "actor": str,
                "details": str
            }
        ]
    },
    
    "recent_conversation": [            # Last 10 messages in full
        {
            "speaker": str,             # "user" or "counterparty"
            "text": str,                # Full message text
            "timestamp": str            # ISO format timestamp
        }
    ],
    
    "market_research": {
        "marketplace_listings": [
            {
                "source": str,          # "OLX", "Facebook", etc.
                "title": str,
                "price": float,
                "condition": str,
                "location": str,
                "url": str
            }
        ],
        "forum_discussions": [
            {
                "source": str,          # "Reddit", etc.
                "title": str,
                "summary": str,
                "price_mentioned": float,
                "url": str
            }
        ],
        "price_range": {
            "min": float,
            "max": float,
            "average": float,
            "sample_size": int
        }
    },
    
    "advisor_trigger": str              # "🔔 USER needs advice RIGHT NOW..."
}
```

### MarketSearchResults

Results from market research searches.

```python
{
    "marketplace_listings": [
        {
            "source": str,              # Marketplace name
            "title": str,               # Listing title
            "price": float,             # Listed price
            "condition": str,           # Item condition
            "location": str,            # Seller location
            "url": str,                 # Listing URL
            "posted_date": str          # When posted
        }
    ],
    "forum_discussions": [
        {
            "source": str,              # Forum name
            "title": str,               # Thread title
            "summary": str,             # Key points
            "price_mentioned": float,   # Price if mentioned
            "url": str,                 # Thread URL
            "date": str                 # Post date
        }
    ],
    "price_range": {
        "min": float,                   # Minimum price found
        "max": float,                   # Maximum price found
        "average": float,               # Average price
        "median": float,                # Median price
        "sample_size": int              # Number of listings
    }
}
```

### ConversationMessage

Individual message in the negotiation transcript.

```python
{
    "speaker": str,                     # "user" or "counterparty"
    "text": str,                        # Message content
    "timestamp": str,                   # ISO format timestamp
    "message_index": int                # Position in conversation
}
```

### NegotiationState

Current state of the negotiation (existing model, enhanced).

```python
{
    "item": str,                        # Item being negotiated
    "userPrice": float,                 # User's asking price
    "counterpartyPrice": float,         # Counterparty's offer
    "transcript": [ConversationMessage], # Full conversation history
    "status": str,                      # "active", "completed", "abandoned"
    "started_at": str,                  # ISO timestamp
    "last_updated": str                 # ISO timestamp
}
```

### InformationGap

Missing information identified by AI.

```python
{
    "category": str,                    # "condition", "age", "authenticity", etc.
    "importance": str,                  # "critical", "important", "nice-to-have"
    "suggested_question": str,          # Question user should ask
    "reason": str                       # Why this information matters
}
```



## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property 1: Information Gap Identification

For any conversation context provided to the Negotiation Advisor, if critical information is missing (such as condition, age, location, or other product-relevant factors), the advisor should identify at least one information gap.

**Validates: Requirements 1.1**

### Property 2: Question Recommendation for Gaps

For any identified information gap, the Negotiation Advisor should recommend at least one specific question that the user can ask the counterparty to fill that gap.

**Validates: Requirements 1.2**

### Property 3: Product-Specific Adaptation

For any product type (physical items, services, digital goods, etc.), the Negotiation Advisor should adapt its information gathering strategy, relevant value factors, and questioning approach based on the product category, without requiring hardcoded product-specific logic.

**Validates: Requirements 1.3, 1.5, 5.2, 5.5**

### Property 4: No Repeated Questions

For any conversation where the counterparty has explicitly stated they do not know specific information, the Negotiation Advisor should not recommend asking for that same information again.

**Validates: Requirements 1.4**

### Property 5: Market Research Execution

For any advisor query received, the backend should execute both marketplace searches and forum searches before building the context for the AI advisor.

**Validates: Requirements 2.1, 2.2**

### Property 6: Price Range Calculation

For any set of search results containing price information, the backend should calculate price statistics including minimum, maximum, and average prices.

**Validates: Requirements 2.3**

### Property 7: Source Citation

For any advice that includes price guidance or market insights, the Negotiation Advisor should cite the sources of that information (marketplace names, forum names, or specific URLs).

**Validates: Requirements 2.4**

### Property 8: Item-Specific Price Comparison

For any market data that includes items with varying conditions, locations, or other relevant factors, the Negotiation Advisor should mention and compare based on these specific factors when providing price guidance.

**Validates: Requirements 2.5, 10.3**

### Property 9: Research Before Context

For any context sent to the Negotiation Advisor, the market research results should already be included, ensuring research completes before AI analysis begins.

**Validates: Requirements 2.6**

### Property 10: Required Metadata Fields

For any negotiation context built by the backend, it should contain the required metadata fields: item name, user asking price, counterparty offer, and total message count.

**Validates: Requirements 3.1**

### Property 11: Structured Summary Generation

For any conversation with more than 10 messages, the backend should generate a structured summary for messages beyond the last 10, including key facts, questions asked, answers given, and negotiation moves.

**Validates: Requirements 3.2, 3.4, 8.2**

### Property 12: Recent Message Preservation

For any conversation context, the backend should include the last N messages (up to 10) in full detail with complete text and timestamps.

**Validates: Requirements 3.3, 8.3, 8.4**

### Property 13: Red Flag Warning

For any conversation containing known red flag patterns (such as "cash only", "no returns", "must decide now", "wire transfer", etc.), the Negotiation Advisor should mention these potential issues in its advice.

**Validates: Requirements 4.4**

### Property 14: Immediate Response

For any advisor query trigger sent to the Negotiation Advisor, a response should be received within a reasonable time threshold (e.g., 5 seconds for initial response).

**Validates: Requirements 7.1**

### Property 15: No Empty Responses

For any advisor query, the Negotiation Advisor should not respond with standalone phrases like "I don't know" or "I can't help" without attempting to provide some form of guidance or explanation.

**Validates: Requirements 7.4**

### Property 16: Advisor Trigger Inclusion

For any conversation context built for an advice request, it should include the advisor query trigger field indicating the user needs advice.

**Validates: Requirements 7.5**

### Property 17: Basic Information Extraction

For any conversation transcript, the backend should extract basic information including item name, prices mentioned, and key facts stated by either party.

**Validates: Requirements 8.1**

### Property 18: Message Count Accuracy

For any negotiation state, the total message count in the metadata should equal the actual number of messages in the transcript.

**Validates: Requirements 8.5**

### Property 19: Search Result Structure

For any market research results returned by the backend, they should be structured into two categories: marketplace listings and forum discussions, each with appropriate fields.

**Validates: Requirements 9.3**

### Property 20: Graceful Search Failure

For any search operation that fails (marketplace or forum), the backend should handle the failure gracefully, not crash, and return whatever partial results are available from successful searches.

**Validates: Requirements 9.4**

### Property 21: Market Research in Context

For any conversation context built after an advice request, it should include the market_research field containing structured search results.

**Validates: Requirements 9.5**

### Property 22: Price Reasoning

For any price recommendation provided by the Negotiation Advisor, it should be accompanied by reasoning that explains why that price or price range is suggested.

**Validates: Requirements 10.2**

### Property 23: Confidence Indication

For any advice based on market data, the Negotiation Advisor should indicate confidence level (high, medium, low) based on the quality and quantity of available market data.

**Validates: Requirements 10.4**

### Property 24: Insufficient Data Acknowledgment

For any advice request where market data is insufficient (empty results, very few listings, or no price information), the Negotiation Advisor should explicitly acknowledge this limitation while still providing best-effort guidance.

**Validates: Requirements 10.5**



## Error Handling

### Market Research Failures

**Scenario**: External search APIs fail or return errors

**Handling**:
- Catch exceptions from marketplace and forum search functions
- Log errors with details for debugging
- Return partial results from successful searches
- Include error status in market_research results
- AI advisor acknowledges limited data and provides best-effort advice

**Example**:
```python
try:
    marketplace_results = await search_marketplaces(item)
except Exception as e:
    logger.error(f"Marketplace search failed: {e}")
    marketplace_results = []
    
try:
    forum_results = await search_forums(item)
except Exception as e:
    logger.error(f"Forum search failed: {e}")
    forum_results = []

# Continue with whatever results are available
return {
    "marketplace_listings": marketplace_results,
    "forum_discussions": forum_results,
    "search_errors": errors_encountered
}
```

### Empty or Invalid Conversation State

**Scenario**: Advice requested with no conversation history or missing required fields

**Handling**:
- Validate state before processing
- Provide default values for missing optional fields
- Return error message to user if critical fields missing (item, transcript)
- Log validation failures

**Example**:
```python
if not state.get('item'):
    return {"error": "Cannot provide advice without knowing what item is being negotiated"}
    
if not state.get('transcript') or len(state['transcript']) == 0:
    return {"error": "Cannot provide advice without conversation history"}
```

### Gemini API Connection Failures

**Scenario**: WebSocket connection to Gemini Live API fails or disconnects

**Handling**:
- Implement retry logic with exponential backoff
- Maintain connection state and attempt reconnection
- Notify user of connection issues
- Queue advice requests during disconnection
- Log connection errors for monitoring

**Example**:
```python
max_retries = 3
retry_delay = 1

for attempt in range(max_retries):
    try:
        await gemini_client.connect()
        break
    except ConnectionError as e:
        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay * (2 ** attempt))
        else:
            return {"error": "Unable to connect to AI advisor service"}
```

### Malformed Search Results

**Scenario**: Search results missing expected fields or in unexpected format

**Handling**:
- Validate search result structure before processing
- Use default values for missing optional fields
- Skip malformed entries rather than failing entire operation
- Log data quality issues

**Example**:
```python
def validate_listing(listing: dict) -> bool:
    required_fields = ['title', 'price', 'source']
    return all(field in listing for field in required_fields)

valid_listings = [
    listing for listing in raw_listings 
    if validate_listing(listing)
]
```

### Context Size Limits

**Scenario**: Conversation history exceeds token limits for AI model

**Handling**:
- Implement aggressive summarization for very long conversations
- Prioritize recent messages over old messages
- Truncate structured summary if necessary
- Include message count so AI knows context is partial

**Example**:
```python
MAX_SUMMARY_TOKENS = 2000
MAX_RECENT_MESSAGES = 10

if estimated_tokens(summary) > MAX_SUMMARY_TOKENS:
    summary = truncate_summary(summary, MAX_SUMMARY_TOKENS)
    summary['truncated'] = True
```

### Information Extraction Failures

**Scenario**: Unable to extract structured information from conversation

**Handling**:
- Provide empty structures rather than failing
- Include raw transcript as fallback
- Log extraction failures for improvement
- AI can still analyze raw messages

**Example**:
```python
try:
    facts = extract_facts(messages)
except Exception as e:
    logger.error(f"Fact extraction failed: {e}")
    facts = []  # Empty list, not failure

# Continue with empty facts - AI has raw messages
```

### Rate Limiting

**Scenario**: External APIs rate limit requests

**Handling**:
- Implement request throttling
- Cache search results for repeated queries
- Return cached results when available
- Inform user of delays if rate limited

**Example**:
```python
@rate_limit(max_calls=10, period=60)
async def search_marketplaces(item: str):
    # Check cache first
    cached = await cache.get(f"search:{item}")
    if cached:
        return cached
    
    # Perform search
    results = await perform_search(item)
    await cache.set(f"search:{item}", results, ttl=300)
    return results
```

## Testing Strategy

### Dual Testing Approach

The testing strategy employs both unit tests and property-based tests to ensure comprehensive coverage:

- **Unit tests**: Verify specific examples, edge cases, and error conditions
- **Property tests**: Verify universal properties across all inputs

Both approaches are complementary and necessary. Unit tests catch concrete bugs and validate specific scenarios, while property tests verify general correctness across a wide range of inputs.

### Unit Testing

**Focus Areas**:
- Specific examples demonstrating correct behavior
- Integration points between components
- Edge cases (empty conversations, missing data, malformed input)
- Error conditions (API failures, invalid state, connection errors)

**Example Unit Tests**:

```python
def test_context_builder_with_short_conversation():
    """Test context building with fewer than 10 messages"""
    state = {
        'item': 'iPhone 12',
        'userPrice': 50000,
        'counterpartyPrice': 40000,
        'transcript': [
            {'speaker': 'user', 'text': 'Hello', 'timestamp': '2024-01-01T10:00:00'},
            {'speaker': 'counterparty', 'text': 'Hi', 'timestamp': '2024-01-01T10:01:00'}
        ]
    }
    
    context = build_adaptive_context(state, {})
    
    assert context['negotiation_metadata']['item'] == 'iPhone 12'
    assert len(context['recent_conversation']) == 2
    assert context['conversation_summary']['key_facts'] == []

def test_search_failure_handling():
    """Test that search failures return partial results"""
    with patch('search_marketplaces', side_effect=Exception("API Error")):
        with patch('search_forums', return_value=[{'title': 'Forum post'}]):
            results = await search_market_data('iPhone', 50000, 40000)
            
            assert results['marketplace_listings'] == []
            assert len(results['forum_discussions']) == 1
            assert 'search_errors' in results

def test_price_range_calculation_empty_results():
    """Test price range calculation with no results"""
    results = {'marketplace_listings': [], 'forum_discussions': []}
    price_range = calculate_price_range(results)
    
    assert price_range['min'] is None
    assert price_range['max'] is None
    assert price_range['sample_size'] == 0
```

**Unit Test Guidelines**:
- Keep tests focused on single behaviors
- Use descriptive test names
- Mock external dependencies (APIs, databases)
- Test both success and failure paths
- Avoid testing too many scenarios in unit tests (property tests handle coverage)

### Property-Based Testing

**Testing Library**: Use `hypothesis` for Python property-based testing

**Configuration**: Each property test should run minimum 100 iterations to ensure comprehensive input coverage

**Property Test Structure**:

```python
from hypothesis import given, strategies as st

@given(
    item=st.text(min_size=1),
    user_price=st.floats(min_value=0, allow_nan=False),
    counterparty_price=st.floats(min_value=0, allow_nan=False),
    messages=st.lists(st.dictionaries(...), min_size=0, max_size=50)
)
@settings(max_examples=100)
def test_property_required_metadata_fields(item, user_price, counterparty_price, messages):
    """
    Feature: adaptive-negotiation-ai, Property 10: Required Metadata Fields
    
    For any negotiation context built by the backend, it should contain 
    the required metadata fields: item name, user asking price, 
    counterparty offer, and total message count.
    """
    state = {
        'item': item,
        'userPrice': user_price,
        'counterpartyPrice': counterparty_price,
        'transcript': messages
    }
    
    context = build_adaptive_context(state, {})
    
    assert 'negotiation_metadata' in context
    assert context['negotiation_metadata']['item'] == item
    assert context['negotiation_metadata']['user_asking_price'] == user_price
    assert context['negotiation_metadata']['counterparty_offer'] == counterparty_price
    assert context['negotiation_metadata']['total_messages'] == len(messages)
```

**Property Test Examples**:

1. **Property 11: Structured Summary Generation**
```python
@given(messages=st.lists(message_strategy(), min_size=11, max_size=100))
@settings(max_examples=100)
def test_property_structured_summary_generation(messages):
    """
    Feature: adaptive-negotiation-ai, Property 11: Structured Summary Generation
    
    For any conversation with more than 10 messages, the backend should 
    generate a structured summary for messages beyond the last 10.
    """
    state = {'item': 'test', 'transcript': messages}
    context = build_adaptive_context(state, {})
    
    assert 'conversation_summary' in context
    summary = context['conversation_summary']
    assert 'key_facts' in summary
    assert 'questions_asked' in summary
    assert 'answers_given' in summary
    assert 'negotiation_moves' in summary
```

2. **Property 18: Message Count Accuracy**
```python
@given(messages=st.lists(message_strategy(), min_size=0, max_size=100))
@settings(max_examples=100)
def test_property_message_count_accuracy(messages):
    """
    Feature: adaptive-negotiation-ai, Property 18: Message Count Accuracy
    
    For any negotiation state, the total message count in the metadata 
    should equal the actual number of messages in the transcript.
    """
    state = {'item': 'test', 'transcript': messages}
    context = build_adaptive_context(state, {})
    
    expected_count = len(messages)
    actual_count = context['negotiation_metadata']['total_messages']
    assert actual_count == expected_count
```

3. **Property 20: Graceful Search Failure**
```python
@given(
    marketplace_fails=st.booleans(),
    forum_fails=st.booleans()
)
@settings(max_examples=100)
def test_property_graceful_search_failure(marketplace_fails, forum_fails):
    """
    Feature: adaptive-negotiation-ai, Property 20: Graceful Search Failure
    
    For any search operation that fails, the backend should handle the 
    failure gracefully, not crash, and return whatever partial results 
    are available from successful searches.
    """
    with patch('search_marketplaces', side_effect=Exception if marketplace_fails else None):
        with patch('search_forums', side_effect=Exception if forum_fails else None):
            # Should not raise exception
            results = await search_market_data('test item', 100, 90)
            
            # Should return structured results even if empty
            assert 'marketplace_listings' in results
            assert 'forum_discussions' in results
            assert isinstance(results['marketplace_listings'], list)
            assert isinstance(results['forum_discussions'], list)
```

**Property Test Tag Format**:
```python
"""
Feature: adaptive-negotiation-ai, Property {number}: {property_title}

{property_description}
"""
```

### Integration Testing

**Focus Areas**:
- End-to-end advice request flow
- WebSocket communication with Gemini API
- Market research integration with real APIs (in staging)
- Context building with real conversation data

**Example Integration Tests**:

```python
async def test_full_advice_request_flow():
    """Test complete flow from advice request to response"""
    # Setup
    websocket = await connect_test_client()
    state = create_test_negotiation_state()
    
    # Send advice request
    await websocket.send_json({
        'type': 'ASK_ADVICE',
        'state': state
    })
    
    # Verify market research performed
    assert mock_search_marketplaces.called
    assert mock_search_forums.called
    
    # Verify context built correctly
    sent_context = get_last_sent_context()
    assert 'market_research' in sent_context
    assert 'advisor_trigger' in sent_context
    
    # Verify response received
    response = await websocket.receive_json()
    assert response['type'] == 'ADVISOR_RESPONSE'
    assert 'audio' in response or 'text' in response
```

### AI Behavior Testing

**Challenge**: Testing AI responses is inherently non-deterministic

**Approach**:
- Test for presence of expected elements rather than exact content
- Use keyword/pattern matching for validation
- Test with controlled contexts that should trigger specific behaviors
- Focus on structural properties rather than exact wording

**Example AI Behavior Tests**:

```python
def test_ai_cites_sources_with_market_data():
    """Test that AI mentions sources when market data is provided"""
    context = build_context_with_market_data(
        marketplace_listings=[
            {'source': 'OLX', 'price': 45000, 'title': 'iPhone 12'}
        ]
    )
    
    response = await get_ai_advice(context)
    response_text = response['text'].lower()
    
    # Should mention the source
    assert 'olx' in response_text or 'marketplace' in response_text

def test_ai_warns_about_red_flags():
    """Test that AI warns about suspicious patterns"""
    context = build_context_with_messages([
        {'speaker': 'counterparty', 'text': 'Cash only, no returns, must decide now'}
    ])
    
    response = await get_ai_advice(context)
    response_text = response['text'].lower()
    
    # Should mention red flags or warnings
    assert any(word in response_text for word in ['warning', 'careful', 'red flag', 'suspicious'])
```

### Test Data Strategies

**Hypothesis Strategies for Domain Objects**:

```python
def message_strategy():
    return st.fixed_dictionaries({
        'speaker': st.sampled_from(['user', 'counterparty']),
        'text': st.text(min_size=1, max_size=500),
        'timestamp': st.datetimes().map(lambda dt: dt.isoformat())
    })

def listing_strategy():
    return st.fixed_dictionaries({
        'source': st.sampled_from(['OLX', 'Facebook', 'Craigslist']),
        'title': st.text(min_size=5, max_size=100),
        'price': st.floats(min_value=0, max_value=1000000, allow_nan=False),
        'condition': st.sampled_from(['new', 'like new', 'good', 'fair', 'poor']),
        'location': st.text(min_size=3, max_size=50),
        'url': st.text(min_size=10, max_size=200)
    })

def negotiation_state_strategy():
    return st.fixed_dictionaries({
        'item': st.text(min_size=1, max_size=100),
        'userPrice': st.floats(min_value=0, allow_nan=False),
        'counterpartyPrice': st.floats(min_value=0, allow_nan=False),
        'transcript': st.lists(message_strategy(), min_size=0, max_size=50)
    })
```

### Test Coverage Goals

- **Unit Test Coverage**: Minimum 80% code coverage for backend services
- **Property Test Coverage**: All 24 correctness properties implemented as property tests
- **Integration Test Coverage**: All major user flows covered
- **Edge Case Coverage**: All error conditions and edge cases from requirements

### Continuous Testing

- Run unit tests on every commit
- Run property tests (100 iterations) on every pull request
- Run integration tests in staging environment before deployment
- Monitor test execution time and optimize slow tests
- Track flaky tests and investigate root causes

