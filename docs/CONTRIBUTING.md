# Contributing Guidelines

This document outlines the coding standards, development practices, and guidelines for contributing to the AI Accounting Job Matching project.

## Development Rules and Standards

### 1. Code Style
- Use async/await patterns consistently throughout the codebase
- Follow PEP 8 guidelines for Python code
- Include detailed docstrings for all functions and classes
- Use type hints for function parameters and return values

Example:
```python
async def process_cv(
    cv_file: UploadFile,
    user_id: int,
    *,
    include_analysis: bool = True
) -> CVAnalysisResult:
    """
    Process an uploaded CV file and optionally perform detailed analysis.

    Args:
        cv_file: The uploaded CV file object
        user_id: ID of the user uploading the CV
        include_analysis: Whether to perform detailed AI analysis

    Returns:
        CVAnalysisResult containing extracted information and optional analysis

    Raises:
        CVProcessingError: If CV parsing or analysis fails
        InvalidFileTypeError: If file type is not supported
    """
    # Implementation
```

### 2. Error Handling
- Always implement comprehensive error handling with try/except blocks
- Log errors with full context (request IDs, user IDs, parameters)
- Provide user-friendly fallback responses

Example:
```python
try:
    result = await process_cv(cv_file, user_id)
except CVProcessingError as e:
    logger.error("CV processing failed", 
                extra={
                    "user_id": user_id,
                    "file_name": cv_file.filename,
                    "error": str(e)
                })
    return UserFriendlyError(
        "We couldn't process your CV. Please ensure it's in PDF or Word format."
    )
```

### 3. Database Operations
- Use SQLAlchemy's async engine for all database operations
- Be extra careful with migrations due to shared database with accountingfirmjobs.com
- Include database connection error handling

Example:
```python
async def get_job_matches(user_id: int) -> List[JobMatch]:
    try:
        async with async_session() as session:
            result = await session.execute(
                select(JobMatch).where(JobMatch.user_id == user_id)
            )
            return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error("Database error", extra={"user_id": user_id, "error": str(e)})
        raise DatabaseOperationError("Unable to fetch job matches")
```

### 4. Testing
- Write tests for all new features
- Use pytest and pytest-asyncio
- Include both unit tests and integration tests

Example:
```python
@pytest.mark.asyncio
async def test_cv_processing():
    # Given
    test_cv = create_test_cv_file()
    
    # When
    result = await process_cv(test_cv, user_id=1)
    
    # Then
    assert result.skills is not None
    assert len(result.skills) > 0
```

### 5. Documentation
- Keep PRD.md updated with any new features or changes
- Document all API endpoints with FastAPI's built-in swagger
- Include comments for complex logic

Example:
```python
@router.post("/jobs/search/", response_model=List[JobMatch])
async def search_jobs(
    query: JobSearchQuery,
    current_user: User = Depends(get_current_user)
) -> List[JobMatch]:
    """
    Search for jobs using semantic matching.

    The search uses the following process:
    1. Generate embeddings for the search query
    2. Perform similarity search using pgvector
    3. Filter results based on user preferences
    4. Return ranked matches
    """
```

### 6. Security
- Never commit sensitive data or API keys
- Use environment variables for configuration
- Implement proper input validation

Example:
```python
# Load from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ConfigurationError("OpenAI API key not found in environment")

# Input validation
class JobSearchQuery(BaseModel):
    keywords: str = Field(..., min_length=2, max_length=200)
    location: Optional[str] = Field(None, max_length=100)
    
    @validator("keywords")
    def validate_keywords(cls, v):
        if not v.strip():
            raise ValueError("Keywords cannot be empty or whitespace")
        return v.strip()
```

### 7. Logging
- Use structured JSON logging
- Include appropriate log levels (DEBUG, INFO, WARNING, ERROR)
- Filter out sensitive information from logs

Example:
```python
# Configure JSON logger
logging.config.dictConfig({
    "version": 1,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "fmt": "%(asctime)s %(name)s %(levelname)s %(message)s"
        }
    },
    "handlers": {
        "json": {
            "class": "logging.StreamHandler",
            "formatter": "json"
        }
    },
    "loggers": {
        "": {
            "level": "INFO",
            "handlers": ["json"]
        }
    }
})

# Usage
logger.info("Processing CV", extra={
    "user_id": user.id,
    "file_type": cv_file.content_type,
    # Don't log the actual file content or sensitive user data
})
```

## Pull Request Process

1. Create a new branch for your feature or fix
2. Write or update tests as needed
3. Ensure all tests pass
4. Update documentation if necessary
5. Submit a pull request with a clear description of changes

## Questions or Issues?

If you have questions about these guidelines or need clarification, please open an issue in the repository.
