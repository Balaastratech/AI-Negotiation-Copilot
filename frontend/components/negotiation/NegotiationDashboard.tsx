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
  onStartCopilot: () => void;
  onGetAdvice: () => void;
  onGetCommand: () => void;
  onUserAddressingAI: (active: boolean) => void;
  isAILoading: boolean;
  onSpeakerSelected?: (speaker: 'user' | 'counterparty') => void;
  currentSpeaker?: 'user' | 'counterparty' | null;
  responseMode?: 'advice' | 'command' | null;
  aiLiveTranscription?: string | null;
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
  onStartCopilot,
  onGetAdvice,
  onGetCommand,
  onUserAddressingAI,
  isAILoading,
  onSpeakerSelected,
  currentSpeaker,
  responseMode,
  aiLiveTranscription
}: NegotiationDashboardProps) {
  const [isAddressingAI, setIsAddressingAI] = React.useState(false);
  const longPressTimerRef = React.useRef<NodeJS.Timeout | null>(null);

  const handlePointerDown = React.useCallback(() => {
    console.log('[DEBUG] handlePointerDown called, copilotActive:', state.copilotActive);
    
    if (!state.copilotActive) {
      console.log('[DEBUG] Copilot not active, ignoring press');
      return;
    }
    
    console.log('[DEBUG] Starting 600ms timer for hold detection');
    longPressTimerRef.current = setTimeout(() => {
      console.log('[DEBUG] Hold threshold reached, activating AI');
      // Haptic feedback
      if (navigator.vibrate) {
        navigator.vibrate(30);
      }
      setIsAddressingAI(true);
      onUserAddressingAI(true);
    }, 600);
  }, [state.copilotActive, onUserAddressingAI]);

  const handlePointerEnd = React.useCallback(() => {
    console.log('[DEBUG] handlePointerEnd called, isAddressingAI:', isAddressingAI);
    
    if (longPressTimerRef.current) {
      clearTimeout(longPressTimerRef.current);
      longPressTimerRef.current = null;
    }
    
    if (isAddressingAI) {
      console.log('[DEBUG] Deactivating AI');
      setIsAddressingAI(false);
      onUserAddressingAI(false);
    }
  }, [isAddressingAI, onUserAddressingAI]);

  if (!state.consentGiven) {
    return <PrivacyConsent onAccept={onConsent} />;
  }

  return (
    <div 
      className="flex flex-col h-screen w-full bg-neutral-100 overflow-hidden"
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerEnd}
      onPointerCancel={handlePointerEnd}
      onMouseLeave={handlePointerEnd}
    >
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

      {/* Ask AI Buttons - Advice and Command options */}
      {state.isNegotiating && (
        <div className="fixed bottom-24 right-8 z-50">
          <AskAIButton
            onStartCopilot={onStartCopilot}
            onGetAdvice={onGetAdvice}
            onGetCommand={onGetCommand}
            isLoading={isAILoading}
            isDisabled={!state.isNegotiating}
            copilotActive={state.copilotActive}
            responseMode={responseMode}
          />
        </div>
      )}

      {/* AI Live Transcription - isolated display, not part of transcript */}
      {aiLiveTranscription && state.aiState === 'speaking' && (
        <div className="fixed bottom-36 left-1/2 transform -translate-x-1/2 z-40 max-w-lg w-full px-4 pointer-events-none">
          <div className="bg-neutral-900/85 text-white px-5 py-3 rounded-xl shadow-xl text-sm leading-relaxed">
            <span className="text-blue-400 font-medium text-xs uppercase tracking-wide block mb-1">AI</span>
            {aiLiveTranscription}
          </div>
        </div>
      )}

      {/* Addressing AI Indicator - shows when user is holding to speak to AI */}
      {isAddressingAI && (
        <div className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-50 pointer-events-none">
          <div className="bg-blue-600/90 text-white px-8 py-4 rounded-2xl shadow-2xl flex items-center gap-3 animate-pulse">
            <div className="w-3 h-3 bg-white rounded-full animate-ping"></div>
            <span className="font-semibold text-lg">Listening to you...</span>
          </div>
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
