# Development Rules and Guidelines

This document combines project-specific rules with general development guidelines for the AI‑Powered Accounting Job Matching Bot. It should be read in conjunction with [PRD.md](PRD.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## 1. General Principles

### Modularity
- Organize code into distinct modules:
  - API
  - Telegram Bot
  - CV Processing
  - Embedding
  - Database
  - Dashboard
  - Background Tasks
- Each module must have a single responsibility and clear interface
- Follow the module boundaries defined in the PRD

### Asynchronous Programming
- Use `async/await` for all I/O-bound operations:
  - Database queries
  - External API calls
  - File operations
  - Network requests
- Include proper error handling in all async functions
- Use appropriate async context managers

### Documentation
- Maintain comprehensive documentation:
  - Inline comments
  - Function/class docstrings
  - Type hints
  - API documentation (FastAPI's built-in swagger)
  - Keep PRD.md and other docs updated
- Follow PEP 8 and consistent naming conventions

## 2. Configuration Management

### Project Structure
```
ai-accounting-job-matching/
├── app/
│   ├── config.py           # Central configuration
│   ├── logging_config.py   # Logging setup
│   └── [other modules]
├── tests/
├── scripts/
├── logs/
└── [config files]
```

### Environment Configuration
- Use `app/config.py` as the single source of truth
- Load variables via python-dotenv
- Support dual bot configurations:
  ```python
  BOT_TOKEN = os.getenv(f"TELEGRAM_BOT_TOKEN_{os.getenv('BOT_ENV', 'DEV')}")
  ```
- Never commit sensitive data

### Database Management
- Preserve existing accountingfirmjobs.com data
- Make backward-compatible schema changes
- Test migrations thoroughly
- Document database changes

## 3. Error Handling and Logging

### Logging Standards
- Use structured JSON logging
- Include essential fields:
  ```python
  logger.error("Operation failed",
      extra={
          "timestamp": datetime.utcnow().isoformat(),
          "environment": config.ENVIRONMENT,
          "request_id": request_id,
          "user_id": user_id,
          "function": function_name,
          "error_details": str(error)
      })
  ```
- Implement sensitive data filtering
- Use appropriate log levels

### Error Handling
- Wrap critical operations in try/except
- Provide user-friendly fallbacks
- Log full error context
- Handle background task errors gracefully

## 4. Testing and Validation

### Test Coverage
- Write comprehensive tests:
  - Unit tests
  - Integration tests
  - Data preservation tests
- Use pytest fixtures for:
  - Database connections
  - File operations
  - API simulations

### Monitoring
- Use Streamlit dashboard for:
  - System metrics
  - Error monitoring
  - Performance tracking
- Set up alerting for critical errors

## 5. Database Integration

### Shared Database Guidelines
- Models must remain compatible with accountingfirmjobs.com
- Use SQLAlchemy async engine
- Implement careful migration strategies
- Regular backup procedures

### Model Consistency
- Maintain integrity of existing models:
  - AccountingFirm
  - Job
  - User
  - UserSearch
  - UserConversation
  - JobMatch
  - JobEmbedding

## 6. Background Tasks

### Task Implementation
- Isolate from main API logic
- Include comprehensive logging
- Handle errors without stopping execution
- Track performance metrics

### Embedding Updates
- Run during low-traffic periods
- Log processing statistics
- Implement retry mechanisms
- Preserve existing embeddings

## 7. Security

### Data Protection
- Mask sensitive information in logs
- Use environment variables for secrets
- Implement proper input validation
- Follow security best practices

### API Security
- Validate all inputs
- Implement rate limiting
- Use appropriate authentication
- Follow OWASP guidelines

## 8. Version Control

### Git Practices
- Clear commit messages
- Feature branch workflow
- Peer review requirements
- No sensitive data in commits

## 9. Deployment

### Fly.io Configuration
- Use fly.toml for settings
- Configure proper scaling
- Set up health checks
- Enable proper logging

This document should be treated as a living reference and updated as the project evolves. All team members should follow these guidelines to maintain code quality and consistency.
