import React from 'react';
import { Sparkles, Loader2 } from 'lucide-react';

interface AskAIButtonProps {
  onAskAI: () => void;
  isLoading: boolean;
  isDisabled: boolean;
}

export function AskAIButton({ onAskAI, isLoading, isDisabled }: AskAIButtonProps) {
  return (
    <button
      onClick={onAskAI}
      disabled={isDisabled || isLoading}
      className={`flex items-center justify-center px-6 py-3 rounded-full font-semibold transition-all duration-200 shadow-lg border
        ${isLoading || isDisabled
          ? 'bg-neutral-300 border-neutral-400 text-neutral-500 cursor-not-allowed'
          : 'bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white border-purple-700/50 shadow-purple-600/30 hover:shadow-purple-600/40 transform hover:-translate-y-0.5'
        }`}
      aria-label="Ask AI for advice"
    >
      {isLoading ? (
        <>
          <Loader2 className="w-5 h-5 mr-2 animate-spin" />
          <span>AI Thinking...</span>
        </>
      ) : (
        <>
          <Sparkles className="w-5 h-5 mr-2" />
          <span>Ask AI</span>
        </>
      )}
    </button>
  );
}
