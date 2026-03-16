"use client";
import React from 'react';

interface ManualSpeakerSelectorProps {
  onSpeakerSelected: (speaker: 'user' | 'counterparty') => void;
  currentSpeaker: 'user' | 'counterparty' | null;
}

export function ManualSpeakerSelector({ onSpeakerSelected, currentSpeaker }: ManualSpeakerSelectorProps) {
  const baseStyle = "px-4 py-2 rounded-md text-sm font-semibold transition-colors";
  const activeStyle = "bg-blue-600 text-white";
  const inactiveStyle = "bg-gray-200 text-gray-700 hover:bg-gray-300";

  return (
    <div className="flex items-center space-x-4 p-4 bg-gray-100 rounded-lg">
      <span className="font-medium text-gray-800">Who is speaking now?</span>
      <button
        onClick={() => onSpeakerSelected('user')}
        className={`${baseStyle} ${currentSpeaker === 'user' ? activeStyle : inactiveStyle}`}
      >
        Me (User)
      </button>
      <button
        onClick={() => onSpeakerSelected('counterparty')}
        className={`${baseStyle} ${currentSpeaker === 'counterparty' ? activeStyle : inactiveStyle}`}
      >
        Counterparty
      </button>
    </div>
  );
}
