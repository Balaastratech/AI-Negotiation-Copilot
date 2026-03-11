/**
 * Hook for audio capture with speaker identification.
 * 
 * Integrates voice fingerprinting into the audio pipeline to automatically
 * label audio chunks as USER or COUNTERPARTY before sending to backend.
 */

import { useRef, useCallback } from 'react';
import { AudioProcessorWithSpeakerID, LabeledAudioChunk } from '../lib/audio-processor-with-speaker-id';
import { VoiceFingerprint } from '../lib/voice-fingerprint';

export function useAudioWithSpeakerID(voiceFingerprint: VoiceFingerprint | null) {
  const processorRef = useRef<AudioProcessorWithSpeakerID>(new AudioProcessorWithSpeakerID());

  // Set voice fingerprint when it becomes available
  useCallback(() => {
    if (voiceFingerprint && !processorRef.current.isReady()) {
      processorRef.current.setVoiceFingerprint(voiceFingerprint);
    }
  }, [voiceFingerprint])();

  /**
   * Process an audio chunk and identify the speaker.
   * 
   * @param audioChunk - Raw audio data from microphone
   * @returns Labeled audio chunk with speaker identification
   */
  const processAudioChunk = useCallback((audioChunk: ArrayBuffer): LabeledAudioChunk => {
    return processorRef.current.processChunk(audioChunk);
  }, []);

  /**
   * Check if speaker identification is ready.
   */
  const isReady = useCallback((): boolean => {
    return processorRef.current.isReady();
  }, []);

  return {
    processAudioChunk,
    isReady
  };
}
