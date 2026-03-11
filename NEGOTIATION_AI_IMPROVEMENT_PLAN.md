# Negotiation AI Improvement Plan

## Problem Statement
The AI currently gives random, unrealistic negotiation advice (e.g., "Try negotiating around 70,000") instead of:
- Gathering missing information (condition, storage, age)
- Researching real market data (OLX, Reddit, nearby sellers)
- Providing contextual, data-backed advice
- Guiding negotiation dynamically

## Root Causes

### 1. Generic Master Prompt
Current prompt is too simple:
```python
MASTER_NEGOTIATION_PROMPT = """You are a real-time negotiation advisor. Your job is to help users negotiate better deals.

IMPORTANT RULES:
1. When you see "🔔 ADVISOR_QUERY" - RESPOND IMMEDIATELY with audio advice
2. When you hear conversation audio - listen and wait
3. ALWAYS respond when asked - never stay silent
4. Keep responses brief (1-2 sentences)

Context: {context}

Remember: The user is waiting for your voice guidance. Respond to every ADVISOR_QUERY."""
```

### 2. Minimal Advisor Query
Current query only includes item name:
```python
return f"""🔔 ADVISOR_QUERY: The USER needs your advice RIGHT NOW 🔔

Based on the conversation you've been listening to about {item}, what should the USER say or do next to get a better deal?

RESPOND WITH AUDIO: Speak your advice out loud. Be specific and actionable based on what you've heard in the conversation so far."""
```

### 3. No Research Capability
AI has no access to web search or market data tools.

### 4. No Information Gathering Logic
AI doesn't know to identify missing critical information.

## Solution Architecture

### Phase 1: Enhanced Master Prompt (DRAFT)

**Design Principles:**
- Product-agnostic: Works for ANY item (phones, cars, furniture, etc.)
- AI decides what information matters based on product type
- AI adapts to conversation flow dynamically
- Teaches HOW to think, not WHAT to think

**Proposed Master Prompt:**

```python
MASTER_NEGOTIATION_PROMPT = """You are an expert negotiation advisor helping users get better deals in real-time conversations.

YOUR ROLE:
- You are listening to a live negotiation between the USER and a COUNTERPARTY
- The USER can hear you, the COUNTERPARTY cannot
- When you see "🔔 ADVISOR_QUERY", the USER is asking for your advice
- Provide strategic guidance to help the USER negotiate effectively

HOW TO ANALYZE THE SITUATION:
1. Understand the product being negotiated and what factors affect its value
2. Review the conversation to identify:
   - What information is already known
   - What critical information is missing
   - The negotiation dynamics (who has leverage, urgency, etc.)
   - Whether the counterparty has been cooperative or evasive

3. Determine what information would help the USER make a better decision:
   - For physical items: condition, age, authenticity, functionality
   - For services: scope, timeline, quality guarantees
   - For any product: market value, comparable alternatives, hidden costs
   - Adapt based on the specific product type

HOW TO PROVIDE ADVICE:

WHEN INFORMATION IS MISSING:
- Tell the USER what specific questions to ask the COUNTERPARTY
- Only suggest questions the counterparty can reasonably answer
- If the counterparty already said they don't know something, don't push for it again
- Adapt your strategy based on what information is available

WHEN YOU NEED MARKET DATA:
- Research current market prices for similar items
- Look for comparable listings on marketplaces (OLX, Facebook, etc.)
- Check discussion forums (Reddit, etc.) for price insights
- Compare based on condition, location, and other relevant factors
- Cite your sources when providing price guidance

WHEN GIVING NEGOTIATION ADVICE:
- Base recommendations on actual data, not random numbers
- Consider the conversation context and relationship dynamics
- Suggest specific tactics (counter-offers, walking away, etc.)
- Warn about red flags or potential issues
- Be direct and actionable

RESPONSE GUIDELINES:
- Speak naturally as if advising a friend
- Include important details, don't artificially cut information
- Be concise but complete
- Respond immediately when you see "🔔 ADVISOR_QUERY"
- Always provide value - never say "I don't know" without trying to help

Remember: You have access to web search and market data. Use it to provide informed, data-backed advice that helps the USER negotiate confidently.

Context: {context}
"""
```

**Key Features:**
✅ Product-agnostic (no hardcoded examples)
✅ AI decides what information matters
✅ Adapts to conversation flow
✅ Guides user on what to ask counterparty
✅ Researches market data independently
✅ Natural response length
✅ Strategic thinking framework

### Phase 2: Adaptive Context-Aware Query ✅ DECISIONS MADE

**Design Philosophy:** AI gets complete context and decides what's relevant, not rigid templates.

**Decision 1: Conversation History Strategy**
✅ **CHOSEN: Hybrid Approach (C)**
- Summarize old messages (1-N) with structured summary
- Provide full detail for last 10 messages
- AI has both historical context and recent precision

**Decision 2: Information Extraction**
✅ **CHOSEN: Hybrid (C)**
- Backend extracts basics: item, prices, known facts
- AI refines and adds: tactics, emotional tone, red flags, urgency, and more
- AI decides what additional patterns matter

**Decision 3: Summary Structure**
✅ **CHOSEN: Structured Summary (B)**
- Key facts discovered
- Key questions asked
- Key answers given
- Negotiation moves made

**Decision 4: Advanced Analysis**
✅ **AI Decides:** Negotiation tactics, emotional tone, red flags, counterparty urgency, and any other relevant patterns

**Implementation:**

```python
def build_adaptive_context(state: dict) -> dict:
    """Build complete negotiation context for AI awareness"""
    
    transcript = state.get('transcript', [])
    split_point = max(0, len(transcript) - 10)
    
    return {
        "negotiation_metadata": {
            "item": state.get('item'),
            "user_asking_price": state.get('userPrice'),
            "counterparty_offer": state.get('counterpartyPrice'),
            "total_messages": len(transcript)
        },
        
        "conversation_summary": {
            # Structured summary of messages 1 to N-10
            "key_facts": extract_facts(transcript[:split_point]),
            "questions_asked": extract_questions(transcript[:split_point]),
            "answers_given": extract_answers(transcript[:split_point]),
            "negotiation_moves": extract_moves(transcript[:split_point])
        },
        
        "recent_conversation": [
            # Full detail of last 10 messages
            {"speaker": msg['speaker'], "text": msg['text'], "timestamp": msg['timestamp']}
            for msg in transcript[-10:]
        ],
        
        "advisor_trigger": "🔔 USER needs your advice RIGHT NOW. Analyze the complete context and provide strategic guidance."
    }
```

**Key Features:**
✅ AI has full awareness of negotiation history
✅ Recent messages in full detail for immediate context
✅ Backend provides structure, AI provides intelligence
✅ Adaptive - AI decides what matters based on product/situation

### Phase 3: Web Search Integration ✅ DECISIONS MADE

**Decision 5: When to Research**
✅ **CHOSEN: AI Determines Need (B)**
- AI decides when market research is needed based on conversation context
- Not every advice request requires research
- AI can work with available information when appropriate
- More efficient and contextually aware

**Decision 6: Search Approach**
✅ **CHOSEN: Backend Pre-Search (B)**
- When user clicks "Ask AI", backend automatically searches for market data
- Pass search results to AI in the context
- Simpler implementation for current phase
- Prepares architecture for future Listener session

**Implementation:**

```python
async def handle_ask_advice(state: dict):
    """Handle user request for advice with market research"""
    
    # 1. Extract negotiation context
    item = state.get('item')
    user_price = state.get('userPrice')
    counterparty_price = state.get('counterpartyPrice')
    
    # 2. Backend performs market research
    search_results = await search_market_data(
        item=item,
        user_price=user_price,
        counterparty_price=counterparty_price
    )
    
    # 3. Build adaptive context with research results
    context = build_adaptive_context(
        state=state,
        search_results=search_results
    )
    
    # 4. Send to AI - AI decides if research is sufficient
    advice = await get_ai_advice(context)
    
    return advice

async def search_market_data(item: str, user_price: float, counterparty_price: float):
    """Search for market data on marketplaces and forums"""
    
    results = {
        "marketplace_listings": [],
        "forum_discussions": [],
        "price_range": None
    }
    
    # Search OLX, Facebook Marketplace, etc.
    results["marketplace_listings"] = await search_marketplaces(item)
    
    # Search Reddit, forums for price insights
    results["forum_discussions"] = await search_forums(item)
    
    # Calculate price range from results
    results["price_range"] = calculate_price_range(results)
    
    return results
```

**Key Features:**
✅ Backend handles search complexity
✅ AI receives structured research results
✅ AI can determine if more research needed
✅ Simple to implement and test
✅ Foundation for future Listener architecture

### Phase 4: Testing & Refinement
- Test with various negotiation scenarios
- Verify information gathering works
- Confirm market research is accurate
- Ensure advice is contextual and helpful

## Implementation Steps

### Step 1: Update Master Prompt (backend/app/services/master_prompt.py)
- Add detailed instructions for information gathering
- Include market research guidelines
- Define response patterns

### Step 2: Enhance Advisor Query (backend/app/services/gemini_client.py)
- Include full conversation transcript
- Add price information
- Provide clear task instructions

### Step 3: Add Web Search Capability
- Decide on approach (A, B, or C)
- Implement search integration
- Test search results quality

### Step 4: Update Frontend (if needed)
- Ensure all necessary state is passed in ASK_ADVICE
- Add UI indicators for research activity
- Handle longer response times

## Success Criteria

✅ AI identifies missing information and asks relevant questions
✅ AI performs market research and cites sources
✅ AI provides data-backed price recommendations
✅ AI gives contextual advice based on conversation flow
✅ AI warns about potential issues (condition, scams, etc.)
✅ Responses are natural and conversational, not scripted

## Future Enhancements (To Be Done Later)

### 1. Two-AI Summarizer System
Instead of backend creating structured summaries, use a dedicated AI:

**Architecture:**
- **Summarizer AI**: Analyzes old messages (1-N) and creates intelligent structured summary
- **Advisor AI**: Gets AI-generated summary + recent messages, provides advice
- **Benefits**: More intelligent summarization, better context compression, cleaner separation

**Why Later:**
- Current hybrid approach (backend extracts, AI refines) is simpler to implement
- Two-AI system requires additional API calls and complexity
- Can be added as optimization once basic system works

### 2. Dual Live Session Architecture (Listener + Advisor)
Parallel AI sessions for continuous research and instant advice:

**Architecture:**
```
Negotiation Audio 
  → [Listener Session] (Always listening, researching, analyzing)
      ↓ transcripts + research + insights
  → [FastAPI Bridge] (Manages both sessions, shared state)
      ↓ context injection
  → [Advisor Session] (Activated on-demand when user clicks "Ask AI")
```

**How It Works:**
- **Listener Session**: Continuous WebSocket connection
  - Transcribes conversation in real-time
  - Performs market research proactively as items/prices are mentioned
  - Identifies missing information, red flags, tactics
  - Builds rich context buffer
  
- **Backend Bridge**: Owns shared state
  - Maintains transcript buffer
  - Stores research results from Listener
  - Manages both WebSocket connections simultaneously
  
- **Advisor Session**: On-demand WebSocket connection
  - Activated when user clicks "Ask AI"
  - Receives pre-built context from Listener (including research)
  - Provides instant advice (no research delay)
  - Can request additional research if needed

**Benefits:**
- Zero latency for advice (research already done by Listener)
- Continuous context awareness
- Proactive information gathering
- Better user experience
- Listener does the heavy lifting (research, analysis)
- Advisor focuses on strategic advice

**Why Later:**
- Requires managing two simultaneous Gemini Live sessions
- More complex state management
- Higher API costs (two sessions running)
- Current single-session with backend pre-search is simpler to implement and test
- Need to validate single-session approach first

**Migration Path:**
1. Current: Backend pre-searches when user clicks "Ask AI"
2. Future: Listener session pre-searches continuously, Advisor uses cached results
3. Same search logic, just moved to Listener session

## Next Steps

1. ✅ Phase 2 decisions completed
2. ✅ Phase 3 decisions completed
3. Review Phase 1 Master Prompt updates
4. Implement Phase 1 (Enhanced Master Prompt)
5. Implement Phase 2 (Adaptive Context Query)
6. Implement Phase 3 (Web Search Integration)
7. Test and iterate
8. Implement Phase 4 (Testing & Refinement)
