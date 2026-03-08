import React from 'react';
import { NegotiationState } from '../../lib/types';
import { PrivacyConsent } from './PrivacyConsent';
import { VideoCapture } from './VideoCapture';
import { TranscriptPanel } from './TranscriptPanel';
import { StrategyPanel } from './StrategyPanel';
import { ControlBar } from './ControlBar';
import { AIStateIndicator } from './AIStateIndicator';

interface NegotiationDashboardProps {
  state: NegotiationState;
  onConsent: () => void;
  onToggleAudio: () => void;
  onToggleVision: () => void;
  onStartNegotiation: () => void;
  onEndNegotiation: () => void;
}

export function NegotiationDashboard({
  state,
  onConsent,
  onToggleAudio,
  onToggleVision,
  onStartNegotiation,
  onEndNegotiation
}: NegotiationDashboardProps) {
  if (!state.consentGiven) {
    return <PrivacyConsent onAccept={onConsent} />;
  }

  return (
    <div className="flex flex-col h-screen w-full bg-neutral-100 overflow-hidden">
      {/* AI State Indicator - shows listening/thinking/speaking */}
      <AIStateIndicator state={state.aiState} />

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden p-6 gap-6">

        {/* Left Column: Video and Transcript */}
        <div className="w-1/3 flex flex-col gap-6 min-w-[350px]">
          {/* Video Feed */}
          <div className="shrink-0 rounded-xl overflow-hidden shadow-sm bg-black border border-neutral-300 h-64">
            <VideoCapture
              isActive={state.isVisionActive}
              onToggle={onToggleVision}
            />
          </div>

          {/* Transcript Panel */}
          <div className="flex-1 min-h-0">
            <TranscriptPanel entries={state.transcript} />
          </div>
        </div>

        {/* Right Column: Strategy Panel */}
        <div className="flex-1 min-w-[500px]">
          <StrategyPanel strategy={state.strategy} />
        </div>

      </div>

      {/* Bottom Control Bar */}
      <div className="shrink-0 bg-white">
        <ControlBar
          isAudioActive={state.isAudioActive}
          isVisionActive={state.isVisionActive}
          isNegotiating={state.isNegotiating}
          onToggleAudio={onToggleAudio}
          onToggleVision={onToggleVision}
          onStartNegotiation={onStartNegotiation}
          onEndNegotiation={onEndNegotiation}
        />
      </div>

      {/* AI Degraded Notice overlay if applicable */}
      {state.aiDegraded && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-yellow-100 text-yellow-800 px-6 py-2 rounded-full shadow-md border border-yellow-300 flex items-center z-50 animate-bounce">
          <span className="font-semibold text-sm">Connection unstable. Operating in text-only fallback mode.</span>
        </div>
      )}
    </div>
  );
}
