"use client";

import { useEffect, useState, useRef, useCallback } from 'react';
import { useNegotiation } from '@/hooks/useNegotiation';
import { useNegotiationState } from '@/hooks/useNegotiationState';
import { useAudioWithSpeakerID } from '@/hooks/useAudioWithSpeakerID';
import { useAskAI } from '@/hooks/useAskAI';
import { NegotiationDashboard } from '@/components/negotiation/NegotiationDashboard';
import VoiceEnrollmentScreen from '@/components/enrollment/VoiceEnrollmentScreen';
import { VoiceFingerprint } from '@/lib/voice-fingerprint';

// ─── Setup Dialog ─────────────────────────────────────────────────────────────
// Collects minimum info before session so the ADVISOR_QUERY has real context.
interface SetupFormData {
  item: string;
  target_price: string;
  max_price: string;
  context: string;
}

function SetupDialog({ onStart }: { onStart: (data: SetupFormData) => void }) {
  const [form, setForm] = useState<SetupFormData>({
    item: '',
    target_price: '',
    max_price: '',
    context: '',
  });

  const handle = (field: keyof SetupFormData) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm(prev => ({ ...prev, [field]: e.target.value }));

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.item.trim()) return;
    onStart(form);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <form onSubmit={submit} className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md mx-4 space-y-5">
        <div>
          <h2 className="text-2xl font-bold text-neutral-900">Start Negotiation</h2>
          <p className="text-sm text-neutral-500 mt-1">Tell the AI what you're negotiating so it can give you targeted advice.</p>
        </div>

        <div className="space-y-1">
          <label className="text-sm font-medium text-neutral-700">What are you buying? *</label>
          <input
            value={form.item}
            onChange={handle('item')}
            placeholder="e.g. Used MacBook Pro 2020"
            required
            className="w-full border border-neutral-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-sm font-medium text-neutral-700">Your target price</label>
            <input
              type="number"
              value={form.target_price}
              onChange={handle('target_price')}
              placeholder="e.g. 40000"
              className="w-full border border-neutral-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium text-neutral-700">Your max price</label>
            <input
              type="number"
              value={form.max_price}
              onChange={handle('max_price')}
              placeholder="e.g. 45000"
              className="w-full border border-neutral-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-sm font-medium text-neutral-700">Extra context (optional)</label>
          <textarea
            value={form.context}
            onChange={handle('context')}
            placeholder="e.g. Buying from a local marketplace, seller seems motivated to sell quickly"
            rows={3}
            className="w-full border border-neutral-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>

        <button
          type="submit"
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-xl transition-colors shadow-lg shadow-blue-600/30"
        >
          Start Session →
        </button>
      </form>
    </div>
  );
}

// ─── Main Page ─────────────────────────────────────────────────────────────────
export default function Home() {
  const {
    state,
    connect,
    grantConsent,
    setVoiceprint,
    startNegotiation,
    endNegotiation,
    setManualSpeaker,
    websocket
  } = useNegotiation();

  const {
    state: negotiationState,
    validationErrors,
    addTranscriptEntry,
    updateStateFromAI,
    updateMarketData,
    setResearchState,
    updateStateFromAI: updateFromSetup,
  } = useNegotiationState();

  const { askAI, isLoading: isAILoading, clearLoading } = useAskAI(
    negotiationState,
    websocket,
    setResearchState
  );

  const [voiceFingerprint, setVoiceFingerprint] = useState<VoiceFingerprint | null>(null);
  const [enrollmentComplete, setEnrollmentComplete] = useState(true);
  const [currentSpeaker, setCurrentSpeaker] = useState<'user' | 'counterparty' | null>(null);

  const { processAudioChunk, isReady: isSpeakerIDReady } = useAudioWithSpeakerID(voiceFingerprint);

  const [isSessionActive, setIsSessionActive] = useState(false);
  const [isAudioActive, setIsAudioActive] = useState(false);
  const [isVisionActive, setIsVisionActive] = useState(false);
  const [showSetup, setShowSetup] = useState(false);
  const [pendingSetup, setPendingSetup] = useState<SetupFormData | null>(null);

  const lastSpeakerRef = useRef<'USER' | 'COUNTERPARTY' | null>(null);

  // Connect to WebSocket on mount
  useEffect(() => {
    if (!state.isConnected) {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.hostname;
      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || `${protocol}//${host}:8000/ws`;
      connect(wsUrl).catch(console.error);
    }
  }, [connect, state.isConnected]);

  // Clear AI loading state when AI responds
  useEffect(() => {
    if (state.aiState === 'thinking' || state.aiState === 'speaking') {
      clearLoading();
    }
  }, [state.aiState, clearLoading]);

  // Wire TRANSCRIPT_UPDATE → negotiationState so ADVISOR_QUERY has conversation history
  useEffect(() => {
    const handleTranscript = (event: CustomEvent) => {
      const entry = event.detail as { speaker?: string; text?: string; transcript?: string };
      const text = entry.text || entry.transcript || '';
      if (!text.trim()) return;

      const rawSpeaker = (entry.speaker || '').toUpperCase();
      const speaker: 'USER' | 'COUNTERPARTY' =
        rawSpeaker === 'USER' ? 'USER' : 'COUNTERPARTY';
      addTranscriptEntry(speaker, text);
    };

    // The useNegotiation hook dispatches TRANSCRIPT_UPDATE via window events
    window.addEventListener('negotiation-transcript', handleTranscript as EventListener);

    return () => {
      window.removeEventListener('negotiation-transcript', handleTranscript as EventListener);
    };
  }, [addTranscriptEntry]);

  // Listen for STATE_UPDATE, RESEARCH_COMPLETE, and CONTEXT_UPDATE from backend
  useEffect(() => {
    const handleStateUpdate = (event: CustomEvent) => updateStateFromAI(event.detail);
    const handleResearchComplete = (event: CustomEvent) => {
      if (event.detail.results) updateMarketData(event.detail.results);
    };
    const handleContextUpdate = (event: CustomEvent) => {
      // ListenerAgent sent extracted context — merge into negotiation state
      const detail = event.detail as any;
      if (detail) {
        updateStateFromAI(detail);
      }
    };
    window.addEventListener('negotiation-state-update', handleStateUpdate as EventListener);
    window.addEventListener('market-research-complete', handleResearchComplete as EventListener);
    window.addEventListener('negotiation-context-update', handleContextUpdate as EventListener);
    return () => {
      window.removeEventListener('negotiation-state-update', handleStateUpdate as EventListener);
      window.removeEventListener('market-research-complete', handleResearchComplete as EventListener);
      window.removeEventListener('negotiation-context-update', handleContextUpdate as EventListener);
    };
  }, [updateStateFromAI, updateMarketData]);

  const handleConsent = () => grantConsent('1.0', 'live');

  // Show setup dialog when user clicks Start Session
  const requestStart = useCallback(() => setShowSetup(true), []);

  const handleSetupComplete = useCallback((data: SetupFormData) => {
    setShowSetup(false);
    setPendingSetup(data);

    // Pre-populate negotiation state so ADVISOR_QUERY has real context immediately
    updateFromSetup({
      item: data.item,
      target_price: data.target_price ? Number(data.target_price) : 0,
      max_price: data.max_price ? Number(data.max_price) : 0,
    });

    setIsSessionActive(true);
    setIsAudioActive(true);

    // Build a rich context string for the Gemini system prompt
    const contextParts: string[] = [];
    contextParts.push(`Item being negotiated: ${data.item}`);
    if (data.target_price) contextParts.push(`User's target price: ${data.target_price}`);
    if (data.max_price) contextParts.push(`User's maximum price: ${data.max_price}`);
    if (data.context.trim()) contextParts.push(`Additional context: ${data.context}`);
    const contextStr = contextParts.join('\n');

    // Structured user_context for the ListenerAgent's build_advisor_query()
    const userContext = {
      item: data.item,
      target_price: data.target_price ? Number(data.target_price) : null,
      max_price: data.max_price ? Number(data.max_price) : null,
      extra_context: data.context || null,
    };

    startNegotiation(contextStr, userContext).catch(err => {
      console.error('Failed to start negotiation:', err);
      setIsSessionActive(false);
      setIsAudioActive(false);
    });
  }, [updateFromSetup, startNegotiation]);

  const handleEndNegotiation = () => {
    setIsSessionActive(false);
    setIsAudioActive(false);
    setIsVisionActive(false);
    endNegotiation(null, null);
  };

  const handleToggleAudio = () => setIsAudioActive(prev => !prev);
  const handleToggleVision = () => setIsVisionActive(prev => !prev);

  const handleSpeakerSelected = (speaker: 'user' | 'counterparty') => {
    setCurrentSpeaker(speaker);
    setManualSpeaker(speaker);
  };

  const dashboardState = { ...state, isNegotiating: isSessionActive, isAudioActive, isVisionActive };

  if (!enrollmentComplete) {
    return (
      <VoiceEnrollmentScreen
        onEnrollmentComplete={(fp: VoiceFingerprint) => {
          setVoiceFingerprint(fp);
          setVoiceprint(fp);
          setEnrollmentComplete(true);
        }}
        onError={() => setEnrollmentComplete(true)}
      />
    );
  }

  return (
    <main className="h-screen w-screen overflow-hidden text-neutral-900 bg-neutral-100 font-sans">
      {showSetup && <SetupDialog onStart={handleSetupComplete} />}

      <NegotiationDashboard
        state={dashboardState}
        negotiationState={negotiationState}
        validationErrors={validationErrors}
        voiceFingerprint={voiceFingerprint}
        onConsent={handleConsent}
        onToggleAudio={handleToggleAudio}
        onToggleVision={handleToggleVision}
        onStartNegotiation={requestStart}
        onEndNegotiation={handleEndNegotiation}
        onAskAI={askAI}
        isAILoading={isAILoading}
        onSpeakerSelected={handleSpeakerSelected}
        currentSpeaker={currentSpeaker}
      />
    </main>
  );
}
