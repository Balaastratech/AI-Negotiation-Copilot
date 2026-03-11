import React, { useEffect, useState, useRef } from 'react';
import { Package, DollarSign, Target, TrendingUp, Radio } from 'lucide-react';
import { NegotiationState } from '../../hooks/useNegotiationState';

interface NegotiationStateCardProps {
  state: NegotiationState;
  isDualModelActive?: boolean;
}

interface StateFieldProps {
  label: string;
  value: string;
  icon: React.ReactNode;
  isUpdated?: boolean;
}

function StateField({ label, value, icon, isUpdated }: StateFieldProps) {
  return (
    <div
      className={`flex items-center justify-between p-3 rounded-lg transition-all duration-300 ${
        isUpdated ? 'bg-green-50 border border-green-200 animate-pulse' : 'bg-neutral-50'
      }`}
    >
      <div className="flex items-center gap-2">
        <div className="text-neutral-600">{icon}</div>
        <span className="text-sm font-medium text-neutral-700">{label}</span>
      </div>
      <span className="text-sm font-semibold text-neutral-900">{value}</span>
    </div>
  );
}

export function NegotiationStateCard({ state, isDualModelActive = false }: NegotiationStateCardProps) {
  const [recentlyUpdated, setRecentlyUpdated] = useState<string | null>(null);
  const prevStateRef = useRef(state);

  useEffect(() => {
    const prevState = prevStateRef.current;

    if (state.item !== prevState.item && state.item) {
      setRecentlyUpdated('item');
      setTimeout(() => setRecentlyUpdated(null), 2000);
    } else if (state.seller_price !== prevState.seller_price && state.seller_price !== null) {
      setRecentlyUpdated('seller_price');
      setTimeout(() => setRecentlyUpdated(null), 2000);
    } else if (state.target_price !== prevState.target_price && state.target_price > 0) {
      setRecentlyUpdated('target_price');
      setTimeout(() => setRecentlyUpdated(null), 2000);
    } else if (state.market_data !== prevState.market_data && state.market_data) {
      setRecentlyUpdated('market_data');
      setTimeout(() => setRecentlyUpdated(null), 2000);
    }

    prevStateRef.current = state;
  }, [state]);

  return (
    <div className="bg-white rounded-lg shadow-md border border-neutral-200 p-6 h-full">
      <h3 className="text-lg font-bold text-neutral-800 mb-4 flex items-center gap-2">
        <Package className="w-5 h-5 text-blue-600" />
        Negotiation Context
        {isDualModelActive && (
          <span className="ml-auto flex items-center gap-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-full px-2.5 py-1">
            <Radio className="w-3 h-3 animate-pulse text-emerald-500" />
            Listener Active
          </span>
        )}
      </h3>

      <div className="space-y-3">
        {/* Item */}
        <StateField
          label="Item"
          value={state.item || 'Not detected yet'}
          icon={<Package className="w-4 h-4" />}
          isUpdated={recentlyUpdated === 'item'}
        />

        {/* Seller Price */}
        <StateField
          label="Seller's Price"
          value={state.seller_price ? `$${state.seller_price}` : 'Not mentioned'}
          icon={<DollarSign className="w-4 h-4" />}
          isUpdated={recentlyUpdated === 'seller_price'}
        />

        {/* User Offer */}
        <StateField
          label="Your Offer"
          value={state.user_offer ? `$${state.user_offer}` : 'Not mentioned'}
          icon={<DollarSign className="w-4 h-4" />}
          isUpdated={recentlyUpdated === 'user_offer'}
        />

        {/* Your Target */}
        <StateField
          label="Your Target"
          value={state.target_price > 0 ? `$${state.target_price}` : 'Not set'}
          icon={<Target className="w-4 h-4" />}
          isUpdated={recentlyUpdated === 'target_price'}
        />

        {/* Max Price */}
        <StateField
          label="Your Maximum"
          value={state.max_price > 0 ? `$${state.max_price}` : 'Not set'}
          icon={<DollarSign className="w-4 h-4" />}
          isUpdated={recentlyUpdated === 'max_price'}
        />

        {/* Market Data */}
        {state.market_data && (
          <div
            className={`mt-4 p-4 rounded-lg border transition-all duration-300 ${
              recentlyUpdated === 'market_data'
                ? 'bg-blue-100 border-blue-300 animate-pulse'
                : 'bg-blue-50 border-blue-200'
            }`}
          >
            <div className="flex items-start gap-2">
              <TrendingUp className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <div className="font-semibold text-blue-900 text-sm mb-1">Market Research</div>
                <div className="text-sm text-blue-800 leading-relaxed">{state.market_data}</div>
              </div>
            </div>
          </div>
        )}

        {/* Transcript Count */}
        <div className="pt-3 border-t border-neutral-200 flex items-center justify-between text-xs text-neutral-600">
          <span>Conversation entries</span>
          <span className="font-semibold">{state.transcript.length}</span>
        </div>
      </div>
    </div>
  );
}
