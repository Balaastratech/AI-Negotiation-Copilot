import React, { useRef, useEffect } from 'react';
import { TranscriptEntry } from '../../lib/types';
import { User, MessageSquare, Cpu } from 'lucide-react';

interface TranscriptPanelProps {
  entries: TranscriptEntry[];
}

export function TranscriptPanel({ entries }: TranscriptPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [entries]);

  if (entries.length === 0) {
    return (
      <div className="h-full w-full bg-white rounded-xl shadow-sm border border-neutral-200 p-6 flex flex-col items-center justify-center text-center space-y-4">
        <div className="w-12 h-12 bg-neutral-100 rounded-full flex items-center justify-center animate-pulse">
          <MessageSquare className="w-6 h-6 text-neutral-400" />
        </div>
        <p className="text-neutral-500 text-sm">Waiting for conversation to start...</p>
      </div>
    );
  }

  return (
    <div className="h-full w-full bg-white rounded-xl shadow-sm border border-neutral-200 overflow-hidden flex flex-col flex-grow">
      <div className="bg-neutral-50 border-b border-neutral-200 px-6 py-3 flex flex-row items-center justify-between">
        <h2 className="text-sm font-semibold text-neutral-900 uppercase tracking-wider flex items-center">
          <MessageSquare className="w-4 h-4 mr-2 text-neutral-500" /> Transcript
        </h2>
      </div>

      <div
        ref={scrollRef}
        className="flex-1 p-6 overflow-y-auto space-y-6 scroll-smooth"
      >
        {entries.map((entry, index) => {
          const isUser = entry.speaker === 'user';
          const isCounterparty = entry.speaker === 'counterparty';
          const isAi = entry.speaker === 'ai';

          return (
            <div
              key={entry.id || `transcript-${index}-${entry.timestamp}`}
              className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`flex max-w-[80%] ${isUser ? 'flex-row-reverse' : 'flex-row'} items-end gap-3`}>
                {/* Avatar */}
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm
                  ${isUser ? 'bg-blue-600 text-white' : isCounterparty ? 'bg-orange-500 text-white' : 'bg-indigo-600 text-white'}`}
                >
                  {isUser ? <User className="w-4 h-4" /> : isCounterparty ? <MessageSquare className="w-4 h-4" /> : <Cpu className="w-4 h-4" />}
                </div>

                {/* Bubble */}
                <div className="flex flex-col gap-1">
                  <div className={`px-4 py-3 rounded-2xl ${isUser
                      ? 'bg-blue-600 text-white rounded-br-none'
                      : isCounterparty
                        ? 'bg-neutral-100 text-neutral-900 rounded-bl-none border border-neutral-200'
                        : 'bg-indigo-50 text-indigo-900 rounded-bl-none border border-indigo-200 italic'
                    }`}>
                    <p className="text-sm leading-relaxed">{entry.text}</p>
                  </div>

                  <div className={`text-[10px] text-neutral-400 font-medium tracking-wide flex items-center ${isUser ? 'justify-end' : 'justify-start'}`}>
                    <span className="uppercase mr-1">{entry.speaker}</span>
                    <span>• {new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
