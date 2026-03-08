# Coding Conventions

**Analysis Date:** 2026-03-07

## Naming Patterns

### Files

**TypeScript/React:**
- Components use PascalCase with `.tsx` extension (e.g., `page.tsx`, `layout.tsx`)
- Utilities would use camelCase with `.ts` extension

**Python:**
- Modules use snake_case (e.g., `main.py`, `config.py`)
- Classes use PascalCase (e.g., `Config`, `Settings`)

### Directories

- **Frontend:** `app/` for Next.js App Router structure
- **Backend:** `app/` for Python package structure

### Variables and Functions

**TypeScript/JavaScript:**
- camelCase (e.g., `metadata`, `children`)

**Python:**
- snake_case (e.g., `gemini_api_key`, `log_level`)

### Types (TypeScript)

- PascalCase (e.g., `Metadata` from Next.js)

## Code Style

### Formatting

- **Tool:** Not explicitly configured
- **Defaults used:** 
  - TypeScript: 2-space indentation, semicolons
  - Python: PEP 8 (4-space indentation)

### Linting

- **Frontend:** Not configured (Next.js lint command available but not used)
- **Backend:** Not configured

### TypeScript Specific

- **Strict Mode:** Enabled in `tsconfig.json`
- **Module Resolution:** `bundler` mode
- **Path Aliases:** `@/*` mapped to project root

### Python Specific

- **Framework:** FastAPI
- **Settings:** Pydantic v2 with `pydantic-settings`
- **Logging:** Python standard `logging` module

## Import Organization

### TypeScript/React

From `frontend/app/layout.tsx`:
```typescript
import type { Metadata } from 'next'
```

Order pattern:
1. Type imports
2. React/Next.js imports
3. External libraries
4. Internal components/utilities

### Python

From `backend/app/main.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
```

Order pattern:
1. Standard library
2. Third-party packages
3. Local application imports

## Error Handling

### Python/FastAPI

**Pattern from** `backend/app/main.py`:
- Use try/except blocks for async operations
- Catch specific exceptions first
- Log errors appropriately

**HTTP Status Codes Used:**
- 200: Success
- 400: Bad Request
- 404: Not Found
- 500: Internal Server Error

### TypeScript/React

- Error boundaries for component-level errors
- Try/catch for async operations

## Logging

### Backend (Python)

**Framework:** Python `logging` module

From `backend/app/main.py`:
```python
import logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)
```

**Patterns:**
- Use appropriate log levels: DEBUG, INFO, WARNING, ERROR
- Include context in log messages
- Never log sensitive data

### Frontend

- Console logging for development
- Not explicitly configured for production

## Comments

### When to Comment

- Complex business logic
- Non-obvious workarounds
- API contracts
- Configuration requirements

### JSDoc/TSDoc

- Recommended for public functions and components
- Type definitions

### Python Docstrings

- Required for functions/classes

## Function Design

### Size Guidelines

- Maximum nesting: 3 levels
- Maximum parameters: 5 (use objects for more)
- Single responsibility

### Parameters

**Python:**
```python
def function_name(param1: type, param2: type) -> return_type:
    """Docstring."""
    pass
```

**TypeScript:**
```typescript
function functionName(param1: type, param2: type): returnType {
  // ...
}
```

### Return Values

- Always declare return types
- Use Optional[T] for nullable returns in Python
- Use T | null or undefined for TypeScript

## Module Design

### Exports

**Frontend:**
- Default exports for React pages/components
- Named exports for utilities

**Python:**
- Explicit imports of required items

### Barrel Files

- Not currently used

## Configuration

### Environment Variables

**Python (Pydantic):**
```python
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "default-model"
    
    class Config:
        env_file = ".env"

settings = Config()
```

### Path Aliases

**Frontend:** `@/*` maps to project root

## UI Component Conventions

### TailwindCSS Usage

From `tailwind.config.js`:
```javascript
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx,mdx}',
    './hooks/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  // ...
}
```

**Patterns:**
- Use utility classes for styling
- No inline styles
- Responsive design with Tailwind breakpoints

## Security Conventions

### Environment Variables (Never Commit)

- `.env` files should not be committed
- Use `.env.example` for template

### API Key Handling

```python
# Environment variable
import os
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY must be set")
```

### CORS Configuration

From `backend/app/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## WebSocket Conventions

### Backend

Not yet implemented, but planned structure:
```python
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Handle messages
```

---

*Convention analysis: 2026-03-07*
