"use client";

import { useEffect, useState, useRef, useCallback } from 'react';
import { useNegotiation } from '@/hooks/useNegotiation';
import { useNegotiationState } from '@/hooks/useNegotiationState';
import { useAskAI } from '@/hooks/useAskAI';
import { NegotiationDashboard } from '@/components/negotiation/NegotiationDashboard';

// ─── Main Page ─────────────────────────────────────────────────────────────────
export default function Home() {
    const {
        state,
        connect,
        grantConsent,
        startNegotiation,
        endNegotiation,
        setManualSpeaker,
        startCopilot,
        setUserAddressingAI,
        websocket,
        audioManager,
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

  const [currentSpeaker, setCurrentSpeaker] = useState<'user' | 'counterparty' | null>(null);


  const [isSessionActive, setIsSessionActive] = useState(false);
  const [isAudioActive, setIsAudioActive] = useState(false);
  const [isVisionActive, setIsVisionActive] = useState(false);

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

    window.addEventListener('negotiation-transcript', handleTranscript as EventListener);
    return () => window.removeEventListener('negotiation-transcript', handleTranscript as EventListener);
  }, [addTranscriptEntry]);

  // Listen for STATE_UPDATE, RESEARCH_STARTED, RESEARCH_COMPLETE, and CONTEXT_UPDATE from backend
  useEffect(() => {
    const handleStateUpdate = (event: CustomEvent) => updateStateFromAI(event.detail);
    
    const handleResearchStarted = (event: CustomEvent) => {
      setResearchState(true, `Researching market for ${event.detail.query}...`);
    };
    
    const handleResearchComplete = (event: CustomEvent) => {
      if (event.detail.market_data) updateMarketData(event.detail.market_data);
      setResearchState(false);
    };
    
    const handleContextUpdate = (event: CustomEvent) => {
      const detail = event.detail as any;
      if (detail) updateStateFromAI(detail);
    };
    
    window.addEventListener('negotiation-state-update', handleStateUpdate as EventListener);
    window.addEventListener('market-research-started', handleResearchStarted as EventListener);
    window.addEventListener('market-research-complete', handleResearchComplete as EventListener);
    window.addEventListener('negotiation-context-update', handleContextUpdate as EventListener);
    
    return () => {
      window.removeEventListener('negotiation-state-update', handleStateUpdate as EventListener);
      window.removeEventListener('market-research-started', handleResearchStarted as EventListener);
      window.removeEventListener('market-research-complete', handleResearchComplete as EventListener);
      window.removeEventListener('negotiation-context-update', handleContextUpdate as EventListener);
    };
  }, [updateStateFromAI, updateMarketData, setResearchState]);

  const handleConsent = () => grantConsent('1.0', 'live');

  const handleStartNegotiation = useCallback(() => {
    setIsSessionActive(true);
    setIsAudioActive(true);
    startNegotiation('', {}).catch(err => {
      console.error('Failed to start negotiation:', err);
      setIsSessionActive(false);
      setIsAudioActive(false);
    });
  }, [startNegotiation]);

  const handleEndNegotiation = () => {
    setIsSessionActive(false);
    setIsAudioActive(false);
    setIsVisionActive(false);
    endNegotiation(null, null);
  };

  const handleToggleAudio = () => setIsAudioActive(prev => !prev);
  const handleToggleVision = () => setIsVisionActive(prev => !prev);

  const handleGetAdvice = () => {
    if (!websocket || !websocket.isConnected) return;
    websocket.sendControl('SET_RESPONSE_MODE', { mode: 'advice' });
  };

  const handleGetCommand = () => {
    if (!websocket || !websocket.isConnected) return;
    websocket.sendControl('SET_RESPONSE_MODE', { mode: 'command' });
  };

  const handleSpeakerSelected = (speaker: 'user' | 'counterparty') => {
    setCurrentSpeaker(speaker);
    setManualSpeaker(speaker);
  };

  const dashboardState = { ...state, isNegotiating: isSessionActive, isAudioActive, isVisionActive };

  return (
    <main className="h-screen w-screen overflow-hidden text-neutral-900 bg-neutral-100 font-sans">
      <NegotiationDashboard
        state={dashboardState}
        negotiationState={negotiationState}
        validationErrors={validationErrors}
        onConsent={handleConsent}
        onToggleAudio={handleToggleAudio}
        onToggleVision={handleToggleVision}
        onStartNegotiation={handleStartNegotiation}
        onEndNegotiation={handleEndNegotiation}
        onStartCopilot={startCopilot}
        onGetAdvice={handleGetAdvice}
        onGetCommand={handleGetCommand}
        onUserAddressingAI={setUserAddressingAI}
        isAILoading={isAILoading}
        onSpeakerSelected={handleSpeakerSelected}
        currentSpeaker={currentSpeaker}
        responseMode={state.responseMode}
        aiLiveTranscription={state.aiLiveTranscription}
        liveTranscript={state.transcript.slice(-6)}
      />
    </main>
  );
}
