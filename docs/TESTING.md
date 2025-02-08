# Testing Guidelines

## Overview

This document outlines testing best practices for the AI Accounting Job Matching project. Our testing strategy emphasizes test isolation, proper mocking, and comprehensive coverage while respecting the shared database architecture with accountingfirmjobs.com.

## Test Types

### 1. Unit Tests
- Test individual components in isolation
- Use mocks for external dependencies
- Focus on business logic
- Located in `tests/services/` and `tests/models/`

### 2. Integration Tests
- Test component interactions
- Use test database
- Focus on data flow and API endpoints
- Located in `tests/api/` and `tests/integration/`

## Test Environment

### Database Configuration
- Use a separate test database
- Set `TEST_DATABASE_URL` in `.env`
- Never modify production database during tests
- Respect read-only tables (e.g., `JobsApp_job`)

### Environment Variables
- Set `BOT_ENV=test` during tests
- Use test-specific API keys
- Configure lower rate limits for external services

## Best Practices

### 1. Test Isolation
```python
# Good: Use mock session
@pytest.fixture
def service(mock_db_session):
    return MyService(mock_db_session)

# Bad: Direct database access
@pytest.fixture
def service(db_session):
    return MyService(db_session)
```

### 2. Mock External Services
```python
# Good: Mock OpenAI API
@pytest.fixture
def mock_openai():
    mock = MagicMock()
    mock.embeddings.create = AsyncMock(return_value=...)
    return mock

# Bad: Real API calls
client = AsyncOpenAI()
```

### 3. Test Data
```python
# Good: Use fixtures
@pytest.fixture
def sample_job_data():
    return {...}  # Complete test data

# Bad: Incomplete test data
job = Job(title="Test")  # Missing required fields
```

### 4. Async Testing
```python
# Good: Use pytest-asyncio
@pytest.mark.asyncio
async def test_async_function():
    result = await my_async_function()
    assert result

# Bad: Sync wrapper
def test_async_function():
    result = asyncio.run(my_async_function())  # Don't do this
```

### 5. Error Handling
```python
# Good: Test error cases
@pytest.mark.asyncio
async def test_error_handling():
    with pytest.raises(ValueError):
        await function_that_should_fail()

# Bad: Only testing happy path
async def test_only_success():
    result = await function()  # What about errors?
```

## Event Loop and Database Management

### 1. Event Loop Configuration
```python
@pytest_asyncio.fixture(scope="function")
async def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
```

### 2. Database Session Management
```python
@pytest_asyncio.fixture
async def mock_db_session():
    """Mock database session with proper cleanup."""
    session = AsyncMock()
    async def mock_close():
        await session.close()
    session.close = mock_close
    try:
        yield session
    finally:
        await session.close()
```

### 3. Test Structure with Resource Cleanup
```python
@pytest.mark.asyncio
async def test_example(mock_db_session):
    try:
        # Test logic here
        result = await my_function()
        assert result
    finally:
        # Always clean up resources
        await mock_db_session.close()
```

### Common Pitfalls

1. **Event Loop Issues**
   - Always use `@pytest.mark.asyncio` for async tests
   - Don't mix sync and async code in tests
   - Use proper event loop fixtures
   - Clean up event loops after tests

2. **Database Connection Management**
   - Always close database sessions
   - Use try/finally blocks for cleanup
   - Mock database operations properly
   - Handle transaction rollbacks

3. **Resource Cleanup**
   - Close all connections and resources
   - Use context managers when possible
   - Implement proper teardown in fixtures
   - Clean up temporary files and data

4. **Async Mocking**
   - Use `AsyncMock` for async functions
   - Mock both success and error cases
   - Handle async context managers
   - Test timeout scenarios

### Best Practices for Telegram Bot Testing

1. **Update and Context Mocking**
```python
@pytest.fixture
def mock_update():
    mock = MagicMock(spec=Update)
    mock.effective_user = MagicMock(spec=TelegramUser)
    mock.effective_user.id = 12345
    mock.effective_chat = MagicMock(spec=Chat)
    mock.effective_chat.id = 12345
    return mock

@pytest.fixture
def mock_context():
    mock = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock.bot = MagicMock()
    return mock
```

2. **Command Testing**
```python
@pytest.mark.asyncio
async def test_command(mock_update, mock_context, mock_db_session):
    try:
        # Setup
        bot = JobMatchingBot()
        
        with patch("app.telegram_bot.get_session") as mock_get_session:
            # Configure session
            mock_get_session.return_value.__aenter__.return_value = mock_db_session
            mock_get_session.return_value.__aexit__.return_value = None
            
            # Execute
            await bot._command(mock_update, mock_context)
            
            # Assert
            mock_context.bot.send_message.assert_called_once()
    finally:
        await mock_db_session.close()
```

3. **Error Scenarios**
- Test database errors
- Test user not found cases
- Test invalid input
- Test rate limiting
- Test timeout scenarios

## Test Structure

### 1. File Organization
```
tests/
├── conftest.py         # Shared fixtures
├── api/               # API tests
├── services/          # Service layer tests
├── models/           # Model tests
└── integration/      # Integration tests
```

### 2. Naming Conventions
- Test files: `test_*.py`
- Test functions: `test_*`
- Test classes: `Test*`
- Fixtures: Descriptive names like `sample_job`, `mock_db_session`

### 3. Fixture Scopes
- `function`: Default, isolated tests
- `class`: Shared class setup
- `module`: Module-level resources
- `session`: Long-lived resources

## Running Tests

### Local Development
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/services/test_job_matching.py

# Run with coverage
pytest --cov=app tests/

# Run with verbose output
pytest -v
```

### CI/CD Pipeline
- Tests must pass before merge
- Coverage requirements: 80%
- Integration tests run on staging database

## Mocking Strategy

### 1. Database Layer
- Mock `AsyncSession` for unit tests
- Use test database for integration tests
- Never modify production tables

### 2. External Services
- Mock OpenAI API calls
- Mock Telegram Bot API
- Use test credentials when available

### 3. Time-dependent Operations
- Use `freezegun` for time-sensitive tests
- Mock datetime in fixtures

## Common Patterns

### 1. Testing Services
```python
@pytest.mark.asyncio
async def test_service_method(
    service,
    mock_db_session,
    sample_data
):
    # Arrange
    mock_db_session.execute.return_value.scalar.return_value = sample_data
    
    # Act
    result = await service.method()
    
    # Assert
    assert result.id == sample_data.id
```

### 2. Testing Models
```python
def test_model_validation(sample_data):
    # Test required fields
    with pytest.raises(ValueError):
        Model(incomplete_data)
    
    # Test valid data
    model = Model(**sample_data)
    assert model.field == sample_data["field"]
```

### 3. Testing API Endpoints
```python
@pytest.mark.asyncio
async def test_api_endpoint(client, mock_service):
    # Arrange
    mock_service.method.return_value = expected_result
    
    # Act
    response = await client.get("/api/endpoint")
    
    # Assert
    assert response.status_code == 200
    assert response.json() == expected_result
```

## Troubleshooting

### Common Issues

1. **Database Conflicts**
   - Ensure using test database
   - Check table permissions
   - Verify rollback after tests

2. **Async Test Failures**
   - Use proper async fixtures
   - Await all async calls
   - Check event loop conflicts

3. **Mock Issues**
   - Verify mock return values
   - Check mock call assertions
   - Reset mocks between tests

## Security Considerations

1. **Sensitive Data**
   - Never use production credentials
   - Mask sensitive data in logs
   - Use dummy data for tests

2. **API Keys**
   - Use test API keys
   - Mock external service calls
   - Rotate test credentials regularly

## Maintenance

1. **Regular Updates**
   - Keep dependencies updated
   - Review test coverage
   - Update test data regularly

2. **Documentation**
   - Keep this guide updated
   - Document new patterns
   - Include examples

3. **Clean Up**
   - Remove obsolete tests
   - Clean test data
   - Update mock data

## Test Data Management

### 1. User Data
```python
@pytest.fixture
def sample_user():
    return User(
        id=1,
        telegram_id=12345,
        username="testuser",
        first_name="Test",
        last_name="User",
        cv_text="Sample CV text",
        notification_preferences={
            "notification_type": "telegram",
            "email_frequency": "daily",
            "min_match_score": 0.7
        },
        search_preferences={
            "desired_roles": ["Accountant"],
            "locations": ["London"],
            "min_salary": 50000
        }
    )
```

### 2. Job Data
```python
@pytest.fixture
def sample_job():
    return {
        "title": "Senior Accountant",
        "company": "Test Corp",
        "location": "London",
        "salary_min": 50000,
        "salary_max": 70000,
        "description": "Sample job description",
        "requirements": ["ACCA", "5 years experience"],
        "score": 0.85
    }
```
