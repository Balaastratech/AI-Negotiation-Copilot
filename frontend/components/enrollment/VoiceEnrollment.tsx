"use client";

import React, { useState, useEffect, useRef } from 'react';

interface VoiceEnrollmentProps {
  onEnrollmentComplete: (success: boolean) => void;
  enrollmentStatus: { success: boolean; message: string } | null;
  onStartEnrollment: () => Promise<void>;
}

const VoiceEnrollment: React.FC<VoiceEnrollmentProps> = ({ 
  onEnrollmentComplete, 
  enrollmentStatus,
  onStartEnrollment 
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [countdown, setCountdown] = useState(5);
  const countdownRef = useRef<NodeJS.Timeout>();

  const instructionPhrase = "I am not a robot, and I will be using my own voice for this negotiation.";

  const handleStartRecording = async () => {
    setIsRecording(true);
    setCountdown(5);
    
    countdownRef.current = setInterval(() => {
      setCountdown((prev) => prev - 1);
    }, 1000);

    await onStartEnrollment();

    setTimeout(() => {
      clearInterval(countdownRef.current);
      setIsRecording(false);
    }, 5000);
  };

  useEffect(() => {
    if (enrollmentStatus) {
      onEnrollmentComplete(enrollmentStatus.success);
    }
  }, [enrollmentStatus, onEnrollmentComplete]);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg p-8 shadow-2xl max-w-md w-full text-center border border-gray-700">
        <h2 className="text-2xl font-bold text-white mb-4">Voice-Powered Speaker ID</h2>
        <p className="text-gray-300 mb-6">
          To automatically identify your voice, please record a sample by reading the following phrase aloud.
        </p>
        
        <div className="bg-gray-900 rounded-md p-4 mb-6 border border-gray-600">
          <p className="text-lg text-cyan-400 font-mono">{instructionPhrase}</p>
        </div>

        {!isRecording && !enrollmentStatus && (
          <button
            onClick={handleStartRecording}
            className="w-full bg-cyan-600 hover:bg-cyan-700 text-white font-bold py-3 px-4 rounded-lg transition-transform duration-200 ease-in-out transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-opacity-75"
          >
            Start Recording
          </button>
        )}

        {isRecording && (
          <div className="text-white">
            <p>Recording... Please speak now.</p>
            <p className="text-4xl font-bold mt-2">{countdown}</p>
          </div>
        )}
        
        {enrollmentStatus && (
          <div>
            <p className={`text-lg ${enrollmentStatus.success ? 'text-green-400' : 'text-red-400'}`}>
              {enrollmentStatus.message}
            </p>
            {!enrollmentStatus.success && (
              <button
                onClick={handleStartRecording}
                className="mt-4 bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded"
              >
                Try Again
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default VoiceEnrollment;
