# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Global Development Rules

### Code Style & Formatting
- Use underscores for function and variable names (`function_name`, `variable_name`)
- Use hyphens for routes and enum labels (`route-name`, `enum-label`)
- Use modern, non-deprecated syntax when writing code
- Use TIMESTAMPTZ type consistently for time fields in database design

#### Code Quality Standards (Applied by CI/CD)
The project enforces code quality through automated checks in CI/CD pipeline:

**Critical Requirements (CI will fail):**
- **Flake8 Critical Errors**: Syntax errors, undefined variables, import issues
  - `E9` - Runtime errors (syntax errors, indentation errors)
  - `F63` - Invalid syntax in type comments
  - `F7` - List comprehension redefines variable
  - `F82` - Undefined name in `__all__`

**Style Guidelines (CI warnings only - won't block deployment):**
- **Black Formatting**: Consistent code formatting
  - Line length: 88 characters (Black default)
  - String quotes: Use double quotes by default
  - Trailing commas: Add for multi-line constructs
- **Import Sorting (isort)**: Organized import statements
  - Standard library imports first
  - Third-party imports second
  - Local application imports last
  - Alphabetical sorting within each group

#### Code Quality Commands
```bash
# Check and fix code quality (run in virtual environment)
source venv/bin/activate && black .                    # Format all Python files
source venv/bin/activate && isort .                    # Sort all imports
source venv/bin/activate && flake8 --select=E9,F63,F7,F82  # Check critical errors

# Check specific files
source venv/bin/activate && black app/api/client/v1/auth.py
source venv/bin/activate && isort app/services/client/auth.py
source venv/bin/activate && flake8 --select=E9,F63,F7,F82 app/
```

### Design Patterns
- Obtain service layer instances using dependency injection to improve testability and flexibility
- Place database model conversion in the service layer to keep the routing layer clean
- Handle transactions in the service layer to align business logic with transaction boundaries

### Language Guidelines
- Use Chinese for all code comments and documentation
- Answer questions in Chinese when requested by the user

## Development Commands

### Docker Development Environment (CRITICAL)

**ALWAYS use Docker for development and API testing. DO NOT start the server manually.**

- **Start development environment**: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d`
- **Stop development environment**: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml down`
- **View logs**: `docker-compose logs -f api`
- **API Port**: Uses `API_PORT` from `.env` file (check the .env file for the actual port number)
- **API Base URL**: `http://localhost:{API_PORT}` (where `{API_PORT}` is the value from .env)

**Important Notes**:
- All API testing MUST use the local Docker environment
- Do NOT use `python main.py` or other manual methods to start the server
- The Docker setup includes all necessary services (PostgreSQL, Redis, etc.)
- Any changes to code will be reflected automatically due to volume mounting

### Virtual Environment (CRITICAL)
- **ALWAYS activate virtual environment first**: `source venv/bin/activate`
- **Command format**: `source venv/bin/activate && python script.py`
- This applies to ALL Python operations: scripts, tests, migrations, etc.

### Server

- **Start development server**: `source venv/bin/activate && python main.py` (runs on port 8001 with hot reload)
- **Start production server**: Set `ENV=production` in .env, then `source venv/bin/activate && python main.py`

### Database (PostgreSQL)

- **Install dependencies first**: `source venv/bin/activate && pip install asyncpg psycopg2-binary`
- **Run migrations**: `source venv/bin/activate && alembic upgrade head`
- **Create new migration**: `source venv/bin/activate && alembic revision --autogenerate -m "migration_name"`
- **Downgrade migration**: `source venv/bin/activate && alembic downgrade -1`

#### Database Architecture Notes

- **Async Driver**: Uses `asyncpg` for high-performance async PostgreSQL connections
- **Migration Driver**: Uses `psycopg2` for Alembic migrations (sync operations)
- **Lazy Loading**: Engine and session creation deferred to avoid import issues during migrations
- **Connection Pooling**: Optimized pool settings for production use (20 connections, 30min recycle)

### Background Tasks

- **Start Celery worker**: `source venv/bin/activate && python celery_worker.py`
- **Start Celery beat (scheduler)**: `source venv/bin/activate && celery -A app.core.celery_app beat --loglevel=info`
- **Monitor Celery**: `source venv/bin/activate && celery -A app.core.celery_app flower`

## Architecture Overview

### API Structure

The API follows a dual-client architecture pattern:

- **Client API** (`/api/v1/`): Public-facing endpoints for client applications
- **Backoffice API** (`/api/v1/backoffice/`): Admin/management endpoints with authentication

### Documentation Access

#### Environment-Controlled Documentation Navigation
- **Development/Preview**: Root path (`/`) provides complete API documentation navigation
- **Production**: Root path hidden to prevent API structure disclosure
- **Direct Access**: All documentation endpoints remain accessible via direct URLs

#### Swagger/OpenAPI Documentation
- **Client Docs**: `/client/docs` (Swagger UI), `/client/redoc` (ReDoc)
- **Backoffice Docs**: `/backoffice/docs` (Swagger UI), `/backoffice/redoc` (ReDoc)
- **JSON Export**: `/api-docs/client.json`, `/api-docs/backoffice.json`
- **Environment Control**: Controlled by `ENV` environment variable (`development`, `preview`, `production`)

### Core Components

#### Application Layer (`app/`)

- **`route/route.py`**: Main FastAPI app factory with middleware, CORS, and global exception handlers
- **`route/router_registry.py`**: Centralized route configuration management to avoid duplication
- **`core/config.py`**: Environment-based configuration using Pydantic Settings (PostgreSQL, Redis, Celery, JWT, AWS S3, Email)
- **`core/celery_app.py`**: Celery configuration for background tasks with Redis broker

#### Configuration Layer

- **`configs/`**: Application configuration definitions separated from core system configs
  - `client_swagger_config.py`: Client API Swagger configuration
  - `backoffice_swagger_config.py`: Backoffice API Swagger configuration
  - `docs_apps.py`: Standalone documentation applications

#### Data Layer

- **`db/`**: SQLAlchemy async setup with session management and transaction contexts
  - `base.py`: PostgreSQL connection setup with lazy engine creation
  - `models.py`: Base declarative model for all database models
  - `session.py`: General transaction management and asynchronous sessions
- **`models/`**: SQLAlchemy ORM models inheriting from BaseModel (includes id, created_at, updated_at)
- **`migrations/`**: Alembic database migrations configured for PostgreSQL

#### Business Logic

- **`services/`**: Business logic separated by client/backoffice domains
- **`schemas/`**: Pydantic models for request/response validation
  - `response.py`: Unified response format using `ApiResponse`
  - `paginator.py`: Pagination utilities
- **`api/`**: Route handlers organized by client/backoffice and versioned (v1)
  - `docs_export.py`: API documentation export functionality

#### Background Processing

- **`schedule/`**: Celery task definitions and job scheduling
- **`schedule/jobs/`**: Individual scheduled task implementations

#### Script Management

- **`scripts/`**: Important production and utility scripts (committed to repository)
  - Deployment scripts, database maintenance, backup utilities
  - Permanent, reusable scripts for operations and development
- **`shell/`**: Temporary development scripts (excluded from git)
  - Quick tests, debugging helpers, one-off analysis scripts
  - Not committed to repository (in `.gitignore`)

### Response Design

#### Unified Response Format

- **ALWAYS use `ApiResponse`** from `app.schemas.response` (NOT `SuccessResponse`)
- For pagination, refer to `paginator.py`

```python
from app.schemas.response import ApiResponse  # ✓ Correct

return ApiResponse.success(data=result)
```

#### Exception Handling

- Use `APIException` from `app.exceptions.http_exceptions.py` for standardized exception responses

#### HTTP Status Code Guidelines

- **400 (Bad Request)**: User-facing errors that should be displayed to users
  - Validation errors, missing required fields, invalid input formats
  - These error messages will be shown directly to users in the frontend
- **404 (Not Found)**: Resource not found errors (NOT displayed to users)
- **500 (Internal Server Error)**: System/server errors (NOT displayed to users)

**Important**: Only 400 status code errors are displayed to end users.

### Service Layer Pattern

```python
# In route handler
@router.post("/example")
async def example_handler(
    service: ExampleService = Depends(get_example_service),  # Dependency injection
    db: AsyncSession = Depends(get_db)
):
    result = await service.process_data(db)  # Business logic in service
    return ApiResponse.success(data=result)

# In service layer
async def process_data(self, db: AsyncSession):
    async with transaction(db):  # Transaction in service layer
        # Business logic here
        pass
```

### Key Dependencies

- **FastAPI**: Web framework with OpenAPI documentation
- **SQLAlchemy**: Async ORM with PostgreSQL backend
- **asyncpg**: High-performance async PostgreSQL driver for application operations
- **psycopg2-binary**: PostgreSQL adapter for Alembic migrations (sync operations)
- **Alembic**: Database migrations
- **Celery**: Background task processing with Redis broker
- **Pydantic**: Data validation and settings management
- **Redis**: Caching and Celery broker
- **JWT**: Authentication using python-jose
- **AWS SDK**: S3 integration via boto3

### Configuration Requirements

Environment variables needed in `.env`:

- Database: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`
- Redis: `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`
- JWT: `SECRET_KEY`
- AWS: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_BUCKET_NAME`
- Email: Mail server or Brevo API credentials

### File Organization Rules

- **Important scripts**: Place in `scripts/` directory (deployment scripts, maintenance scripts, utility scripts)
  - These are permanent, reusable scripts that should be committed to the repository
  - Examples: database backup scripts, deployment automation, data migration utilities
- **Temporary scripts**: Place in `shell/` directory (test scripts, one-off scripts, debugging files)
  - These are temporary or experimental scripts that should NOT be committed to git
  - The `shell/` directory is already in `.gitignore`
  - Examples: quick test scripts, temporary analysis, debug helpers
- **Documentation**: Place in `docs/` directory (API docs, flow summaries, markdown files)
- **Always check for existing files** before creating new scripts or documentation
- **Clean up unused files** promptly to maintain directory cleanliness
- **Use descriptive names** that clearly indicate purpose and scope

### Logging & Monitoring

- Structured logging with file rotation in `logs/` directory
- Redis-based log aggregation with separate consumer thread
- Master process detection to prevent duplicate background services

## Database Migration Notes

### PostgreSQL Architecture

The application has been migrated from MySQL to PostgreSQL with the following architectural improvements:

#### Dual Driver Architecture
- **asyncpg**: Used for all application database operations (high-performance async)
- **psycopg2-binary**: Used exclusively for Alembic migrations (synchronous operations)

#### Lazy Loading Pattern
- Database engines are created lazily to prevent import issues during migrations
- Session factories are instantiated on-demand to avoid circular dependencies
- Alembic can import models without triggering async engine creation

#### Connection Pool Optimization
- **Production**: 20 connections, 10 max overflow, 30-minute recycle
- **Scheduler**: Separate engine with 5 connections for background tasks
- **Connection timeout**: 30 seconds with pre-ping health checks

#### Migration Best Practices
1. Always install both drivers before running migrations
2. Use `TIMESTAMPTZ` type for time fields (PostgreSQL best practice)
3. Test migrations in development before production deployment
4. Backup database before running migrations on production
