"use client";

import React, { useState } from 'react';
import { NegotiationDashboard } from '../../components/negotiation/NegotiationDashboard';
import { INITIAL_NEGOTIATION_STATE, NegotiationState } from '../../lib/types';
import { MOCK_STRATEGY, MOCK_TRANSCRIPT } from '../../lib/mock-data';

export default function NegotiatePage() {
  const [state, setState] = useState<NegotiationState>(INITIAL_NEGOTIATION_STATE);

  // Handlers for UI actions
  const handleConsent = () => {
    setState(prev => ({ ...prev, consentGiven: true }));
  };

  const handleToggleAudio = () => {
    setState(prev => ({ ...prev, isAudioActive: !prev.isAudioActive }));
  };

  const handleToggleVision = () => {
    setState(prev => ({ ...prev, isVisionActive: !prev.isVisionActive }));
  };

  const handleEndNegotiation = () => {
    console.log("End Negotiation Clicked");
    setState(prev => ({ 
      ...prev, 
      isNegotiating: false,
      isConnected: false,
      isAudioActive: false,
      isVisionActive: false 
    }));
  };

  // Mock Data Loader for testing Phase 4 UI
  const loadMockData = () => {
    setState(prev => ({
      ...prev,
      transcript: MOCK_TRANSCRIPT,
      strategy: MOCK_STRATEGY,
      isNegotiating: true,
      isConnected: true
    }));
  };

  return (
    <div className="relative w-full h-screen bg-gray-100">
      <NegotiationDashboard 
        state={state}
        onConsent={handleConsent}
        onToggleAudio={handleToggleAudio}
        onToggleVision={handleToggleVision}
        onEndNegotiation={handleEndNegotiation}
      />

      {/* Temporary Mock Data Control (For Dev Only) */}
      {state.consentGiven && (
        <div className="absolute top-4 right-4 z-50">
          <button
            onClick={loadMockData}
            className="px-4 py-2 bg-purple-600 text-white font-semibold rounded shadow hover:bg-purple-700 transition"
          >
            Load Mock Data
          </button>
        </div>
      )}
    </div>
  );
}
