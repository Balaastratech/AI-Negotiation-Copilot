# AI Negotiation Copilot

## What This Is

AI Negotiation Copilot is a multimodal real-time negotiation assistant designed to help users obtain better prices, terms, or agreements during real-world negotiations. Built specifically for the Live Agent category, it observes the negotiation environment through visual input, listens to the conversation through voice input, and generates structured negotiation intelligence through text and spoken guidance.

## Core Value

Continuously gather information from the environment and guide the user through the negotiation process in real-time to secure better deals, acting strictly as a copilot without ever negotiating autonomously on their behalf.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

<!-- Current scope. Building toward these. -->

- [ ] Multimodal environment observation (Vision for reading price boards, product names, contracts)
- [ ] Voice interaction and conversation monitoring via Gemini Live API
- [ ] Real-time market context analysis and price comparison via Google Cloud integrations
- [ ] Dynamic negotiation strategy generation (opening approach, counteroffers, logical justifications)
- [ ] Adaptive strategy adjustment based on live conversation analysis
- [ ] Deal closure tracking, savings calculation, and effectiveness summary
- [ ] Privacy & Audio Control toggle for strict legal compliance during audio capture
- [ ] Negotiation Dashboard UI comprising visual capture area, strategy info, conversation transcript, and recommendation panel

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Autonomous negotiation on behalf of the user — The assistant acts strictly as a copilot, leaving the user as the primary participant in control.

## Context

- Intended to support negotiations in everyday situations: purchasing products, negotiating hotel prices, bargaining in marketplaces, service fees, freelance contracts, salary, real estate, and business procurement.
- Transforms visual information from the real world into structured data and monitors live conversation dialogue, handling natural interruptions and conversational barge-ins gracefully.

## Constraints

- **Platform**: Hosted entirely on Google Cloud — Required by architectural definition.
- **Technology**: Built on Gemini Live API — Essential for low-latency multimodal interaction (Vision, Voice, Text).
- **Compliance**: Must include explicit consent toggles for microphone monitoring to ensure legal compliance and protect participant privacy.

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Multimodal architecture (Vision + Voice + Text) | Necessary to understand both the physical/digital environment and active conversation simultaneously. | — Pending |
| User-in-the-loop operation | Prevents liability from autonomous agents and maintains user control and agency in sensitive negotiations. | — Pending |

---
*Last updated: 2026-03-06 after initialization*
