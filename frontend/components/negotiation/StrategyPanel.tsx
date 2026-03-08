import React from 'react';
import { Strategy } from '../../lib/types';
import { Target, TrendingDown, TrendingUp, Users, AlertTriangle, Lightbulb } from 'lucide-react';

interface StrategyPanelProps {
  strategy: Strategy | null;
}

export function StrategyPanel({ strategy }: StrategyPanelProps) {
  if (!strategy) {
    return (
      <div className="h-full w-full bg-white rounded-xl shadow-sm border border-neutral-200 p-6 flex flex-col items-center justify-center text-center space-y-4">
        <div className="w-12 h-12 bg-neutral-100 rounded-full flex items-center justify-center animate-pulse">
          <Lightbulb className="w-6 h-6 text-neutral-400" />
        </div>
        <p className="text-neutral-500 text-sm">Listening to negotiation to formulate strategy...</p>
      </div>
    );
  }

  const {
    target_price,
    current_offer,
    recommended_response,
    key_points,
    approach_type,
    confidence,
    walkaway_threshold,
  } = strategy;

  const clampedConfidence = Math.min(1, Math.max(0, confidence));
  const confidencePercent = Math.round(clampedConfidence * 100);

  return (
    <div className="h-full w-full bg-white rounded-xl shadow-sm border border-neutral-200 overflow-hidden flex flex-col flex-grow">
      {/* Header */}
      <div className="bg-neutral-50 border-b border-neutral-200 px-6 py-4 flex flex-row items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className={`p-1.5 rounded-md ${approach_type === 'collaborative' ? 'bg-blue-100 text-blue-700' : approach_type === 'aggressive' ? 'bg-orange-100 text-orange-700' : 'bg-red-100 text-red-700'}`}>
            {approach_type === 'collaborative' ? <Users className="w-4 h-4" /> : approach_type === 'aggressive' ? <TrendingUp className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
          </div>
          <h2 className="text-sm font-semibold text-neutral-900 uppercase tracking-wider">
            {approach_type} Strategy
          </h2>
        </div>
        <div className="flex items-center space-x-1" title="AI Confidence Score">
          <div className="h-2 w-16 bg-neutral-200 rounded-full overflow-hidden">
            <div className="h-full bg-green-500" style={{ width: `${confidencePercent}%` }} />
          </div>
          <span className="text-xs text-neutral-500 font-medium ml-2">{confidencePercent}%</span>
        </div>
      </div>

      <div className="p-6 flex-1 overflow-y-auto space-y-6">
        {/* Recommended Response */}
        <div className="space-y-3">
          <h3 className="text-xs font-bold text-neutral-500 uppercase tracking-widest flex items-center">
            <Lightbulb className="w-3 h-3 mr-1.5" /> What to Say
          </h3>
          <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 relative">
            <p className="text-blue-900 text-base font-medium leading-relaxed italic">
              "{recommended_response}"
            </p>
          </div>
        </div>

        {/* Pricing Dynamics */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-neutral-50 rounded-lg p-4 border border-neutral-100 flex flex-col items-center justify-center">
            <span className="text-xs font-semibold text-neutral-500 uppercase mb-1 flex items-center">
              <TrendingDown className="w-3 h-3 mr-1" /> They Want
            </span>
            <span className="text-2xl font-bold text-neutral-900">
              {current_offer !== null ? `$${current_offer.toFixed(2)}` : '???'}
            </span>
          </div>

          <div className="bg-emerald-50 rounded-lg p-4 border border-emerald-100 flex flex-col items-center justify-center">
            <span className="text-xs font-semibold text-emerald-600 uppercase mb-1 flex items-center">
              <Target className="w-3 h-3 mr-1" /> Target
            </span>
            <span className="text-2xl font-bold text-emerald-700">
              {target_price !== null ? `$${target_price.toFixed(2)}` : '???'}
            </span>
          </div>
        </div>

        {/* Key Talking Points */}
        {key_points.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-neutral-500 uppercase tracking-widest flex items-center">
              <TrendingUp className="w-3 h-3 mr-1.5" /> Key Leverage Points
            </h3>
            <ul className="space-y-2">
              {key_points.map((point, idx) => (
                <li key={idx} className="flex items-start text-sm text-neutral-700 bg-white border border-neutral-200 rounded p-3 shadow-sm">
                  <div className="mr-3 mt-0.5 w-1.5 h-1.5 rounded-full bg-blue-500 flex-shrink-0" />
                  {point}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Walkaway Notice */}
        {walkaway_threshold !== null && (
          <div className="mt-6 pt-6 border-t border-neutral-100">
            <div className="flex items-center text-red-600 text-xs font-semibold uppercase tracking-wider">
              <AlertTriangle className="w-3 h-3 mr-1" /> Walkaway Threshold: <span className="ml-1 text-red-700">${walkaway_threshold.toFixed(2)}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
