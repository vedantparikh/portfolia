# Development Guide

## 🚀 Getting Started

### Prerequisites

- **Python 3.9+**: Latest stable Python version
- **PostgreSQL 12+**: Database server
- **Redis 6+**: Caching and session storage
- **Git**: Version control
- **Docker**: Containerization (optional)

### Development Environment Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/portfolia/portfolia-api.git
   cd portfolia-api
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   # Install in development mode
   pip install -e ".[dev]"

   # Or install requirements directly
   pip install -r requirements.txt
   ```

4. **Set up pre-commit hooks**

   ```bash
   pre-commit install
   ```

5. **Configure environment**

   ```bash
   cp app/config.env.example app/.env
   # Edit .env with your local configuration
   ```

6. **Set up database**

   ```bash
   # Create database
   createdb portfolia_dev

   # Run migrations
   alembic upgrade head
   ```

7. **Start Redis**
   ```bash
   redis-server
   ```

## 🏗️ Project Structure

### Directory Layout

```
api/
├── app/                          # Main application
│   ├── main.py                   # FastAPI app instance
│   ├── config.py                 # Configuration management
│   └── core/                     # Core functionality
│       ├── database/             # Database layer
│       ├── auth/                 # Authentication
│       └── middleware/           # Custom middleware
├── api/                          # API endpoints
│   └── v1/                       # Version 1 API
├── services/                     # Business logic
├── models/                       # Pydantic schemas
├── utils/                        # Utility functions
├── tests/                        # Test suite
├── scripts/                      # Utility scripts
├── docs/                         # Documentation
├── requirements.txt              # Python dependencies
└── pyproject.toml               # Project configuration
```

### Key Components

- **`app/`**: Core application logic and configuration
- **`api/`**: HTTP API endpoints and routing
- **`services/`**: Business logic implementation
- **`models/`**: Data models and schemas
- **`utils/`**: Reusable utility functions
- **`tests/`**: Test suite and test utilities

## 🔧 Development Workflow

### 1. Feature Development

1. **Create feature branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Implement feature**

   - Follow coding standards
   - Write tests for new functionality
   - Update documentation

3. **Test your changes**

   ```bash
   pytest tests/unit/  # Unit tests
   pytest tests/integration/  # Integration tests
   pytest --cov=app --cov=app --cov=services  # With coverage
   ```

4. **Code quality checks**

   ```bash
   black .  # Code formatting
   flake8 .  # Linting
   mypy .    # Type checking
   ```

5. **Commit changes**

   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

6. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   # Create pull request on GitHub
   ```

### 2. Code Review Process

1. **Self-review**: Review your own code before submitting
2. **Peer review**: At least one other developer must review
3. **Address feedback**: Make requested changes
4. **Approval**: Get approval from reviewer
5. **Merge**: Merge to main branch

### 3. Testing Strategy

#### Test Types

- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test component interactions
- **API Tests**: Test HTTP endpoints
- **Database Tests**: Test database operations

#### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_services.py

# Run with coverage
pytest --cov=app --cov=app --cov=services --cov-report=html

# Run specific test
pytest tests/unit/test_services.py::test_create_portfolio

# Run tests matching pattern
pytest -k "portfolio"

# Run tests with markers
pytest -m "unit and not slow"
```

#### Writing Tests

```python
import pytest
from unittest.mock import Mock, patch
from services.portfolio_service import PortfolioService

class TestPortfolioService:
    def setup_method(self):
        self.mock_db = Mock()
        self.service = PortfolioService(self.mock_db)

    def test_create_portfolio_success(self):
        # Arrange
        portfolio_data = {"name": "Test Portfolio", "user_id": 1}

        # Act
        result = self.service.create_portfolio(portfolio_data)

        # Assert
        assert result is not None
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()
```

### 4. Code Quality Standards

#### Python Style Guide

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use [Black](https://black.readthedocs.io/) for code formatting
- Maximum line length: 88 characters
- Use type hints for all function parameters and return values

#### Code Formatting

```bash
# Format code with Black
black .

# Check formatting without changing files
black --check .

# Format specific file
black app/main.py
```

#### Linting

```bash
# Run flake8
flake8 .

# Run with specific configuration
flake8 --config=.flake8 .

# Fix common issues automatically
autopep8 --in-place --recursive .
```

#### Type Checking

```bash
# Run MyPy
mypy .

# Check specific module
mypy app/core/database/

# Generate type checking report
mypy --html-report reports/mypy .
```

## 🗄️ Database Development

### Database Migrations

#### Creating Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Check current migration status
alembic current
```

#### Migration Best Practices

1. **Always test migrations** on development database first
2. **Use descriptive names** for migration files
3. **Include rollback logic** for complex migrations
4. **Test both upgrade and downgrade** paths
5. **Document breaking changes** in migration comments

### Database Models

#### Creating New Models

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database.models import Base

class NewModel(Base):
    __tablename__ = "new_models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="new_models")
```

#### Model Best Practices

1. **Use appropriate column types** for data
2. **Add indexes** for frequently queried columns
3. **Define relationships** clearly
4. **Use nullable=False** for required fields
5. **Add created_at/updated_at** timestamps

## 🔐 Authentication Development

### JWT Token Management

#### Creating Tokens

```python
from datetime import datetime, timedelta, timezone
from jose import jwt
from config import settings

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt
```

#### Token Validation

```python
from jose import JWTError, jwt
from config import settings

def verify_token(token: str):
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None
```

## 📊 API Development

### Creating New Endpoints

#### 1. Define Pydantic Schemas

```python
# schemas/new_feature.py
from pydantic import BaseModel
from typing import Optional

class NewFeatureCreate(BaseModel):
    name: str
    description: Optional[str] = None

class NewFeatureResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True
```

#### 2. Implement Service Logic

```python
# services/new_feature_service.py
from typing import List, Optional
from sqlalchemy.orm import Session
from core.database.models import NewFeature
from models.new_feature import NewFeatureCreate

class NewFeatureService:
    def __init__(self, db: Session):
        self.db = db

    def create_feature(self, feature_data: NewFeatureCreate) -> NewFeature:
        feature = NewFeature(**feature_data.dict())
        self.db.add(feature)
        self.db.commit()
        self.db.refresh(feature)
        return feature
```

#### 3. Create API Router

```python
# api/v1/new_feature.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database.connection import get_db
from models.new_feature import NewFeatureCreate, NewFeatureResponse
from services.new_feature_service import NewFeatureService

router = APIRouter()

@router.post("/", response_model=NewFeatureResponse)
def create_new_feature(
    feature_data: NewFeatureCreate,
    db: Session = Depends(get_db)
):
    service = NewFeatureService(db)
    return service.create_feature(feature_data)
```

#### 4. Include Router in Main App

```python
# app/main.py
from api.v1.new_feature import router as new_feature_router

app.include_router(
    new_feature_router,
    prefix=f"{settings.api_v1_str}/new-feature",
    tags=["new-feature"]
)
```

### API Best Practices

1. **Use consistent naming** for endpoints
2. **Implement proper error handling** with HTTP status codes
3. **Add input validation** using Pydantic schemas
4. **Document endpoints** with clear descriptions
5. **Use appropriate HTTP methods** (GET, POST, PUT, DELETE)
6. **Implement pagination** for list endpoints
7. **Add rate limiting** for public endpoints

## 🧪 Testing Development

### Test Organization

#### Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── test_services/      # Service layer tests
│   ├── test_models/        # Model tests
│   └── test_utils/         # Utility tests
├── integration/             # Integration tests
│   ├── test_api/           # API endpoint tests
│   └── test_database/      # Database integration tests
├── conftest.py              # Test configuration
└── fixtures/                # Test data fixtures
```

#### Test Configuration

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app
from core.database.connection import get_db

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
```

### Test Data Management

#### Using Factories

```python
# tests/factories.py
import factory
from core.database.models import User, Portfolio

class UserFactory(factory.Factory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username = factory.Sequence(lambda n: f"user{n}")
    password_hash = factory.LazyFunction(lambda: "hashed_password")
    is_active = True
    is_verified = True

class PortfolioFactory(factory.Factory):
    class Meta:
        model = Portfolio

    name = factory.Sequence(lambda n: f"Portfolio {n}")
    description = factory.Faker("text")
    user_id = factory.SubFactory(UserFactory)
```

#### Using Fixtures

```python
@pytest.fixture
def sample_user(db):
    user = UserFactory()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def sample_portfolio(db, sample_user):
    portfolio = PortfolioFactory(user_id=sample_user.id)
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio
```

## 🔍 Debugging

### Logging

#### Structured Logging

```python
import structlog

logger = structlog.get_logger()

def some_function():
    logger.info("Processing request", user_id=123, action="create")

    try:
        # Some operation
        result = perform_operation()
        logger.info("Operation successful", result=result)
        return result
    except Exception as e:
        logger.error("Operation failed", error=str(e), user_id=123)
        raise
```

#### Debug Mode

```python
# app/config.py
class Settings(BaseSettings):
    debug: bool = False
    log_level: str = "INFO"

# app/main.py
if settings.debug:
    logging.basicConfig(level=logging.DEBUG)
```

### Debugging Tools

#### PDB (Python Debugger)

```python
import pdb

def complex_function():
    # Set breakpoint
    pdb.set_trace()

    # Your code here
    result = some_calculation()
    return result
```

#### IPDB (Enhanced Debugger)

```bash
pip install ipdb
```

```python
import ipdb

def debug_function():
    ipdb.set_trace()
    # Interactive debugging session
```

## 🚀 Performance Optimization

### Database Optimization

#### Query Optimization

```python
# Bad: N+1 query problem
portfolios = db.query(Portfolio).all()
for portfolio in portfolios:
    print(portfolio.user.username)  # Query for each portfolio

# Good: Eager loading
portfolios = db.query(Portfolio).options(
    joinedload(Portfolio.user)
).all()
for portfolio in portfolios:
    print(portfolio.user.username)  # No additional queries
```

#### Connection Pooling

```python
# app/core/database/connection.py
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True
)
```

### Caching

#### Redis Caching

```python
import redis
from config import settings

redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=0,
    decode_responses=True
)

def get_cached_data(key: str):
    cached = redis_client.get(key)
    if cached:
        return cached

    # Fetch from database
    data = fetch_from_database()

    # Cache for 1 hour
    redis_client.setex(key, 3600, data)
    return data
```

## 📚 Documentation

### Code Documentation

#### Docstrings

```python
def calculate_portfolio_value(portfolio_id: int, db: Session) -> float:
    """
    Calculate the total value of a portfolio.

    Args:
        portfolio_id: The ID of the portfolio to calculate
        db: Database session for queries

    Returns:
        float: The total portfolio value in USD

    Raises:
        ValueError: If portfolio_id is invalid
        DatabaseError: If database query fails

    Example:
        >>> value = calculate_portfolio_value(123, db_session)
        >>> print(f"Portfolio value: ${value:,.2f}")
    """
    # Implementation here
    pass
```

#### Type Hints

```python
from typing import List, Optional, Union
from decimal import Decimal

def process_transactions(
    transactions: List[Transaction],
    currency: str = "USD"
) -> Union[Decimal, None]:
    """
    Process a list of transactions and return total value.

    Args:
        transactions: List of transaction objects
        currency: Currency code for conversion

    Returns:
        Total value in specified currency, or None if no transactions
    """
    if not transactions:
        return None

    total = sum(t.amount for t in transactions)
    return convert_currency(total, "USD", currency)
```

### API Documentation

#### OpenAPI/Swagger

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="Portfolia API",
    description="Financial portfolio analysis and trading strategy API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

class PortfolioResponse(BaseModel):
    """Portfolio information response model."""

    id: int = Field(..., description="Unique portfolio identifier")
    name: str = Field(..., description="Portfolio name")
    description: Optional[str] = Field(None, description="Portfolio description")

    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "name": "My Investment Portfolio",
                "description": "Long-term investment portfolio"
            }
        }
```

## 🔒 Security Development

### Input Validation

#### Pydantic Validation

```python
from pydantic import BaseModel, validator, Field
from typing import Optional

class PortfolioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)

    @validator('name')
    def name_must_be_valid(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        if any(char in v for char in ['<', '>', '&', '"', "'"]):
            raise ValueError('Name contains invalid characters')
        return v.strip()
```

#### SQL Injection Prevention

```python
# Bad: String concatenation (vulnerable to SQL injection)
def bad_query(user_input):
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    return db.execute(query)

# Good: Parameterized queries
def good_query(user_input):
    query = "SELECT * FROM users WHERE name = :name"
    return db.execute(query, {"name": user_input})
```

### Authentication Testing

```python
def test_protected_endpoint_requires_auth(client):
    response = client.get("/api/v1/protected")
    assert response.status_code == 401

def test_protected_endpoint_with_valid_token(client, valid_token):
    headers = {"Authorization": f"Bearer {valid_token}"}
    response = client.get("/api/v1/protected", headers=headers)
    assert response.status_code == 200
```

## 🚀 Deployment Preparation

### Environment Configuration

#### Production Settings

```python
# app/config.py
class Settings(BaseSettings):
    environment: str = "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origins(self) -> List[str]:
        if self.is_production:
            return ["https://app.portfolia.com"]
        return ["http://localhost:3000", "http://localhost:8080"]
```

#### Health Checks

```python
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.version
    }

@app.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check with database connectivity."""
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
```

### Docker Configuration

#### Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Docker Compose

```yaml
version: "3.8"

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/portfolia
      - REDIS_HOST=redis
    depends_on:
      - db
      - redis
    volumes:
      - .:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=portfolia
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

## 🆘 Troubleshooting

### Common Issues

#### Import Errors

```bash
# Error: ModuleNotFoundError: No module named 'app'
export PYTHONPATH="${PYTHONPATH}:/path/to/your/project"
```

#### Database Connection Issues

```bash
# Check database connectivity
psql -h localhost -U username -d portfolia

# Check Redis connectivity
redis-cli ping
```

#### Test Failures

```bash
# Run tests with verbose output
pytest -v

# Run specific failing test
pytest tests/unit/test_specific.py::test_function -v -s

# Debug test setup
pytest --setup-show
```

### Getting Help

1. **Check logs** for error messages
2. **Review documentation** for usage examples
3. **Search existing issues** on GitHub
4. **Create new issue** with detailed information
5. **Ask in discussions** for general questions

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://pydantic-docs.helpmanual.io/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
