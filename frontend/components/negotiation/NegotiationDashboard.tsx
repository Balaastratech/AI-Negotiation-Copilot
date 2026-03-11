import React from 'react';
import { NegotiationState } from '../../lib/types';
import { NegotiationState as ButtonTriggeredState, ValidationError } from '../../hooks/useNegotiationState';
import { VoiceFingerprint } from '../../lib/voice-fingerprint';
import { PrivacyConsent } from './PrivacyConsent';
import { VideoCapture } from './VideoCapture';
import { TranscriptPanel } from './TranscriptPanel';
import { StrategyPanel } from './StrategyPanel';
import { ControlBar } from './ControlBar';
import { AIStateIndicator } from './AIStateIndicator';
import { ValidationErrors } from './ValidationErrors';
import { NegotiationStateCard } from './NegotiationStateCard';
import { ResearchIndicator } from './ResearchIndicator';
import { AskAIButton } from './AskAIButton';
import { ManualSpeakerSelector } from './ManualSpeakerSelector';

interface NegotiationDashboardProps {
  state: NegotiationState;
  negotiationState: ButtonTriggeredState;
  validationErrors: ValidationError[];
  voiceFingerprint: VoiceFingerprint | null;
  onConsent: () => void;
  onToggleAudio: () => void;
  onToggleVision: () => void;
  onStartNegotiation: () => void;
  onEndNegotiation: () => void;
  onAskAI: () => void;
  isAILoading: boolean;
  onSpeakerSelected?: (speaker: 'user' | 'counterparty') => void;
  currentSpeaker?: 'user' | 'counterparty' | null;
}

export function NegotiationDashboard({
  state,
  negotiationState,
  validationErrors,
  voiceFingerprint,
  onConsent,
  onToggleAudio,
  onToggleVision,
  onStartNegotiation,
  onEndNegotiation,
  onAskAI,
  isAILoading,
  onSpeakerSelected,
  currentSpeaker
}: NegotiationDashboardProps) {
  if (!state.consentGiven) {
    return <PrivacyConsent onAccept={onConsent} />;
  }

  return (
    <div className="flex flex-col h-screen w-full bg-neutral-100 overflow-hidden">
      {/* AI State Indicator - shows listening/thinking/speaking */}
      <AIStateIndicator state={state.aiState} />

      {/* Manual Speaker Selector - only show when negotiation is active */}
      {state.isNegotiating && onSpeakerSelected && (
        <div className="px-4 pt-4">
          <ManualSpeakerSelector 
            onSpeakerSelected={onSpeakerSelected}
            currentSpeaker={currentSpeaker || null}
          />
        </div>
      )}

      {/* Research Indicator - shows when researching market data */}
      <ResearchIndicator 
        isResearching={negotiationState.isResearching} 
        progress={negotiationState.researchProgress} 
      />

      {/* Validation Errors - shows state validation issues */}
      {validationErrors.length > 0 && (
        <div className="px-6 pt-4">
          <ValidationErrors errors={validationErrors} />
        </div>
      )}

      {/* Voice Fingerprint Status */}
      {voiceFingerprint && (
        <div className="px-6 pt-2">
          <div className="text-xs text-green-600 flex items-center gap-2">
            <span>✓</span>
            <span>Voice fingerprint active ({voiceFingerprint.mean.length} coefficients)</span>
          </div>
        </div>
      )}

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

        {/* Right Column: Strategy Panel and Negotiation State */}
        <div className="flex-1 min-w-[500px] flex flex-col gap-6">
          <div className="flex-1 min-h-0">
            <StrategyPanel strategy={state.strategy} />
          </div>
          
          {/* Negotiation State Card - shows extracted state + listener status */}
          <div className="shrink-0">
            <NegotiationStateCard
              state={negotiationState}
              isDualModelActive={state.isNegotiating}
            />
          </div>
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

      {/* Ask AI Button - Floating button for advice */}
      {state.isNegotiating && (
        <div className="fixed bottom-24 right-8 z-50">
          <AskAIButton
            onAskAI={onAskAI}
            isLoading={isAILoading}
            isDisabled={!state.isNegotiating}
          />
        </div>
      )}

      {/* AI Degraded Notice overlay if applicable */}
      {state.aiDegraded && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-yellow-100 text-yellow-800 px-6 py-2 rounded-full shadow-md border border-yellow-300 flex items-center z-50 animate-bounce">
          <span className="font-semibold text-sm">Connection unstable. Operating in text-only fallback mode.</span>
        </div>
      )}
    </div>
  );
}
