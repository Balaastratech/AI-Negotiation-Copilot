# Testing Patterns

**Analysis Date:** 2026-03-07

## Test Framework

### Current State

**No test frameworks are currently installed or configured.**

Both frontend and backend projects need testing infrastructure to be set up.

### Backend (Python) - To Be Configured

**Recommended:**
- **Framework:** pytest
- **Async Support:** pytest-asyncio
- **HTTP Testing:** httpx (for FastAPI testing)

**Installation would be:**
```bash
pip install pytest pytest-asyncio httpx
```

**Run Commands (when configured):**
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_main.py

# Run with verbose output
pytest -v
```

### Frontend (TypeScript/React) - To Be Configured

**Recommended:**
- **Framework:** Jest (comes with Next.js) or Vitest
- **Testing Library:** @testing-library/react
- **E2E (future):** Playwright or Cypress

**Installation would be:**
```bash
npm install --save-dev @testing-library/react @testing-library/user-event
npm install --save-dev jest @types/jest ts-jest
# OR use Vitest
npm install --save-dev vitest @testing-library/react jsdom
```

**Run Commands (when configured):**
```bash
# Run all tests
npm test

# Watch mode
npm test -- --watch

# Coverage
npm test -- --coverage
```

## Test File Organization

### Recommended Structure

**Backend:**
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── config.py
└── tests/
    ├── __init__.py
    ├── test_main.py
    ├── test_config.py
    ├── conftest.py          # Shared fixtures
    └── services/
        └── test_gemini_client.py
```

**Frontend:**
```
frontend/
├── app/
│   ├── page.tsx
│   └── layout.tsx
└── components/
    └── __tests__/
        └── ComponentName.test.tsx
```

### Naming

- `test_*.py` for Python (pytest convention)
- `*.test.ts` or `*.test.tsx` for TypeScript

## Test Structure

### Python (pytest)

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient

from app.main import app
from app.config import Config


class TestMain:
    """Test suite for main application."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        return Config(
            GEMINI_API_KEY="test-key",
            GEMINI_MODEL="test-model",
            CORS_ORIGINS=["http://localhost:3000"],
            LOG_LEVEL="INFO"
        )

    @pytest.mark.asyncio
    async def test_health_check(self, mock_settings):
        """Test health endpoint returns healthy status."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}
```

### TypeScript (Jest)

```typescript
import { render, screen } from '@testing-library/react';

describe('Home Page', () => {
  it('renders the page title', () => {
    // This is a placeholder - actual page content will need testing
    expect(true).toBe(true);
  });
});
```

## Mocking

### Framework Recommendations

**Python:**
- `unittest.mock` (MagicMock, AsyncMock)
- `pytest-mock` for enhanced fixture

**TypeScript:**
- `jest.fn()` for functions
- `jest.mock()` for modules

### Python Mocking Patterns

```python
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# Mock async function
@pytest.mark.asyncio
async def test_example():
    mock_function = AsyncMock(return_value="result")
    result = await mock_function()
    assert result == "result"

# Mock external dependency
def test_external_api():
    with patch('module.function') as mock_func:
        mock_func.return_value = "mocked"
        # test code
```

### TypeScript Mocking Patterns

```typescript
// Mock function
const mockFn = jest.fn().mockResolvedValue('result');

// Mock module
jest.mock('@/lib/example', () => ({
  exampleFunction: jest.fn(),
}));

// Mock React component
jest.mock('./Component', () => ({
  Component: () => <div>Mocked</div>,
}));
```

## Fixtures and Factories

### Python Fixtures

```python
# backend/tests/conftest.py
import pytest

@pytest.fixture
def test_app():
    """Create test FastAPI app."""
    from app.main import app
    return app

@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        "GEMINI_API_KEY": "test-key",
        "GEMINI_MODEL": "test-model",
        "CORS_ORIGINS": ["http://localhost:3000"],
    }
```

### TypeScript Factories

```typescript
// Simple factory pattern
const createMockConfig = (overrides = {}) => ({
  apiKey: 'test-key',
  model: 'gemini-2.0-flash',
  ...overrides,
});
```

## Coverage

### Recommendations

- Minimum 70% line coverage
- Critical paths should have higher coverage:
  - API endpoints
  - WebSocket message handling
  - Configuration validation
  - Error handling paths

### View Coverage

**Backend:**
```bash
pytest --cov=app --cov-report=term-missing
```

**Frontend:**
```bash
npm test -- --coverage
```

## Test Types

### Unit Tests

**Scope:** Individual functions, classes in isolation
**Approach:** Mock all external dependencies

### Integration Tests

**Scope:** Multiple units working together
**Approach:** Use real implementations, mock external services

**Backend Example:**
```python
@pytest.mark.asyncio
async def test_health_endpoint_integration():
    """Test health endpoint with real app."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        
        assert response.status_code == 200
```

### E2E Tests

- Not currently set up
- Recommendation: Playwright or Cypress for future

## Common Patterns

### Async Testing (Python)

```python
@pytest.mark.asyncio
async def test_async_operation():
    """Test async function."""
    result = await async_function()
    assert result is not None
```

### Error Testing (Python)

```python
@pytest.mark.asyncio
async def test_handles_error():
    """Test error handling."""
    with pytest.raises(ValueError):
        await invalid_operation()
```

### WebSocket Testing (Python - Future)

```python
@pytest.mark.asyncio
async def test_websocket_connection():
    """Test WebSocket endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with client.websocket_connect("/ws") as ws:
            # Test connection
            pass
```

## Current Test Gaps

### Missing Test Infrastructure

1. **Backend:**
   - No pytest installation
   - No test directory structure
   - No conftest.py fixtures
   - No test files

2. **Frontend:**
   - No Jest/Vitest configuration
   - No test directory structure
   - No test files
   - No @testing-library/react installed

### Priority Areas for Testing

1. **Backend API endpoints** (`/health`, `/api/health`)
2. **Configuration loading** (`config.py`)
3. **CORS middleware** behavior
4. **Logging configuration**

---

*Testing analysis: 2026-03-07*
