import React from 'react';
import { Mic, MicOff, Camera, CameraOff, PhoneOff, Phone } from 'lucide-react';

interface ControlBarProps {
  isAudioActive: boolean;
  isVisionActive: boolean;
  isNegotiating: boolean;
  onToggleAudio: () => void;
  onToggleVision: () => void;
  onStartNegotiation: () => void;
  onEndNegotiation: () => void;
}

export function ControlBar({
  isAudioActive,
  isVisionActive,
  isNegotiating,
  onToggleAudio,
  onToggleVision,
  onStartNegotiation,
  onEndNegotiation
}: ControlBarProps) {
  return (
    <div className="w-full bg-white border-t border-neutral-200 p-4 shadow-[0_-4px_20px_-10px_rgba(0,0,0,0.05)] z-10 flex items-center justify-center">
      <div className="flex items-center space-x-6">
        {/* Audio Toggle */}
        <button
          onClick={onToggleAudio}
          disabled={!isNegotiating}
          className={`flex flex-col items-center justify-center p-4 rounded-full transition-all duration-200 shadow-sm border
            ${isAudioActive
              ? 'bg-blue-50 border-blue-200 text-blue-600 hover:bg-blue-100'
              : 'bg-neutral-100 border-neutral-200 text-neutral-500 hover:bg-neutral-200'}
            ${!isNegotiating ? 'opacity-50 cursor-not-allowed' : ''}`}
          title={isAudioActive ? "Mute Microphone" : "Unmute Microphone"}
        >
          {isAudioActive ? <Mic className="w-6 h-6" /> : <MicOff className="w-6 h-6" />}
        </button>

        {/* Start / End Call Button */}
        {isNegotiating ? (
          <button
            onClick={onEndNegotiation}
            className="flex items-center justify-center px-8 py-4 rounded-full bg-red-600 hover:bg-red-700 text-white font-bold transition-all duration-200 shadow-lg shadow-red-600/30 border border-red-700/50 hover:shadow-red-600/40 transform hover:-translate-y-0.5"
            title="End Negotiation"
          >
            <PhoneOff className="w-5 h-5 mr-2" />
            End Session
          </button>
        ) : (
          <button
            onClick={onStartNegotiation}
            className="flex items-center justify-center px-8 py-4 rounded-full bg-green-600 hover:bg-green-700 text-white font-bold transition-all duration-200 shadow-lg shadow-green-600/30 border border-green-700/50 hover:shadow-green-600/40 transform hover:-translate-y-0.5"
            title="Start Negotiation"
          >
            <Phone className="w-5 h-5 mr-2" />
            Start Session
          </button>
        )}

        {/* Vision Toggle */}
        <button
          onClick={onToggleVision}
          disabled={!isNegotiating}
          className={`flex flex-col items-center justify-center p-4 rounded-full transition-all duration-200 shadow-sm border
            ${isVisionActive
              ? 'bg-blue-50 border-blue-200 text-blue-600 hover:bg-blue-100'
              : 'bg-neutral-100 border-neutral-200 text-neutral-500 hover:bg-neutral-200'}
            ${!isNegotiating ? 'opacity-50 cursor-not-allowed' : ''}`}
          title={isVisionActive ? "Disable Camera" : "Enable Camera"}
        >
          {isVisionActive ? <Camera className="w-6 h-6" /> : <CameraOff className="w-6 h-6" />}
        </button>
      </div>
    </div>
  );
}
