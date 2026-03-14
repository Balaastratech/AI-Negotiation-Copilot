import React from 'react';
import { Mic, Brain, Volume2, Loader2, CheckCircle2 } from 'lucide-react';

interface AIStateIndicatorProps {
  state: 'idle' | 'connecting' | 'connected' | 'listening' | 'thinking' | 'speaking';
}

export function AIStateIndicator({ state }: AIStateIndicatorProps) {
  if (state === 'idle') return null;

  const stateConfig = {
    connecting: {
      icon: Loader2,
      text: 'Connecting...',
      bgColor: 'bg-orange-500',
      textColor: 'text-orange-50',
      pulseColor: 'bg-orange-400',
      description: 'Connecting to AI advisor',
      spin: true,
    },
    connected: {
      icon: CheckCircle2,
      text: 'Connected',
      bgColor: 'bg-emerald-500',
      textColor: 'text-emerald-50',
      pulseColor: 'bg-emerald-400',
      description: 'AI advisor ready',
      spin: false,
    },
    listening: {
      icon: Mic,
      text: 'Listening...',
      bgColor: 'bg-blue-500',
      textColor: 'text-blue-50',
      pulseColor: 'bg-blue-400',
      description: 'AI is listening',
      spin: false,
    },
    thinking: {
      icon: Brain,
      text: 'Processing...',
      bgColor: 'bg-purple-500',
      textColor: 'text-purple-50',
      pulseColor: 'bg-purple-400',
      description: 'AI is analyzing',
      spin: false,
    },
    speaking: {
      icon: Volume2,
      text: 'Speaking...',
      bgColor: 'bg-green-500',
      textColor: 'text-green-50',
      pulseColor: 'bg-green-400',
      description: 'AI is responding',
      spin: false,
    },
  };

  const config = stateConfig[state];
  const Icon = config.icon;

  return (
    <div className="fixed top-6 left-1/2 transform -translate-x-1/2 z-50">
      <div className={`${config.bgColor} ${config.textColor} px-6 py-3 rounded-full shadow-lg flex items-center gap-3 border-2 border-white/20`}>
        <div className="relative">
          {!config.spin && (
            <div className={`absolute inset-0 ${config.pulseColor} rounded-full animate-ping opacity-75`}></div>
          )}
          <Icon className={`w-5 h-5 relative z-10 ${config.spin ? 'animate-spin' : ''}`} />
        </div>
        <div className="flex flex-col">
          <span className="font-semibold text-sm">{config.text}</span>
          <span className="text-xs opacity-90">{config.description}</span>
        </div>
      </div>
    </div>
  );
}
