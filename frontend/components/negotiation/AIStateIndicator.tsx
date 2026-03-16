import React from 'react';
import { Mic, Brain, Volume2, Loader2, CheckCircle2 } from 'lucide-react';

interface AIStateIndicatorProps {
  state: 'idle' | 'connecting' | 'connected' | 'listening' | 'thinking' | 'speaking';
}

export function AIStateIndicator({ state }: AIStateIndicatorProps) {
  if (state === 'idle') return null;

  const cfg = {
    connecting: { icon: Loader2,      text: 'Connecting to AI advisor', color: '#fb923c', spin: true  },
    connected:  { icon: CheckCircle2, text: 'AI advisor ready',          color: '#34d399', spin: false },
    listening:  { icon: Mic,          text: 'AI listening',              color: '#60a5fa', spin: false },
    thinking:   { icon: Brain,        text: 'AI processing',             color: '#c084fc', spin: false },
    speaking:   { icon: Volume2,      text: 'AI speaking',               color: '#34d399', spin: false },
  }[state];

  const Icon = cfg.icon;

  return (
    <div className="fixed top-3 left-1/2 -translate-x-1/2 z-50 pointer-events-none">
      <div className="flex items-center gap-1.5 px-3 py-1 rounded-full"
        style={{
          background: 'rgba(8,8,16,0.55)',
          backdropFilter: 'blur(24px) saturate(180%)',
          border: `1px solid ${cfg.color}45`,
          boxShadow: `0 0 14px ${cfg.color}20`,
        }}>
        <Icon className={`w-3 h-3 ${cfg.spin ? 'animate-spin' : ''}`} style={{ color: cfg.color }} />
        <span className="text-[11px] font-semibold" style={{ color: cfg.color }}>{cfg.text}</span>
      </div>
    </div>
  );
}
