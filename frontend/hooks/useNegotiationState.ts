import { useState, useCallback } from 'react';

/**
 * Negotiation state for button-triggered advice system.
 * Separate from useNegotiation hook - tracks item, prices, market data, and transcript.
 */
export interface NegotiationState {
  item: string;
  seller_price: number | null;
  user_offer: number | null;
  target_price: number;
  max_price: number;
  market_data: any;
  transcript: TranscriptEntry[];
  isResearching: boolean;
  researchProgress: string | null;
}

/**
 * Transcript entry with speaker label and timestamp.
 */
export interface TranscriptEntry {
  speaker: 'USER' | 'COUNTERPARTY';
  text: string;
  timestamp: number;
}

/**
 * Validation error for negotiation state.
 */
export interface ValidationError {
  field: keyof NegotiationState;
  message: string;
}

const INITIAL_STATE: NegotiationState = {
  item: '',
  seller_price: null,
  user_offer: null,
  target_price: 0,
  max_price: 0,
  market_data: null,
  transcript: [],
  isResearching: false,
  researchProgress: null
};

/**
 * Hook for managing negotiation state in button-triggered advice system.
 * 
 * Features:
 * - Tracks item, prices, market data, and transcript
 * - Maintains 90-second rolling window for transcript
 * - Extracts prices from transcript text
 * - Supports AI-driven state updates
 * - Validates price constraints (target_price ≤ max_price)
 * 
 * @returns State and update functions
 */
export function useNegotiationState() {
  const [state, setState] = useState<NegotiationState>(INITIAL_STATE);
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);

  /**
   * Validate negotiation state.
   * Checks that target_price ≤ max_price.
   * 
   * @param stateToValidate - State to validate
   * @returns Array of validation errors (empty if valid)
   */
  const validateState = useCallback((stateToValidate: NegotiationState): ValidationError[] => {
    const errors: ValidationError[] = [];

    // Validate target_price ≤ max_price
    if (stateToValidate.target_price > stateToValidate.max_price && stateToValidate.max_price > 0) {
      errors.push({
        field: 'target_price',
        message: 'Target price cannot exceed maximum price'
      });
    }

    return errors;
  }, []);

  /**
   * Add a transcript entry with automatic price extraction.
   * Maintains 90-second rolling window.
   * 
   * @param speaker - Speaker label (USER or COUNTERPARTY)
   * @param text - Transcript text
   */
  const addTranscriptEntry = useCallback((
    speaker: 'USER' | 'COUNTERPARTY',
    text: string
  ) => {
    setState(prev => {
      const newEntry: TranscriptEntry = {
        speaker,
        text,
        timestamp: Date.now()
      };

      // Keep only last 90 seconds (90000ms)
      const cutoffTime = Date.now() - 90000;
      const recentTranscript = [
        ...prev.transcript.filter(e => e.timestamp > cutoffTime),
        newEntry
      ];

      // Extract price from counterparty speech
      const extractedPrice = extractPriceFromText(text);
      const newSellerPrice = speaker === 'COUNTERPARTY' && extractedPrice !== null
        ? extractedPrice
        : prev.seller_price;

      return {
        ...prev,
        transcript: recentTranscript,
        seller_price: newSellerPrice
      };
    });
  }, []);

  /**
   * Update state from AI extraction with smart merging.
   * AI analyzes transcript and extracts item, prices, etc.
   * 
   * Smart merge rules:
   * - Item: Prefer longer/more specific names (e.g., "iPhone 14 Pro Max" over "Pro Max")
   * - Prices: Only update if new value is different and valid
   * - Never overwrite good data with worse data
   * 
   * Validates state after update.
   * 
   * @param updates - Partial state updates from AI
   */
  const updateStateFromAI = useCallback((updates: Partial<NegotiationState>) => {
    setState(prev => {
      const newState = { ...prev };
      
      // Smart merge for item name
      if (updates.item !== undefined) {
        const currentItem = prev.item || '';
        const newItem = updates.item || '';
        
        // Prefer longer, more specific item names
        if (newItem.length > currentItem.length) {
          newState.item = newItem;
        } else if (currentItem.length === 0) {
          // If no current item, use new one
          newState.item = newItem;
        }
        // Otherwise keep current (it's longer/better)
      }
      
      // Smart merge for prices - only update if new value is valid and different
      if (updates.seller_price !== undefined && updates.seller_price !== null) {
        if (updates.seller_price !== prev.seller_price) {
          newState.seller_price = updates.seller_price;
        }
      }
      
      if (updates.user_offer !== undefined && updates.user_offer !== null) {
        if (updates.user_offer !== prev.user_offer) {
          newState.user_offer = updates.user_offer;
        }
      }
      
      if (updates.target_price !== undefined && updates.target_price !== null) {
        if (updates.target_price !== prev.target_price) {
          newState.target_price = updates.target_price;
        }
      }
      
      if (updates.max_price !== undefined && updates.max_price !== null) {
        if (updates.max_price !== prev.max_price) {
          newState.max_price = updates.max_price;
        }
      }
      
      // Other fields can be merged normally
      if (updates.market_data !== undefined) {
        newState.market_data = updates.market_data;
      }
      
      // Validate the new state
      const errors = validateState(newState);
      setValidationErrors(errors);
      
      return newState;
    });
  }, [validateState]);

  /**
   * Update market research data.
   * 
   * @param data - Market research results
   */
  const updateMarketData = useCallback((data: string) => {
    setState(prev => ({
      ...prev,
      market_data: data,
      isResearching: false,
      researchProgress: null
    }));
  }, []);

  /**
   * Set research state.
   * 
   * @param isResearching - Whether research is in progress
   * @param progress - Progress message
   */
  const setResearchState = useCallback((isResearching: boolean, progress: string | null = null) => {
    setState(prev => ({
      ...prev,
      isResearching,
      researchProgress: progress
    }));
  }, []);

  /**
   * Reset state to initial values.
   */
  const resetState = useCallback(() => {
    setState(INITIAL_STATE);
  }, []);

  return {
    state,
    validationErrors,
    addTranscriptEntry,
    updateStateFromAI,
    updateMarketData,
    setResearchState,
    resetState,
    validateState
  };
}

/**
 * Extract price from text using common price patterns.
 * Supports multiple currency formats.
 * 
 * @param text - Text to extract price from
 * @returns Extracted price or null if not found
 */
function extractPriceFromText(text: string): number | null {
  // Match common price patterns
  const patterns = [
    /₹\s*(\d+(?:,\d+)*)/,  // ₹50,000
    /\$\s*(\d+(?:,\d+)*)/,  // $500
    /(\d+(?:,\d+)*)\s*(?:rupees|dollars|bucks)/i,  // 500 rupees
    /(\d+(?:,\d+)*)\s*(?:rs|inr|usd)/i  // 500 rs
  ];

  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match) {
      const priceStr = match[1].replace(/,/g, '');
      const price = parseInt(priceStr, 10);
      if (!isNaN(price)) {
        return price;
      }
    }
  }

  return null;
}
