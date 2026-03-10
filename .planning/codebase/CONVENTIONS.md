# Coding Conventions

**Analysis Date:** 2026-03-10

## Naming Patterns

**Files:**
- Components: `PascalCase.tsx` - e.g., `ValidationErrors.tsx`, `NegotiationDashboard.tsx`
- Hooks: `camelCase.ts` with `use` prefix - e.g., `useNegotiationState.ts`, `useAskAI.ts`
- Types/Interfaces: `PascalCase.ts` - e.g., `types.ts`
- Tests: Same name as file with `.test.ts` or `.test.tsx` suffix - e.g., `useNegotiationState.test.ts`

**Functions:**
- Hooks: `useCamelCase` - e.g., `useNegotiationState`, `useAskAI`
- Component functions: `PascalCase` - e.g., `ValidationErrors`, `AskAIButton`
- Helper functions: `camelCase` - e.g., `extractPriceFromText`
- Event handlers: `handleCamelCase` - e.g., `handleEnrollmentComplete`, `handleSpeakerSelected`

**Variables:**
- camelCase: `negotiationState`, `validationErrors`, `isLoading`
- Boolean prefixes: `is`, `has`, `can` - e.g., `isResearching`, `hasError`
- Refs: `camelCase` with `Ref` suffix - e.g., `wsRef`, `audioManagerRef`

**Types:**
- Interfaces: PascalCase - e.g., `NegotiationState`, `ValidationError`, `TranscriptEntry`
- Type aliases: PascalCase - e.g., `Action` for reducer actions
- Enum-like unions: PascalCase with literal types - e.g., `'USER' | 'COUNTERPARTY'`

## Code Style

**Formatting:**
- No explicit Prettier config detected - using editor defaults
- Tailwind CSS for styling with utility classes
- 2-space indentation in TypeScript/TSX files

**Linting:**
- No explicit ESLint config detected
- TypeScript strict mode enabled (`"strict": true` in tsconfig.json)

**TypeScript Configuration:**
- `tsconfig.json` with strict mode enabled
- Path alias: `@/*` maps to `./` (frontend root)
- Module resolution: `bundler` for Next.js 15
- JSX: preserved for Next.js

## Import Organization

**Order:**
1. React/Next imports - `import { useState, useCallback } from 'react';`
2. External libraries - `import { Sparkles, Loader2 } from 'lucide-react';`
3. Internal hooks - `import { useNegotiationState } from '@/hooks/useNegotiationState';`
4. Internal components - `import { NegotiationDashboard } from '@/components/negotiation/NegotiationDashboard';`
5. Internal lib/utils - `import { NegotiationWebSocket } from '../lib/websocket';`

**Path Aliases:**
- Use `@/*` for frontend-relative imports - e.g., `@/hooks/useNegotiationState`
- Use relative paths for sibling modules - e.g., `../lib/types`

## Error Handling

**Patterns:**
- Validation functions return arrays of error objects
- Error objects use `ValidationError` interface: `{ field: keyof State, message: string }`
- Console logging for development debugging: `console.log()`, `console.warn()`, `console.error()`
- Custom events for cross-component communication: `window.dispatchEvent(new CustomEvent(...))`

**Validation Example:**
```typescript
const validateState = useCallback((stateToValidate: NegotiationState): ValidationError[] => {
  const errors: ValidationError[] = [];
  if (stateToValidate.target_price > stateToValidate.max_price && stateToValidate.max_price > 0) {
    errors.push({
      field: 'target_price',
      message: 'Target price cannot exceed maximum price'
    });
  }
  return errors;
}, []);
```

## Logging

**Framework:** console (no dedicated logging library)

**Patterns:**
- Feature tagging in brackets: `console.log('[Integration] STATE_UPDATE received:', event.detail)`
- Conditional warnings: `console.warn('[Integration] Validation errors:', validationErrors)`
- Error logging with context: `console.error('Voice enrollment failed:', error)`

## Comments

**When to Comment:**
- JSDoc for exported functions/hooks explaining purpose and parameters
- Inline comments for complex logic (e.g., "Keep only last 90 seconds")
- TODO comments for temporary workarounds marked with "TEMPORARILY DISABLED"

**JSDoc Usage:**
```typescript
/**
 * Hook for managing negotiation state in button-triggered advice system.
 * 
 * Features:
 * - Tracks item, prices, market data, and transcript
 * - Maintains 90-second rolling window for transcript
 * - Extracts prices from transcript text
 * 
 * @returns State and update functions
 */
export function useNegotiationState() { }
```

## Function Design

**Size:** Keep functions focused and under 100 lines where possible

**Parameters:**
- Use explicit types for all parameters
- Destructuring for object parameters in components
- Optional parameters marked with `?` - e.g., `progress?: string | null`

**Return Values:**
- Hooks return object with named properties - e.g., `{ state, validationErrors, addTranscriptEntry }`
- Components return JSX or null

## Module Design

**Exports:**
- Named exports for components and hooks
- Default exports for page components (Next.js convention)
- Interface exports for types

**Barrel Files:** Not detected (no `index.ts` barrel files)

## Component Patterns

**Props Interface:**
```typescript
interface ValidationErrorsProps {
  errors: ValidationError[];
}
```

**Functional Components:**
- Arrow functions with explicit type annotations
- Destructured props in function signature

**State Management:**
- `useState` for local component state
- `useReducer` for complex state logic (see `useNegotiation.ts`)
- Custom hooks for reusable stateful logic

---

*Convention analysis: 2026-03-10*
