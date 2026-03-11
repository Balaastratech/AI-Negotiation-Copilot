import { useEffect, useCallback } from 'react';
import { useNegotiation } from './useNegotiation';
import { useNegotiationState } from './useNegotiationState';
import { VoiceFingerprint, identifySpeaker } from '../lib/voice-fingerprint';

/**
 * Integrated negotiation hook that combines:
 * - Old useNegotiation (WebSocket, audio streaming)
 * - New useNegotiationState (button-triggered state management)
 * - Voice fingerprinting for speaker identification
 * 
 * This hook bridges the old and new implementations up to task 5 completion.
 */
export function useIntegratedNegotiation(voiceFingerprint: VoiceFingerprint | null) {
  const negotiation = useNegotiation();
  const buttonState = useNegotiationState();

  // Sync transcript from old system to new state manager with speaker identification
  useEffect(() => {
    if (negotiation.state.transcript.length > 0) {
      const latestEntry = negotiation.state.transcript[negotiation.state.transcript.length - 1];
      
      // Map speaker labels from old system to new system
      let speaker: 'USER' | 'COUNTERPARTY';
      if (latestEntry.speaker === 'user') {
        speaker = 'USER';
      } else if (latestEntry.speaker === 'ai') {
        // AI responses are not added to button-triggered transcript
        return;
      } else {
        speaker = 'COUNTERPARTY';
      }

      // Add to button-triggered state manager
      buttonState.addTranscriptEntry(speaker, latestEntry.text);
      
      console.log(`[Speaker ID] ${speaker}: ${latestEntry.text}`);
    }
  }, [negotiation.state.transcript.length]);

  // Sync market data updates
  const handleMarketDataUpdate = useCallback((data: string) => {
    buttonState.updateMarketData(data);
  }, [buttonState]);

  // Handle AI state extraction updates
  const handleAIStateUpdate = useCallback((updates: any) => {
    buttonState.updateStateFromAI(updates);
  }, [buttonState]);

  // ------------- Web Speech API (Local Transcription Fallback) -------------
  // Since Gemini's input_transcription can be flaky or delayed over WebSocket,
  // we use the browser's native speech recognition to guarantee instant transcripts.
  
  useEffect(() => {
    if (!negotiation.state.isNegotiating) return;

    // Check for browser support
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn("Browser does not support SpeechRecognition. Transcription relies solely on backend.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    let finalTranscript = '';

    recognition.onresult = (event: any) => {
      let interimTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          const text = event.results[i][0].transcript.trim();
          if (text) {
            // Determine active speaker from buttonState or negotiation state
            // If manual speaker selection is in use, we could get it from buttonState context 
            // but for now we default to what the system thinks or 'USER'
            const activeSpeaker = 'USER'; // Can be improved to track active manual speaker
            
            console.log(`[Local Speech] ${activeSpeaker}: ${text}`);
            buttonState.addTranscriptEntry(activeSpeaker, text);
          }
        } else {
          interimTranscript += event.results[i][0].transcript;
        }
      }
    };

    recognition.onerror = (event: any) => {
      console.warn("Speech recognition error", event.error);
    };

    recognition.onend = () => {
      // Auto-restart if we are still negotiating
      if (negotiation.state.isNegotiating) {
        try {
          recognition.start();
        } catch (e) {
          console.warn("Could not restart speech recognition", e);
        }
      }
    };

    try {
      recognition.start();
      console.log("[Local Speech] Recognition started");
    } catch (e) {
      console.warn("Failed to start speech recognition", e);
    }

    return () => {
      try {
        recognition.stop();
      } catch (e) {}
    };
  }, [negotiation.state.isNegotiating, buttonState]);

  return {
    // Old system
    negotiation,
    
    // New button-triggered system
    buttonState: buttonState.state,
    validationErrors: buttonState.validationErrors,
    updateStateFromAI: handleAIStateUpdate,
    updateMarketData: handleMarketDataUpdate,
    
    // Voice fingerprint
    voiceFingerprint
  };
}
