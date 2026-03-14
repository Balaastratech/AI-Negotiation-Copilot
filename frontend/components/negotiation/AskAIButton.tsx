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

export function AskAIButton({ 
  onStartCopilot, 
  onGetAdvice, 
  onGetCommand,
  isLoading, 
  isDisabled, 
  copilotActive,
  responseMode
}: AskAIButtonProps) {
  console.log('[AskAIButton] copilotActive:', copilotActive, 'isDisabled:', isDisabled, 'responseMode:', responseMode);
  
  return (
    <div className="flex flex-col gap-2">
      {/* When copilot is NOT active - show Start Copilot button */}
      {!copilotActive && (
        <button
          onClick={onStartCopilot}
          disabled={isDisabled || isLoading}
          className={`flex items-center justify-center px-6 py-3 rounded-full font-semibold transition-all duration-200 shadow-lg border
            ${isLoading || isDisabled
              ? 'bg-neutral-300 border-neutral-400 text-neutral-500 cursor-not-allowed'
              : 'bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white border-purple-700/50 shadow-purple-600/30 hover:shadow-purple-600/40 transform hover:-translate-y-0.5'
            }`}
          aria-label="Start Copilot"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              <span>Starting...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-5 h-5 mr-2" />
              <span>Start Copilot</span>
            </>
          )}
        </button>
      )}

          {/* When copilot IS active - show Get Advice and Get Command buttons */}
          {copilotActive && (
            <div className="flex flex-col gap-2">
              <div className="text-center text-xs text-green-600 font-medium mb-1">
                <Mic className="w-3 h-3 inline mr-1 animate-pulse" />
                Copilot Active - Select mode below
              </div>
              
              <div className="flex gap-2">
                {/* Get Advice Button - skips validation */}
                <button
                  onClick={() => {
                    console.log('[DEBUG] Get Advice button clicked');
                    onGetAdvice();
                  }}
                  disabled={isDisabled || isLoading}
                  className={`flex items-center justify-center px-4 py-2 rounded-full font-semibold transition-all duration-200 shadow-lg border text-sm flex-1
                    ${responseMode === 'advice'
                      ? 'bg-green-600 border-green-700 ring-2 ring-green-400'
                      : isLoading || isDisabled
                      ? 'bg-neutral-300 border-neutral-400 text-neutral-500 cursor-not-allowed'
                      : 'bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white border-blue-700/50 shadow-blue-600/30 hover:shadow-blue-600/40 transform hover:-translate-y-0.5'
                    }`}
                  aria-label="Get Advice"
                >
                  {responseMode === 'advice' && <Check className="w-4 h-4 mr-1" />}
                  <MessageSquare className="w-4 h-4 mr-1" />
                  <span>Advice</span>
                </button>

                {/* Get Command Button - validates response */}
                <button
                  onClick={() => {
                    console.log('[DEBUG] Get Command button clicked');
                    onGetCommand();
                  }}
                  disabled={isDisabled || isLoading}
                  className={`flex items-center justify-center px-4 py-2 rounded-full font-semibold transition-all duration-200 shadow-lg border text-sm flex-1
                    ${responseMode === 'command'
                      ? 'bg-green-600 border-green-700 ring-2 ring-green-400'
                      : isLoading || isDisabled
                      ? 'bg-neutral-300 border-neutral-400 text-neutral-500 cursor-not-allowed'
                      : 'bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-700 hover:to-red-700 text-white border-orange-700/50 shadow-orange-600/30 hover:shadow-orange-600/40 transform hover:-translate-y-0.5'
                    }`}
                  aria-label="Get Command"
                >
                  {responseMode === 'command' && <Check className="w-4 h-4 mr-1" />}
                  <Zap className="w-4 h-4 mr-1" />
                  <span>Command</span>
                </button>
              </div>
          
          <div className="text-center text-xs text-neutral-500">
            Then press and hold to talk
          </div>
        </div>
      )}
    </div>
  );
}
