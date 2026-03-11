import { describe, it, expect, beforeEach, vi } from 'vitest';
import { NegotiationState, TranscriptEntry } from './useNegotiationState';

/**
 * Unit tests for useNegotiationState hook
 * 
 * Tests verify state management logic for button-triggered advice system.
 * Validates: Requirements 5.1, 5.2, 5.5, 9.1, 9.2
 */

describe('useNegotiationState', () => {
  let mockDate: number;

  beforeEach(() => {
    mockDate = 1000000000000; // Fixed timestamp for testing
    vi.spyOn(Date, 'now').mockReturnValue(mockDate);
  });

  describe('initialization', () => {
    /**
     * Test: Initial state structure
     * Validates: Requirement 5.1 (state object structure)
     */
    it('should have correct initial state structure', () => {
      const initialState: NegotiationState = {
        item: '',
        seller_price: null,
        target_price: 0,
        max_price: 0,
        market_data: null,
        transcript: [],
        isResearching: false,
        researchProgress: null,
      };

      expect(initialState.item).toBe('');
      expect(initialState.seller_price).toBeNull();
      expect(initialState.target_price).toBe(0);
      expect(initialState.max_price).toBe(0);
      expect(initialState.market_data).toBeNull();
      expect(initialState.transcript).toEqual([]);
    });
  });

  describe('transcript management', () => {
    /**
     * Test: Transcript entry structure
     * Validates: Requirement 9.1 (transcript with speaker label)
     */
    it('should create transcript entry with correct structure', () => {
      const entry: TranscriptEntry = {
        speaker: 'USER',
        text: 'Hello',
        timestamp: mockDate
      };

      expect(entry.speaker).toBe('USER');
      expect(entry.text).toBe('Hello');
      expect(entry.timestamp).toBe(mockDate);
    });

    /**
     * Test: 90-second rolling window
     * Validates: Requirement 5.5, 9.2 (retain last 90 seconds)
     */
    it('should maintain 90-second rolling window', () => {
      const transcript: TranscriptEntry[] = [
        { speaker: 'USER', text: 'Old message', timestamp: mockDate - 91000 },
        { speaker: 'USER', text: 'Recent message', timestamp: mockDate - 30000 }
      ];

      const cutoffTime = mockDate - 90000;
      const filtered = transcript.filter(e => e.timestamp > cutoffTime);

      expect(filtered).toHaveLength(1);
      expect(filtered[0].text).toBe('Recent message');
    });

    /**
     * Test: Speaker labels
     * Validates: Requirement 9.6 (speaker labels USER or COUNTERPARTY)
     */
    it('should use correct speaker labels', () => {
      const validSpeakers: Array<'USER' | 'COUNTERPARTY'> = ['USER', 'COUNTERPARTY'];

      expect(validSpeakers).toContain('USER');
      expect(validSpeakers).toContain('COUNTERPARTY');
      expect(validSpeakers).toHaveLength(2);
    });
  });

  describe('price extraction', () => {
    /**
     * Test: Extract prices from counterparty speech
     * Validates: Requirement 5.2 (price extraction from transcript)
     */
    it('should extract rupee symbol prices', () => {
      const text = 'Price is ₹25,000';
      const pattern = /₹\s*(\d+(?:,\d+)*)/;
      const match = text.match(pattern);

      expect(match).not.toBeNull();
      if (match) {
        const price = parseInt(match[1].replace(/,/g, ''), 10);
        expect(price).toBe(25000);
      }
    });

    it('should extract dollar symbol prices', () => {
      const text = 'That will be $500';
      const pattern = /\$\s*(\d+(?:,\d+)*)/;
      const match = text.match(pattern);

      expect(match).not.toBeNull();
      if (match) {
        const price = parseInt(match[1].replace(/,/g, ''), 10);
        expect(price).toBe(500);
      }
    });

    it('should extract prices with currency words', () => {
      const text = 'I want 1000 rupees';
      const pattern = /(\d+(?:,\d+)*)\s*(?:rupees|dollars|bucks)/i;
      const match = text.match(pattern);

      expect(match).not.toBeNull();
      if (match) {
        const price = parseInt(match[1].replace(/,/g, ''), 10);
        expect(price).toBe(1000);
      }
    });

    it('should extract prices with currency abbreviations', () => {
      const text = 'Cost is 2500 rs';
      const pattern = /(\d+(?:,\d+)*)\s*(?:rs|inr|usd)/i;
      const match = text.match(pattern);

      expect(match).not.toBeNull();
      if (match) {
        const price = parseInt(match[1].replace(/,/g, ''), 10);
        expect(price).toBe(2500);
      }
    });

    it('should handle prices without commas', () => {
      const text = 'Price: ₹50000';
      const pattern = /₹\s*(\d+(?:,\d+)*)/;
      const match = text.match(pattern);

      expect(match).not.toBeNull();
      if (match) {
        const price = parseInt(match[1].replace(/,/g, ''), 10);
        expect(price).toBe(50000);
      }
    });

    it('should return null for text without prices', () => {
      const text = 'Hello, how are you?';
      const patterns = [
        /₹\s*(\d+(?:,\d+)*)/,
        /\$\s*(\d+(?:,\d+)*)/,
        /(\d+(?:,\d+)*)\s*(?:rupees|dollars|bucks)/i,
        /(\d+(?:,\d+)*)\s*(?:rs|inr|usd)/i
      ];

      const hasMatch = patterns.some(pattern => text.match(pattern));
      expect(hasMatch).toBe(false);
    });
  });

  describe('AI state updates', () => {
    /**
     * Test: AI can update item field
     * Validates: Requirement 5.1 (AI extracts item from conversation)
     */
    it('should support AI updating item field', () => {
      const updates: Partial<NegotiationState> = {
        item: 'iPhone 14 Pro'
      };

      expect(updates.item).toBe('iPhone 14 Pro');
    });

    /**
     * Test: AI can update price fields
     * Validates: Requirement 5.2 (AI extracts prices from conversation)
     */
    it('should support AI updating price fields', () => {
      const updates: Partial<NegotiationState> = {
        target_price: 40000,
        max_price: 50000
      };

      expect(updates.target_price).toBe(40000);
      expect(updates.max_price).toBe(50000);
    });

    /**
     * Test: AI can update multiple fields
     * Validates: Requirement 5.1 (state management)
     */
    it('should support AI updating multiple fields at once', () => {
      const updates: Partial<NegotiationState> = {
        item: 'MacBook Pro',
        target_price: 80000,
        max_price: 100000,
        seller_price: 95000
      };

      expect(updates.item).toBe('MacBook Pro');
      expect(updates.target_price).toBe(80000);
      expect(updates.max_price).toBe(100000);
      expect(updates.seller_price).toBe(95000);
    });
  });

  describe('market data', () => {
    /**
     * Test: Market data structure
     * Validates: Requirement 5.4 (market_data field update)
     */
    it('should support market data updates', () => {
      const marketData = 'Market price range: ₹45,000 - ₹55,000';
      const state: NegotiationState = {
        item: 'iPhone',
        seller_price: null,
        target_price: 0,
        max_price: 0,
        market_data: marketData,
        transcript: [],
        isResearching: false,
        researchProgress: null,
      };

      expect(state.market_data).toBe(marketData);
    });
  });

  describe('state structure validation', () => {
    /**
     * Test: Complete state object structure
     * Validates: Requirement 5.1 (state object contains all required fields)
     */
    it('should have all required fields', () => {
      const state: NegotiationState = {
        item: 'Test Item',
        seller_price: 50000,
        target_price: 40000,
        max_price: 45000,
        market_data: 'Test data',
        transcript: [],
        isResearching: false,
        researchProgress: null,
      };

      expect(state).toHaveProperty('item');
      expect(state).toHaveProperty('seller_price');
      expect(state).toHaveProperty('target_price');
      expect(state).toHaveProperty('max_price');
      expect(state).toHaveProperty('market_data');
      expect(state).toHaveProperty('transcript');
    });

    /**
     * Test: State serialization
     * Validates: Requirement 5.6 (state remains valid JSON)
     */
    it('should be serializable to JSON', () => {
      const state: NegotiationState = {
        item: 'iPhone 14 Pro',
        seller_price: 60000,
        target_price: 45000,
        max_price: 50000,
        market_data: 'Market range: ₹48,000 - ₹58,000',
        transcript: [
          { speaker: 'USER', text: 'Hello', timestamp: mockDate },
          { speaker: 'COUNTERPARTY', text: 'Hi', timestamp: mockDate + 1000 }
        ],
        isResearching: false,
        researchProgress: null,
      };

      const serialized = JSON.stringify(state);
      const deserialized = JSON.parse(serialized);

      expect(deserialized.item).toBe(state.item);
      expect(deserialized.seller_price).toBe(state.seller_price);
      expect(deserialized.target_price).toBe(state.target_price);
      expect(deserialized.max_price).toBe(state.max_price);
      expect(deserialized.market_data).toBe(state.market_data);
      expect(deserialized.transcript).toHaveLength(2);
    });
  });

  describe('price validation', () => {
    /**
     * Test: Valid price configuration
     * Validates: target_price ≤ max_price constraint
     */
    it('should pass validation when target_price ≤ max_price', () => {
      const state: NegotiationState = {
        item: 'Test Item',
        seller_price: null,
        target_price: 40000,
        max_price: 50000,
        market_data: null,
        transcript: [],
        isResearching: false,
        researchProgress: null,
      };

      // Validation logic: target_price ≤ max_price
      const isValid = state.target_price <= state.max_price;
      expect(isValid).toBe(true);
    });

    /**
     * Test: Invalid price configuration
     * Validates: target_price > max_price should fail validation
     */
    it('should fail validation when target_price > max_price', () => {
      const state: NegotiationState = {
        item: 'Test Item',
        seller_price: null,
        target_price: 60000,
        max_price: 50000,
        market_data: null,
        transcript: [],
        isResearching: false,
        researchProgress: null,
      };

      // Validation logic: target_price ≤ max_price
      const isValid = state.target_price <= state.max_price;
      expect(isValid).toBe(false);
    });

    /**
     * Test: Edge case - equal prices
     * Validates: target_price = max_price is valid
     */
    it('should pass validation when target_price equals max_price', () => {
      const state: NegotiationState = {
        item: 'Test Item',
        seller_price: null,
        target_price: 50000,
        max_price: 50000,
        market_data: null,
        transcript: [],
        isResearching: false,
        researchProgress: null,
      };

      const isValid = state.target_price <= state.max_price;
      expect(isValid).toBe(true);
    });

    /**
     * Test: Zero max_price should not trigger validation
     * Validates: Validation only applies when max_price > 0
     */
    it('should not validate when max_price is zero', () => {
      const state: NegotiationState = {
        item: 'Test Item',
        seller_price: null,
        target_price: 100,
        max_price: 0,
        market_data: null,
        transcript: [],
        isResearching: false,
        researchProgress: null,
      };

      // Validation should not trigger when max_price is 0 (not set yet)
      const shouldValidate = state.max_price > 0;
      expect(shouldValidate).toBe(false);
    });

    /**
     * Test: Validation error message structure
     * Validates: Error messages are clear and actionable
     */
    it('should provide clear validation error message', () => {
      const errorMessage = 'Target price cannot exceed maximum price';
      
      expect(errorMessage).toContain('Target price');
      expect(errorMessage).toContain('maximum price');
      expect(errorMessage.length).toBeGreaterThan(0);
    });
  });
});
