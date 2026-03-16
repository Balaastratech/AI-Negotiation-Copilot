import React from 'react';
import { Sparkles, Loader2, Mic, Zap, MessageSquare, Check } from 'lucide-react';

interface AskAIButtonProps {
  onStartCopilot: () => void;
  onGetAdvice: () => void;
  onGetCommand: () => void;
  isLoading: boolean;
  isDisabled: boolean;
  copilotActive: boolean;
  responseMode?: 'advice' | 'command' | null;
}

export function AskAIButton({ onStartCopilot, onGetAdvice, onGetCommand, isLoading, isDisabled, copilotActive, responseMode }: AskAIButtonProps) {
  const goldBtn = {
    background: 'linear-gradient(135deg, #f5c518, #ffd700)',
    color: '#080810',
    boxShadow: '0 0 28px rgba(245,197,24,0.45), inset 0 1px 0 rgba(255,255,255,0.3)',
    border: '1px solid rgba(245,197,24,0.6)',
  };
  const ghostBtn = {
    background: 'rgba(245,197,24,0.08)',
    color: 'rgba(255,255,255,0.92)',
    border: '1px solid rgba(245,197,24,0.22)',
  };
  const disabledBtn = {
    background: 'rgba(255,255,255,0.04)',
    color: 'rgba(255,255,255,0.2)',
    border: '1px solid rgba(255,255,255,0.08)',
    cursor: 'not-allowed' as const,
  };

  return (
    <div className="flex flex-col gap-2 items-end">
      {!copilotActive && (
        <button
          onClick={onStartCopilot}
          disabled={isDisabled || isLoading}
          className="flex items-center justify-center px-6 py-3 rounded-full font-bold transition-all duration-200 hover:scale-105"
          style={isDisabled || isLoading ? disabledBtn : goldBtn}
          aria-label="Start Copilot"
        >
          {isLoading
            ? <><Loader2 className="w-5 h-5 mr-2 animate-spin" /><span>Starting...</span></>
            : <><Sparkles className="w-5 h-5 mr-2" /><span>Start Copilot</span></>}
        </button>
      )}

      {copilotActive && (
        <div className="flex flex-col gap-2 items-end">
          <div className="flex items-center gap-1.5 text-xs font-bold"
            style={{ color: '#f5c518', textShadow: '0 0 10px rgba(245,197,24,0.5)' }}>
            <Mic className="w-3 h-3 animate-pulse" />
            Copilot Active — Select mode
          </div>
          <div className="flex gap-2">
            <button
              onClick={onGetAdvice}
              disabled={isDisabled || isLoading}
              className="flex items-center justify-center px-4 py-2 rounded-full font-bold text-sm transition-all duration-200 hover:scale-105"
              style={responseMode === 'advice' ? goldBtn : ghostBtn}
              aria-label="Get Advice"
            >
              {responseMode === 'advice' && <Check className="w-4 h-4 mr-1" />}
              <MessageSquare className="w-4 h-4 mr-1" />Advice
            </button>
            <button
              onClick={onGetCommand}
              disabled={isDisabled || isLoading}
              className="flex items-center justify-center px-4 py-2 rounded-full font-bold text-sm transition-all duration-200 hover:scale-105"
              style={responseMode === 'command' ? goldBtn : ghostBtn}
              aria-label="Get Command"
            >
              {responseMode === 'command' && <Check className="w-4 h-4 mr-1" />}
              <Zap className="w-4 h-4 mr-1" />Command
            </button>
          </div>
          <div className="text-[10px]" style={{ color: 'rgba(245,197,24,0.45)' }}>
            Then press and hold to talk
          </div>
        </div>
      )}
    </div>
  );
}
