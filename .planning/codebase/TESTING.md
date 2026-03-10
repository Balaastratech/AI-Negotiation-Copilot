# Testing Patterns

**Analysis Date:** 2026-03-10

## Test Framework

**Runner:**
- Vitest 4.0.18
- Config: `frontend/vitest.config.ts`

**Assertion Library:**
- Vitest built-in (`expect`)

**Property-Based Testing:**
- fast-check 4.5.3 for property-based tests
- Default 100 iterations per property test

**Run Commands:**
```bash
npm run test              # Run all tests (vitest --run)
npm run test:watch       # Watch mode (vitest)
npm run test:ui          # UI mode (vitest --ui)
npm run test:coverage    # Coverage (vitest --coverage)
```

## Test File Organization

**Location:**
- Co-located with source files
- Test files in same directory as implementation

**Naming:**
- `.test.ts` for TypeScript test files
- `.test.tsx` for React component tests
- Example files use `.example.tsx` suffix (e.g., `ValidationErrors.example.tsx`)

**Structure:**
```
frontend/
├── hooks/
│   ├── useNegotiationState.ts
│   └── useNegotiationState.test.ts
├── components/
│   └── negotiation/
│       ├── ValidationErrors.tsx
│       └── ValidationErrors.test.tsx
└── tests/
    ├── setup.ts
    └── example.test.ts
```

## Test Structure

**Suite Organization:**
```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('ComponentName', () => {
  beforeEach(() => {
    // Setup before each test
    vi.spyOn(Date, 'now').mockReturnValue(mockDate);
  });

  describe('feature group', () => {
    /**
     * Test: Description
     * Validates: Requirement or feature being tested
     */
    it('should do something specific', () => {
      // Arrange
      const input = 'test value';
      
      // Act
      const result = processInput(input);
      
      // Assert
      expect(result).toBe('expected');
    });
  });
});
```

**Patterns:**

1. **Setup/teardown**: `beforeEach` for resetting state and mocking
2. **Nested describe**: Group related tests by feature
3. **JSDoc comments**: Document what each test validates
4. **Requirement references**: Include requirement numbers in comments

## Mocking

**Framework:** Vitest built-in (`vi`)

**Patterns:**

```typescript
// Spy on Date.now()
vi.spyOn(Date, 'now').mockReturnValue(mockDate);

// Mock implementation
vi.spyOn(obj, 'method').mockImplementation(() => 'mocked');

// Restore after test
vi.restoreAllMocks();
```

**What to Mock:**
- Time-dependent functions (`Date.now()`)
- Browser APIs (when running in node environment)
- External services

**What NOT to Mock:**
- Internal helper functions that are the test subject
- Simple data transformations

## Fixtures and Factories

**Test Data:**
```typescript
// Inline fixtures for simple tests
const initialState: NegotiationState = {
  item: '',
  seller_price: null,
  target_price: 0,
  max_price: 0,
  market_data: null,
  transcript: []
};

// Test-specific data
const mockTranscript = [
  { speaker: 'USER', text: 'Old message', timestamp: mockDate - 91000 },
  { speaker: 'USER', text: 'Recent message', timestamp: mockDate - 30000 }
];
```

**Location:**
- Inline in test files for simplicity
- Shared utilities in `frontend/tests/setup.ts`

## Setup File

**File:** `frontend/tests/setup.ts`

```typescript
/**
 * Test setup file for Vitest
 * 
 * This file is automatically loaded before running tests.
 * Configure global test utilities and mocks here.
 */

import fc from 'fast-check';

export const DEFAULT_NUM_RUNS = 100;
export { fc };
```

## Coverage

**Requirements:** Not explicitly enforced

**View Coverage:**
```bash
npm run test:coverage
```

**Config (vitest.config.ts):**
```typescript
coverage: {
  provider: 'v8',
  reporter: ['text', 'json', 'html'],
  exclude: [
    'node_modules/',
    '.next/',
    'coverage/',
    '**/*.config.{js,ts}',
    '**/*.d.ts',
  ],
}
```

## Test Types

**Unit Tests:**
- Test individual functions and hooks
- Test state management logic
- Test price extraction utilities
- Run in Node environment

**Component Tests:**
- Currently testing component interfaces and logic
- Full DOM rendering tests require `@testing-library/react` (not installed)
- Test props interfaces, error structures, rendering conditions

**Property-Based Tests:**
- Use fast-check with `fc.assert()` and `fc.property()`
- Example from `example.test.ts`:
```typescript
it('should run property-based tests with fast-check', () => {
  fc.assert(
    fc.property(
      fc.integer(),
      (num) => {
        expect(num + 0).toBe(num);
      }
    ),
    { numRuns: DEFAULT_NUM_RUNS }
  );
});
```

## Common Patterns

**Async Testing:**
```typescript
// Not currently used - synchronous state updates
// For async operations, would use async/await with expect
```

**Error Testing:**
```typescript
it('should handle error case', () => {
  const state: NegotiationState = {
    item: 'Test Item',
    seller_price: null,
    target_price: 60000,  // > max_price
    max_price: 50000,
    market_data: null,
    transcript: []
  };

  const isValid = state.target_price <= state.max_price;
  expect(isValid).toBe(false);
});
```

**Type Testing:**
```typescript
// Test type structures by creating instances
const error: ValidationError = {
  field: 'target_price',
  message: 'Target price cannot exceed maximum price'
};

expect(error).toHaveProperty('field');
expect(error).toHaveProperty('message');
```

## Environment

**Test Environment:** `node` (not `jsdom`)

**Implications:**
- No DOM APIs available in tests
- Component tests test logic/interfaces, not rendering
- Would need `@testing-library/react` for DOM testing

---

*Testing analysis: 2026-03-10*
