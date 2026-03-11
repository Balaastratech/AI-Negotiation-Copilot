# Testing Infrastructure Setup

This document describes the testing infrastructure for the Button-Triggered Advice System feature.

## Overview

The testing infrastructure supports both **unit testing** and **property-based testing (PBT)** for comprehensive coverage:

- **Unit Tests**: Verify specific examples, edge cases, and integration points
- **Property Tests**: Verify universal properties across randomized inputs (minimum 100 iterations)

## Backend Testing (Python)

### Dependencies

- **pytest**: Test runner and framework
- **pytest-asyncio**: Async test support
- **hypothesis**: Property-based testing library

All dependencies are already installed via `backend/requirements-dev.txt`.

### Configuration

**pytest.ini**: Main pytest configuration
- Test discovery patterns
- Async mode configuration
- Hypothesis integration
- Coverage settings

**tests/conftest.py**: Test fixtures and Hypothesis profiles
- Environment variable setup
- Hypothesis profiles (default: 100 examples, ci: 200, dev: 50, debug: 10)
- Profile selection via `HYPOTHESIS_PROFILE` environment variable

### Running Tests

```bash
# Activate virtual environment
cd backend
.\venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate      # Linux/Mac

# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_example_setup.py

# Run with verbose output
python -m pytest -v

# Run with coverage
python -m pytest --cov=app --cov-report=html

# Run only property-based tests
python -m pytest -m property

# Run with specific Hypothesis profile
HYPOTHESIS_PROFILE=ci python -m pytest
```

### Writing Tests

**Unit Test Example:**
```python
def test_basic_functionality():
    """Test specific behavior."""
    result = my_function(input)
    assert result == expected
```

**Property Test Example:**
```python
from hypothesis import given, strategies as st

@pytest.mark.property
@given(st.integers())
def test_property(num: int):
    """
    Feature: button-triggered-advice-system
    Property 1: Description of property
    
    Validates: Requirements X.Y
    """
    # Property assertion
    assert some_property_holds(num)
```

## Frontend Testing (TypeScript)

### Dependencies

- **vitest**: Fast test runner for TypeScript/React
- **@vitest/ui**: Optional UI for test visualization
- **fast-check**: Property-based testing library

Installed via `npm install --save-dev vitest @vitest/ui fast-check`.

### Configuration

**vitest.config.ts**: Main Vitest configuration
- Test environment (Node.js)
- Coverage settings
- Path aliases

**tests/setup.ts**: Test setup and fast-check configuration
- Default number of runs: 100 iterations
- Global test utilities

### Running Tests

```bash
cd frontend

# Run all tests (single run)
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage
```

### Writing Tests

**Unit Test Example:**
```typescript
import { describe, it, expect } from 'vitest';

describe('Component', () => {
  it('should behave correctly', () => {
    const result = myFunction(input);
    expect(result).toBe(expected);
  });
});
```

**Property Test Example:**
```typescript
import { describe, it, expect } from 'vitest';
import { fc, DEFAULT_NUM_RUNS } from './setup';

describe('Property Tests', () => {
  it('should satisfy property', () => {
    /**
     * Feature: button-triggered-advice-system
     * Property 7: Speaker Classification
     * 
     * Validates: Requirements 4.2, 4.3, 4.4
     */
    fc.assert(
      fc.property(
        fc.float({ min: 0, max: 1 }),
        (similarity) => {
          const label = classifySpeaker(similarity, 0.7);
          if (similarity > 0.7) {
            expect(label).toBe('USER');
          } else {
            expect(label).toBe('COUNTERPARTY');
          }
        }
      ),
      { numRuns: DEFAULT_NUM_RUNS }
    );
  });
});
```

## Test Organization

### Backend Structure
```
backend/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest configuration
│   ├── test_example_setup.py    # Example tests
│   └── test_*.py                # Feature tests
└── pytest.ini                   # Pytest settings
```

### Frontend Structure
```
frontend/
├── tests/
│   ├── setup.ts                 # Test setup
│   └── example.test.ts          # Example tests
├── components/
│   └── *.test.tsx               # Component tests
├── lib/
│   └── *.test.ts                # Library tests
└── vitest.config.ts             # Vitest settings
```

## Property-Based Testing Guidelines

### Minimum Iterations
- All property tests MUST run at least 100 iterations (as per design document)
- Backend: Configured in `conftest.py` via Hypothesis settings
- Frontend: Use `DEFAULT_NUM_RUNS` constant from `tests/setup.ts`

### Property Test Format
Each property test MUST include:
1. Feature tag: `Feature: button-triggered-advice-system`
2. Property number and description: `Property X: Description`
3. Requirements validation: `Validates: Requirements X.Y, X.Z`

### Test Strategies
- Use appropriate generators for input data
- Test edge cases through property assertions
- Ensure properties are universal (hold for all valid inputs)
- Keep properties simple and focused

## Coverage Goals

- **Unit test coverage**: >80% of code paths
- **Property test coverage**: All 36 correctness properties from design document
- **Integration test coverage**: All critical user flows
- **Error handling coverage**: All error scenarios

## Continuous Integration

- Run unit tests on every commit
- Run property tests nightly (longer execution time)
- Run integration tests before deployment
- Monitor test execution time and optimize slow tests

## Troubleshooting

### Backend Issues

**"No module named pytest"**
- Ensure virtual environment is activated
- Run `pip install -r requirements-dev.txt`

**Hypothesis not running 100 examples**
- Check `conftest.py` has correct settings
- Verify profile is loaded correctly

### Frontend Issues

**"Cannot find module 'vitest'"**
- Run `npm install` to install dependencies
- Check `package.json` has vitest in devDependencies

**Tests not finding setup file**
- Verify `vitest.config.ts` has correct `setupFiles` path
- Check `tests/setup.ts` exists

## Next Steps

After setting up the testing infrastructure:

1. Write property tests for all 36 correctness properties
2. Write unit tests for specific scenarios and edge cases
3. Write integration tests for end-to-end flows
4. Set up CI/CD pipeline for automated testing
5. Monitor test coverage and add tests for uncovered code
