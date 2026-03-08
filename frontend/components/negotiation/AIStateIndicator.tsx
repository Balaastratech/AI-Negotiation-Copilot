import React from 'react';
import { Mic, Brain, Volume2 } from 'lucide-react';

interface AIStateIndicatorProps {
  state: 'idle' | 'listening' | 'thinking' | 'speaking';
}

export function AIStateIndicator({ state }: AIStateIndicatorProps) {
  if (state === 'idle') {
    return null;
  }

  const stateConfig = {
    listening: {
      icon: Mic,
      text: 'Listening...',
      bgColor: 'bg-blue-500',
      textColor: 'text-blue-50',
      pulseColor: 'bg-blue-400',
      description: 'AI is listening to you speak'
    },
    thinking: {
      icon: Brain,
      text: 'Processing...',
      bgColor: 'bg-purple-500',
      textColor: 'text-purple-50',
      pulseColor: 'bg-purple-400',
      description: 'AI is analyzing and preparing response'
    },
    speaking: {
      icon: Volume2,
      text: 'Speaking...',
      bgColor: 'bg-green-500',
      textColor: 'text-green-50',
      pulseColor: 'bg-green-400',
      description: 'AI is responding'
    }
  };

  const config = stateConfig[state];
  const Icon = config.icon;

  return (
    <div className="fixed top-6 left-1/2 transform -translate-x-1/2 z-50">
      <div className={`${config.bgColor} ${config.textColor} px-6 py-3 rounded-full shadow-lg flex items-center gap-3 border-2 border-white/20`}>
        {/* Animated pulse indicator */}
        <div className="relative">
          <div className={`absolute inset-0 ${config.pulseColor} rounded-full animate-ping opacity-75`}></div>
          <Icon className="w-5 h-5 relative z-10" />
        </div>
        
        {/* State text */}
        <div className="flex flex-col">
          <span className="font-semibold text-sm">{config.text}</span>
          <span className="text-xs opacity-90">{config.description}</span>
        </div>
      </div>
    </div>
  );
}
