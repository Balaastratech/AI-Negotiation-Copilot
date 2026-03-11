import React from 'react';
import { NegotiationState } from '../../hooks/useNegotiationState';

/**
 * Debug panel to display the button-triggered negotiation state.
 * Shows item, prices, market data, and transcript for development/testing.
 */
interface StateDebugPanelProps {
  state: NegotiationState;
}

export function StateDebugPanel({ state }: StateDebugPanelProps) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-4">
      <h3 className="text-sm font-semibold text-neutral-700 mb-3">
        Negotiation State (Button-Triggered System)
      </h3>
      
      <div className="space-y-2 text-xs">
        <div className="flex justify-between">
          <span className="text-neutral-600">Item:</span>
          <span className="font-medium">{state.item || 'Not set'}</span>
        </div>
        
        <div className="flex justify-between">
          <span className="text-neutral-600">Seller Price:</span>
          <span className="font-medium">
            {state.seller_price !== null ? `$${state.seller_price}` : 'Not mentioned'}
          </span>
        </div>
        
        <div className="flex justify-between">
          <span className="text-neutral-600">Target Price:</span>
          <span className="font-medium">
            {state.target_price > 0 ? `$${state.target_price}` : 'Not set'}
          </span>
        </div>
        
        <div className="flex justify-between">
          <span className="text-neutral-600">Max Price:</span>
          <span className="font-medium">
            {state.max_price > 0 ? `$${state.max_price}` : 'Not set'}
          </span>
        </div>
        
        <div className="flex justify-between">
          <span className="text-neutral-600">Market Data:</span>
          <span className="font-medium text-right max-w-[200px] truncate">
            {state.market_data || 'Not available'}
          </span>
        </div>
        
        <div className="pt-2 border-t border-neutral-200">
          <span className="text-neutral-600">Transcript Entries:</span>
          <span className="font-medium ml-2">{state.transcript.length}</span>
        </div>
        
        {state.transcript.length > 0 && (
          <div className="mt-2 max-h-32 overflow-y-auto text-xs">
            {state.transcript.slice(-5).map((entry, idx) => (
              <div key={idx} className="py-1">
                <span className={entry.speaker === 'USER' ? 'text-blue-600' : 'text-purple-600'}>
                  [{entry.speaker}]
                </span>
                <span className="ml-2 text-neutral-700">{entry.text}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
