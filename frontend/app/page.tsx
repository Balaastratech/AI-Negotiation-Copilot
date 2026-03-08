"use client";

import { useEffect, useState } from 'react';
import { useNegotiation } from '@/hooks/useNegotiation';
import { NegotiationDashboard } from '@/components/negotiation/NegotiationDashboard';

export default function Home() {
  const {
    state,
    connect,
    grantConsent,
    startNegotiation,
    endNegotiation
  } = useNegotiation();

  // Local UI state – controls button label and mic/camera independently of
  // the backend-driven `state.isNegotiating` so the UI responds instantly.
  const [isSessionActive, setIsSessionActive] = useState(false);
  const [isAudioActive, setIsAudioActive] = useState(false);
  const [isVisionActive, setIsVisionActive] = useState(false);

  useEffect(() => {
    if (!state.isConnected) {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.hostname;
      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || `${protocol}//${host}:8000/ws`;
      connect(wsUrl).catch(console.error);
    }
  }, [connect, state.isConnected]);

  const handleConsent = () => {
    grantConsent('1.0', 'live');
  };

  // Start: flip button immediately, turn on mic + camera, then send to backend
  const handleStartNegotiation = () => {
    setIsSessionActive(true);
    setIsAudioActive(true);
    setIsVisionActive(true);

    startNegotiation('I am buying a used laptop at a market. The seller is asking $500.')
      .catch(err => {
        console.error("Failed to start negotiation:", err);
        // Roll back UI on failure
        setIsSessionActive(false);
        setIsAudioActive(false);
        setIsVisionActive(false);
      });
  };

  // End: flip button immediately, stop mic + camera, then send to backend
  const handleEndNegotiation = () => {
    setIsSessionActive(false);
    setIsAudioActive(false);
    setIsVisionActive(false);

    endNegotiation(null, null);
  };

  const handleToggleAudio = () => {
    setIsAudioActive(prev => !prev);
  };

  const handleToggleVision = () => {
    setIsVisionActive(prev => !prev);
  };

  const dashboardState = {
    ...state,
    // Override backend isNegotiating with local flag so the button responds instantly
    isNegotiating: isSessionActive,
    isAudioActive,
    isVisionActive,
  };

  return (
    <main className="h-screen w-screen overflow-hidden text-neutral-900 bg-neutral-100 font-sans">
      <NegotiationDashboard
        state={dashboardState}
        onConsent={handleConsent}
        onToggleAudio={handleToggleAudio}
        onToggleVision={handleToggleVision}
        onStartNegotiation={handleStartNegotiation}
        onEndNegotiation={handleEndNegotiation}
      />
    </main>
  );
}
