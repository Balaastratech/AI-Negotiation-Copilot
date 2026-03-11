"use client";

import { useState } from 'react';

interface ManualSpeakerSelectorProps {
  onSpeakerSelected: (speaker: 'user' | 'counterparty') => void;
  currentSpeaker: 'user' | 'counterparty' | null;
}

export function ManualSpeakerSelector({ onSpeakerSelected, currentSpeaker }: ManualSpeakerSelectorProps) {
  return (
    <div className="flex items-center gap-3 p-4 bg-white rounded-lg shadow-sm border border-neutral-200">
      <span className="text-sm font-medium text-neutral-700">Who is speaking?</span>
      
      <div className="flex gap-2">
        <button
          onClick={() => onSpeakerSelected('user')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
            currentSpeaker === 'user'
              ? 'bg-blue-600 text-white shadow-md'
              : 'bg-neutral-100 text-neutral-700 hover:bg-neutral-200'
          }`}
        >
          👤 USER
        </button>
        
        <button
          onClick={() => onSpeakerSelected('counterparty')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
            currentSpeaker === 'counterparty'
              ? 'bg-green-600 text-white shadow-md'
              : 'bg-neutral-100 text-neutral-700 hover:bg-neutral-200'
          }`}
        >
          🤝 COUNTERPARTY
        </button>
      </div>
      
      {currentSpeaker && (
        <span className="text-xs text-neutral-500 ml-2">
          (Active: {currentSpeaker.toUpperCase()})
        </span>
      )}
    </div>
  );
}
