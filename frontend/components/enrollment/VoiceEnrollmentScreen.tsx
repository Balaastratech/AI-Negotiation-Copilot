'use client';

import { useState, useEffect, useCallback } from 'react';
import { enrollUserVoice, VoiceFingerprint } from '@/lib/voice-fingerprint';

/**
 * Voice Enrollment Screen Component
 * 
 * Provides a guided voice enrollment experience where users record 3 seconds
 * of audio for voice fingerprinting. The component displays clear visual feedback
 * at each step of the enrollment process.
 * 
 * Requirements:
 * - 12.1: Display "Voice Setup" screen on app launch
 * - 12.2: Show "Speak for 3 seconds..." instruction
 * - 12.3: Display red recording indicator dot
 * - 12.4: Show countdown timer (3...2...1)
 * - 12.5: Display "Processing..." spinner
 * - 12.6: Show "✓ Voice captured!" confirmation
 * - 12.7: Auto-transition to negotiation screen within 1 second
 * - 12.8: Provide clear visual feedback at each step
 */

/**
 * Enrollment state machine states
 */
type EnrollmentState = 
  | 'ready'       // Initial state, preparing to record
  | 'recording'   // Actively recording user's voice
  | 'processing'  // Extracting voice fingerprint
  | 'success'     // Enrollment successful
  | 'error';      // Enrollment failed

/**
 * UI state for enrollment screen
 */
interface EnrollmentUIState {
  state: EnrollmentState;
  countdown: number | null;
  errorMessage: string | null;
}

/**
 * Component props
 */
interface VoiceEnrollmentScreenProps {
  /** Callback when enrollment completes successfully */
  onEnrollmentComplete: (voiceprint: VoiceFingerprint) => void;
  
  /** Callback when enrollment fails */
  onError: (error: Error) => void;
}

/**
 * VoiceEnrollmentScreen Component
 * 
 * Guides users through voice enrollment with visual feedback:
 * 1. Auto-starts recording on mount
 * 2. Shows countdown (3, 2, 1) with red recording dot
 * 3. Displays processing spinner
 * 4. Shows success confirmation
 * 5. Auto-transitions to negotiation screen
 * 
 * Validates: Requirements 12.1-12.8
 */
export default function VoiceEnrollmentScreen({ 
  onEnrollmentComplete, 
  onError 
}: VoiceEnrollmentScreenProps) {
  const [uiState, setUIState] = useState<EnrollmentUIState>({
    state: 'ready',
    countdown: null,
    errorMessage: null
  });

  /**
   * Start recording user's voice for enrollment.
   * 
   * Process:
   * 1. Request microphone access
   * 2. Start recording with countdown
   * 3. Collect audio for 3 seconds
   * 4. Process enrollment
   * 
   * Validates: Requirements 12.2, 12.3, 12.4
   */
  const startRecording = useCallback(async () => {
    try {
      // Request microphone access with optimal settings for voice
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      
      // Start recording with countdown (Requirement 12.4)
      setUIState({ state: 'recording', countdown: 10, errorMessage: null });
      
      // Set up audio processing
      const audioContext = new AudioContext({ sampleRate: 16000 });
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      
      // Collect audio chunks
      const chunks: Float32Array[] = [];
      
      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        chunks.push(new Float32Array(inputData));
      };
      
      source.connect(processor);
      processor.connect(audioContext.destination);
      
      // Countdown timer (Requirement 12.4) - 10 seconds for better accuracy
      let countdown = 10;
      const countdownInterval = setInterval(() => {
        countdown--;
        setUIState(prev => ({ ...prev, countdown }));
        
        if (countdown === 0) {
          clearInterval(countdownInterval);
        }
      }, 1000);
      
      // Stop recording after 10 seconds (increased for better voice fingerprint)
      setTimeout(async () => {
        processor.disconnect();
        source.disconnect();
        stream.getTracks().forEach(track => track.stop());
        await audioContext.close();
        
        // Process the enrollment
        await processEnrollment(chunks);
      }, 10000);
      
    } catch (error) {
      console.error('Microphone access error:', error);
      setUIState({ 
        state: 'error', 
        countdown: null, 
        errorMessage: 'Microphone access denied. Please allow microphone access and try again.' 
      });
      onError(error as Error);
    }
  }, [onError]);

  /**
   * Process enrollment audio to create voice fingerprint.
   * 
   * Process:
   * 1. Concatenate all audio chunks
   * 2. Extract voice fingerprint using MFCC
   * 3. Show success confirmation
   * 4. Auto-transition after 1 second
   * 
   * Validates: Requirements 12.5, 12.6, 12.7
   */
  const processEnrollment = async (chunks: Float32Array[]) => {
    // Show processing state (Requirement 12.5)
    setUIState({ state: 'processing', countdown: null, errorMessage: null });
    
    try {
      // Concatenate all audio chunks
      const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
      const audioSamples = new Float32Array(totalLength);
      let offset = 0;
      for (const chunk of chunks) {
        audioSamples.set(chunk, offset);
        offset += chunk.length;
      }
      
      // Extract voice fingerprint (Requirement 3.2, 3.3)
      const voiceprint = await enrollUserVoice(audioSamples, 16000);
      
      // Show success confirmation (Requirement 12.6)
      setUIState({ state: 'success', countdown: null, errorMessage: null });
      
      // Auto-transition to negotiation screen after 1 second (Requirement 12.7)
      setTimeout(() => {
        onEnrollmentComplete(voiceprint);
      }, 1000);
      
    } catch (error) {
      console.error('Voice processing error:', error);
      setUIState({ 
        state: 'error', 
        countdown: null, 
        errorMessage: 'Failed to process voice. Please try again.' 
      });
      onError(error as Error);
    }
  };

  // Auto-start recording when component mounts
  useEffect(() => {
    startRecording();
  }, [startRecording]);

  return (
    <div className="enrollment-screen">
      <div className="enrollment-container">
        {/* Voice Setup Heading (Requirement 12.1) */}
        <h1 className="enrollment-heading">Voice Setup</h1>
        
        {/* Ready State */}
        {uiState.state === 'ready' && (
          <p className="enrollment-instruction">
            Preparing to record...
          </p>
        )}
        
        {/* Recording State (Requirements 12.2, 12.3, 12.4) */}
        {uiState.state === 'recording' && (
          <>
            <p className="enrollment-instruction">
              Speak for 10 seconds so I can learn your voice accurately
            </p>
            <div className="recording-indicator">
              {/* Red recording dot (Requirement 12.3) */}
              <div className="red-dot" />
              {/* Countdown timer (Requirement 12.4) */}
              <span className="countdown">{uiState.countdown}</span>
            </div>
          </>
        )}
        
        {/* Processing State (Requirement 12.5) */}
        {uiState.state === 'processing' && (
          <>
            <div className="spinner" />
            <p className="processing-text">Processing...</p>
          </>
        )}
        
        {/* Success State (Requirement 12.6) */}
        {uiState.state === 'success' && (
          <>
            <div className="checkmark">✓</div>
            <p className="success-text">Voice captured!</p>
          </>
        )}
        
        {/* Error State */}
        {uiState.state === 'error' && (
          <>
            <div className="error-icon">✗</div>
            <p className="error-text">{uiState.errorMessage}</p>
            <button 
              onClick={startRecording}
              className="retry-button"
            >
              Try Again
            </button>
          </>
        )}
      </div>

      <style jsx>{`
        .enrollment-screen {
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 100vh;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          padding: 1rem;
        }

        .enrollment-container {
          text-align: center;
          padding: 3rem 2rem;
          background: white;
          border-radius: 16px;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
          max-width: 500px;
          width: 100%;
        }

        .enrollment-heading {
          font-size: 2.5rem;
          font-weight: 700;
          margin-bottom: 2rem;
          color: #1a202c;
          letter-spacing: -0.5px;
        }

        .enrollment-instruction {
          font-size: 1.25rem;
          color: #4a5568;
          margin-bottom: 2.5rem;
          line-height: 1.6;
        }

        .recording-indicator {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 1.5rem;
          margin-top: 2rem;
        }

        .red-dot {
          width: 20px;
          height: 20px;
          background: #ef4444;
          border-radius: 50%;
          animation: pulse 1s infinite;
          box-shadow: 0 0 20px rgba(239, 68, 68, 0.6);
        }

        @keyframes pulse {
          0%, 100% { 
            opacity: 1;
            transform: scale(1);
          }
          50% { 
            opacity: 0.6;
            transform: scale(1.1);
          }
        }

        .countdown {
          font-size: 4rem;
          font-weight: 800;
          color: #1a202c;
          font-variant-numeric: tabular-nums;
          min-width: 80px;
        }

        .spinner {
          width: 64px;
          height: 64px;
          border: 6px solid #e5e7eb;
          border-top-color: #667eea;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
          margin: 2rem auto 1.5rem;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .processing-text {
          font-size: 1.25rem;
          color: #4a5568;
          font-weight: 500;
        }

        .checkmark {
          font-size: 5rem;
          color: #10b981;
          margin-bottom: 1rem;
          animation: scaleIn 0.3s ease-out;
        }

        @keyframes scaleIn {
          from {
            transform: scale(0);
            opacity: 0;
          }
          to {
            transform: scale(1);
            opacity: 1;
          }
        }

        .success-text {
          font-size: 1.5rem;
          color: #10b981;
          font-weight: 700;
        }

        .error-icon {
          font-size: 5rem;
          color: #ef4444;
          margin-bottom: 1rem;
        }

        .error-text {
          font-size: 1.125rem;
          color: #ef4444;
          margin-bottom: 1.5rem;
          line-height: 1.6;
        }

        .retry-button {
          padding: 0.875rem 2rem;
          font-size: 1.125rem;
          font-weight: 600;
          color: white;
          background: #667eea;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.2s;
        }

        .retry-button:hover {
          background: #5568d3;
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        .retry-button:active {
          transform: translateY(0);
        }

        @media (max-width: 640px) {
          .enrollment-heading {
            font-size: 2rem;
          }

          .enrollment-instruction {
            font-size: 1.125rem;
          }

          .countdown {
            font-size: 3rem;
          }
        }
      `}</style>
    </div>
  );
}
