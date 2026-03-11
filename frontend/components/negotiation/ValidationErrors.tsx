import React from 'react';
import { AlertCircle, DollarSign, Package, Target } from 'lucide-react';
import { ValidationError } from '../../hooks/useNegotiationState';

/**
 * Props for ValidationErrors component
 */
interface ValidationErrorsProps {
  errors: ValidationError[];
}

/**
 * Friendly error messages with icons and actionable guidance
 */
const ERROR_DETAILS: Record<string, { title: string; message: string; icon: React.ReactNode }> = {
  'missing_item': {
    title: 'Item not detected',
    message: 'I couldn\'t identify what you\'re negotiating for. Try saying "I\'m buying a [item]"',
    icon: <Package className="w-5 h-5 text-yellow-600" />
  },
  'missing_seller_price': {
    title: 'Seller price unknown',
    message: 'I haven\'t heard the seller\'s asking price yet. Ask them "How much are you asking?"',
    icon: <DollarSign className="w-5 h-5 text-yellow-600" />
  },
  'missing_target_price': {
    title: 'Target price not set',
    message: 'You haven\'t set your target price. Say "I want to pay around $[amount]"',
    icon: <Target className="w-5 h-5 text-yellow-600" />
  },
  'target_price': {
    title: 'Price constraint issue',
    message: 'Your target price is higher than your maximum price. Please adjust your limits.',
    icon: <AlertCircle className="w-5 h-5 text-red-600" />
  },
  'max_price': {
    title: 'Maximum price issue',
    message: 'Your maximum price should be higher than your target price.',
    icon: <AlertCircle className="w-5 h-5 text-red-600" />
  }
};

/**
 * Component to display validation errors for negotiation state.
 * Shows clear, actionable error messages when state validation fails.
 * 
 * Validates: Requirements 12.4, 12.5 (display validation errors)
 */
export function ValidationErrors({ errors }: ValidationErrorsProps) {
  if (errors.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2" role="alert" aria-live="polite">
      {errors.map((error, index) => {
        const details = ERROR_DETAILS[error.field] || {
          title: 'Validation Error',
          message: error.message,
          icon: <AlertCircle className="w-5 h-5 text-yellow-600" />
        };
        
        return (
          <div 
            key={`${error.field}-${index}`} 
            className="flex items-start gap-3 p-4 bg-yellow-50 border border-yellow-200 rounded-lg"
          >
            <div className="flex-shrink-0 mt-0.5">
              {details.icon}
            </div>
            <div className="flex-1">
              <div className="font-semibold text-yellow-900 text-sm mb-1">
                {details.title}
              </div>
              <div className="text-sm text-yellow-800 leading-relaxed">
                {details.message}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
