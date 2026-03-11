# State Validation Implementation

## Overview

This document describes the implementation of state validation for the button-triggered advice system, specifically validating that `target_price ≤ max_price`.

## Task Details

**Task:** 5.6 Implement state validation  
**Requirements:** 12.4, 12.5 (Note: Task description mentions price validation, though requirement numbers refer to voice enrollment UI)  
**Spec:** button-triggered-advice-system

## Implementation

### 1. State Manager Updates (`useNegotiationState.ts`)

Added validation functionality to the state manager hook:

#### New Interface: `ValidationError`
```typescript
export interface ValidationError {
  field: keyof NegotiationState;
  message: string;
}
```

#### New State: `validationErrors`
- Tracks current validation errors
- Updated automatically when state changes via `updateStateFromAI()`

#### New Function: `validateState()`
- Validates that `target_price ≤ max_price`
- Only validates when `max_price > 0` (to avoid false positives during initialization)
- Returns array of validation errors

#### Updated Function: `updateStateFromAI()`
- Now validates state after AI updates
- Sets validation errors automatically
- Ensures state consistency

### 2. Validation Component (`ValidationErrors.tsx`)

Created a reusable component to display validation errors:

**Features:**
- Displays validation errors with clear, actionable messages
- Shows warning icon (⚠️) for each error
- Accessible with ARIA attributes (`role="alert"`, `aria-live="polite"`)
- Returns `null` when no errors (doesn't render)
- Styled with inline CSS (can be moved to separate file)

**Usage:**
```typescript
import { ValidationErrors } from './ValidationErrors';

function MyComponent() {
  const { validationErrors } = useNegotiationState();
  
  return <ValidationErrors errors={validationErrors} />;
}
```

### 3. Tests

#### State Manager Tests (`useNegotiationState.test.ts`)
Added comprehensive validation tests:
- Valid price configuration (target ≤ max)
- Invalid price configuration (target > max)
- Edge case: equal prices (target = max)
- Edge case: zero max_price (validation skipped)
- Error message clarity

**All tests pass:** ✓ 21/21 tests

#### Component Tests (`ValidationErrors.test.tsx`)
Added component structure tests:
- Component interface validation
- Error message structure
- Multiple errors support
- Accessibility requirements
- Rendering logic

**All tests pass:** ✓ 7/7 tests

### 4. Usage Examples (`ValidationErrors.example.tsx`)

Created example implementations showing:
- Basic validation display
- Form integration with validation
- Submit button disabled when errors exist
- Validation status indicators

## Validation Rules

### Price Validation
- **Rule:** `target_price ≤ max_price`
- **Condition:** Only validates when `max_price > 0`
- **Error Message:** "Target price cannot exceed maximum price"
- **Field:** `target_price`

### Future Validation Rules
The validation system is extensible. Additional rules can be added to `validateState()`:
- Item name required
- Prices must be positive
- Seller price within reasonable range
- etc.

## Integration Points

### Where Validation Occurs
1. **AI State Updates:** Automatic validation when AI extracts prices from conversation
2. **Manual Updates:** Can be triggered manually via `validateState()` function
3. **Form Submission:** Check `validationErrors.length` before submitting

### How to Use in Components

```typescript
import { useNegotiationState } from '../../hooks/useNegotiationState';
import { ValidationErrors } from './ValidationErrors';

function NegotiationComponent() {
  const { state, validationErrors, updateStateFromAI } = useNegotiationState();
  
  // Display errors
  return (
    <div>
      <ValidationErrors errors={validationErrors} />
      
      {/* Disable actions when errors exist */}
      <button disabled={validationErrors.length > 0}>
        Ask AI
      </button>
    </div>
  );
}
```

## Files Modified/Created

### Modified
- `frontend/hooks/useNegotiationState.ts` - Added validation logic
- `frontend/hooks/useNegotiationState.test.ts` - Added validation tests

### Created
- `frontend/components/negotiation/ValidationErrors.tsx` - Error display component
- `frontend/components/negotiation/ValidationErrors.test.tsx` - Component tests
- `frontend/components/negotiation/ValidationErrors.example.tsx` - Usage examples
- `frontend/components/negotiation/VALIDATION_IMPLEMENTATION.md` - This document

## Testing Results

All tests pass with no diagnostics:
- ✓ useNegotiationState: 21/21 tests
- ✓ ValidationErrors: 7/7 tests
- ✓ No TypeScript errors
- ✓ No linting issues

## Design Decisions

1. **Validation on AI Update:** Validation runs automatically when AI updates state, ensuring immediate feedback
2. **Non-blocking:** Validation errors don't prevent state updates, allowing the system to continue operating
3. **Conditional Validation:** Only validates when `max_price > 0` to avoid false positives during initialization
4. **Accessible UI:** Component uses proper ARIA attributes for screen reader support
5. **Extensible:** Validation system designed to easily add more rules in the future

## Next Steps

To fully integrate validation into the UI:
1. Add `ValidationErrors` component to negotiation screen
2. Disable "Ask AI" button when validation errors exist
3. Consider adding validation for other fields (item name, etc.)
4. Add user-facing documentation about price constraints
