"use client";

import React, { useState, useEffect, useRef } from 'react';

interface VoiceEnrollmentScreenProps {
  onEnrollmentComplete: (success: boolean) => void;
  enrollmentStatus: { success: boolean; message: string } | null;
  onStartEnrollment: () => Promise<void>;
}

const VoiceEnrollmentScreen: React.FC<VoiceEnrollmentScreenProps> = ({ 
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
      setCountdown((prev) => {
        if (prev <= 1) {
          if (countdownRef.current) clearInterval(countdownRef.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    await onStartEnrollment();

    // The parent component will handle the completion logic
  };

  useEffect(() => {
    if (enrollmentStatus) {
      if (countdownRef.current) clearInterval(countdownRef.current);
      setIsRecording(false);
      
      // Notify parent after a short delay to allow user to see the message
      setTimeout(() => {
        onEnrollmentComplete(enrollmentStatus.success);
      }, 1500);
    }
  }, [enrollmentStatus, onEnrollmentComplete]);
  
  // Auto-start recording on component mount
  useEffect(() => {
    handleStartRecording();
  }, []);

  const getStatusContent = () => {
    if (isRecording && !enrollmentStatus) {
      return (
        <>
          <div className="flex items-center justify-center space-x-4">
            <div className="w-8 h-8 bg-red-500 rounded-full animate-pulse"></div>
            <p className="text-2xl">Recording...</p>
          </div>
          <p className="text-6xl font-bold mt-4">{countdown}</p>
          <p className="mt-4 text-gray-400">Please begin speaking.</p>
        </>
      );
    }

    if (enrollmentStatus) {
      return (
        <>
          <p className={`text-2xl ${enrollmentStatus.success ? 'text-green-400' : 'text-red-400'}`}>
            {enrollmentStatus.success ? '✓ Success!' : '✗ Error'}
          </p>
          <p className="mt-2 text-gray-300">{enrollmentStatus.message}</p>
          {!enrollmentStatus.success && (
            <button
              onClick={handleStartRecording}
              className="mt-6 bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded-lg"
            >
              Try Again
            </button>
          )}
        </>
      );
    }

    return null;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-2xl p-8 shadow-2xl max-w-lg w-full text-center border border-gray-700">
        <h2 className="text-3xl font-bold text-white mb-4">Voice Enrollment</h2>
        <p className="text-gray-300 mb-6">
          To enable hands-free speaker identification, please read the following phrase aloud.
        </p>
        
        <div className="bg-gray-900 rounded-md p-4 mb-8 border border-gray-600">
          <p className="text-xl text-cyan-400 font-mono leading-relaxed">{`"${instructionPhrase}"`}</p>
        </div>

        <div className="h-24 flex items-center justify-center">
          {getStatusContent()}
        </div>
      </div>
    </div>
  );
};

export default VoiceEnrollmentScreen;
