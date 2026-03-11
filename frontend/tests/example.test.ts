/**
 * Example test file to verify testing infrastructure setup
 * 
 * This file demonstrates both unit testing and property-based testing
 * with fast-check for the button-triggered-advice-system feature.
 */

import { describe, it, expect } from 'vitest';
import { fc, DEFAULT_NUM_RUNS } from './setup';

describe('Testing Infrastructure Setup', () => {
  it('should run basic unit tests', () => {
    expect(true).toBe(true);
  });

  it('should run property-based tests with fast-check', () => {
    fc.assert(
      fc.property(
        fc.integer(),
        (num) => {
          // Property: adding zero to any number returns the same number
          expect(num + 0).toBe(num);
        }
      ),
      { numRuns: DEFAULT_NUM_RUNS }
    );
  });
});
