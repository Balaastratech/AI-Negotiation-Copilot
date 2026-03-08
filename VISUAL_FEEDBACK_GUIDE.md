# Visual Feedback Guide - What Users Will See

## The AI State Indicator

A floating badge appears at the top-center of the screen during active sessions:

```
┌─────────────────────────────────────────────────────────┐
│                    Top of Screen                        │
│                                                         │
│         ┌──────────────────────────────┐               │
│         │  🎤  Listening...            │  ← Blue badge │
│         │     AI is listening to you   │               │
│         └──────────────────────────────┘               │
│                                                         │
│  [Rest of the negotiation interface below]             │
└─────────────────────────────────────────────────────────┘
```

## State Transitions

### 1. LISTENING STATE (Blue)
```
┌──────────────────────────────────┐
│  🎤  Listening...                │  Blue background
│     AI is listening to you speak │  Pulsing microphone icon
└──────────────────────────────────┘
```
**When shown:**
- Session just started
- User is speaking
- AI finished responding and ready for next input

**What it means:**
- Microphone is active
- AI is receiving your audio
- You can speak freely

---

### 2. THINKING STATE (Purple)
```
┌──────────────────────────────────────────┐
│  🧠  Processing...                       │  Purple background
│     AI is analyzing and preparing response│  Pulsing brain icon
└──────────────────────────────────────────┘
```
**When shown:**
- 1.5 seconds after you stop speaking
- During the 10-20 second Gemini processing time

**What it means:**
- AI detected you finished speaking
- Processing your input with Gemini
- Preparing a response
- **This explains the delay!**

---

### 3. SPEAKING STATE (Green)
```
┌──────────────────────────────────┐
│  🔊  Speaking...                 │  Green background
│     AI is responding             │  Pulsing speaker icon
└──────────────────────────────────┘
```
**When shown:**
- AI starts delivering audio response
- While AI is talking

**What it means:**
- AI is speaking to you
- Audio is playing
- Listen to the response

---

## Visual Design Details

### Colors
- **Blue (#3B82F6)**: Listening - calm, receptive
- **Purple (#A855F7)**: Thinking - processing, intelligent
- **Green (#22C55E)**: Speaking - active, delivering

### Animation
- Pulsing ring around icon (subtle, not distracting)
- Smooth fade transitions between states
- Always visible but not obtrusive

### Position
- Fixed at top-center of screen
- Above all other content (z-index: 50)
- Doesn't block important UI elements

### Typography
- Bold state name (e.g., "Listening...")
- Smaller descriptive text below
- High contrast for readability

## Example Conversation Flow

```
Time    State        What User Sees
────────────────────────────────────────────────────────────
0:00    LISTENING    🎤 Listening...
                     AI is listening to you speak

0:02    LISTENING    [User speaks: "I want to buy this laptop"]
                     🎤 Listening...

0:05    THINKING     [User stops speaking]
                     🧠 Processing...
                     AI is analyzing and preparing response

0:18    SPEAKING     [AI starts responding]
                     🔊 Speaking...
                     AI is responding

0:25    LISTENING    [AI finishes]
                     🎤 Listening...
                     AI is listening to you speak

0:27    LISTENING    [User speaks: "What's your best price?"]
                     🎤 Listening...

0:30    THINKING     [User stops speaking]
                     🧠 Processing...
                     AI is analyzing and preparing response

0:45    SPEAKING     [AI responds]
                     🔊 Speaking...
                     AI is responding
```

## Benefits for User Experience

### 1. Reduces Anxiety
- Users know the system is working
- No wondering "Is it broken?"
- Clear feedback at every stage

### 2. Sets Expectations
- "Processing..." explains the 10-20 second delay
- Users understand AI needs time to think
- Reduces perceived wait time

### 3. Guides Interaction
- Clear when to speak (Listening)
- Clear when to wait (Thinking/Speaking)
- Natural conversation flow

### 4. Professional Polish
- Modern, clean design
- Smooth animations
- Attention to detail

## Technical Notes

### Silence Detection
- Uses RMS (Root Mean Square) energy calculation
- Threshold: 500 (adjustable for sensitivity)
- 1.5 second silence triggers "Thinking" state

### State Management
- React state managed via useReducer
- WebSocket messages trigger state changes
- Client-side silence detection for "Thinking"
- Server-side signals for "Speaking"

### Performance
- Lightweight component
- No impact on audio processing
- Efficient state updates

## Customization

If you need to adjust the behavior:

**Change silence threshold:**
```typescript
// frontend/lib/audio-worklet-manager.ts
private readonly SILENCE_THRESHOLD_MS = 1500; // Increase for longer wait
```

**Change speech detection sensitivity:**
```typescript
// frontend/lib/audio-worklet-manager.ts
return rms > 500; // Lower = more sensitive, Higher = less sensitive
```

**Change colors:**
```typescript
// frontend/components/negotiation/AIStateIndicator.tsx
listening: { bgColor: 'bg-blue-500', ... }
thinking: { bgColor: 'bg-purple-500', ... }
speaking: { bgColor: 'bg-green-500', ... }
```

## Accessibility

- High contrast colors for visibility
- Clear text descriptions
- Icon + text for redundancy
- Smooth animations (not jarring)
- Respects reduced motion preferences (via Tailwind)
