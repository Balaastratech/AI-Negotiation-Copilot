import React from 'react';
import { Loader2, Search, Sparkles } from 'lucide-react';

interface ResearchIndicatorProps {
  isResearching: boolean;
  progress: string | null;
}

export function ResearchIndicator({ isResearching, progress }: ResearchIndicatorProps) {
  if (!isResearching) return null;
  
  return (
    <div className="fixed top-20 left-1/2 transform -translate-x-1/2 z-50 animate-in fade-in slide-in-from-top-4 duration-300">
      <div className="bg-gradient-to-r from-purple-600 to-blue-600 text-white px-6 py-3 rounded-full shadow-lg flex items-center gap-3">
        <div className="relative">
          <Loader2 className="w-5 h-5 animate-spin" />
          <Sparkles className="w-3 h-3 absolute -top-1 -right-1 animate-pulse" />
        </div>
        <span className="font-semibold">
          {progress || 'Analyzing conversation...'}
        </span>
      </div>
    </div>
  );
}
