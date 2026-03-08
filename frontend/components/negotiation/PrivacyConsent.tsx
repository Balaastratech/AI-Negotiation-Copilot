import React from 'react';
import { Shield } from 'lucide-react';

interface PrivacyConsentProps {
  onAccept: () => void;
}

export function PrivacyConsent({ onAccept }: PrivacyConsentProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-8 border border-neutral-200">
        <div className="flex flex-col items-center text-center space-y-4">
          <div className="bg-blue-50 p-3 rounded-full">
            <Shield className="w-10 h-10 text-blue-600" />
          </div>
          
          <h2 className="text-2xl font-bold tracking-tight text-neutral-900">Privacy & Consent</h2>
          
          <p className="text-neutral-600 text-sm leading-relaxed">
            This AI Negotiation Copilot requires access to your microphone and camera to function effectively. 
            By continuing, your audio and video streams will be sent in real-time to the Gemini AI models 
            for processing and strategic recommendations.
          </p>

          <div className="w-full pt-4">
            <button
              onClick={onAccept}
              className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            >
              I Understand and Consent
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
