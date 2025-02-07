# AI Accounting Job Matching

An AI-powered system for matching accounting professionals with job opportunities using advanced CV processing and semantic search.

## Features

- CV processing and analysis
- Job posting semantic search
- Telegram bot interface
- Admin dashboard
- Automated embedding generation
- Smart matching algorithm

## Setup

1. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and configure your environment variables:
```bash
cp .env.example .env
```

4. Run the application:
```bash
python -m app.main
```

## Documentation

- [Product Requirements Document](docs/PRD.md)
- [Contributing Guidelines](docs/CONTRIBUTING.md)
- [Development Rules](docs/DEVELOPMENT_RULES.md)

## Development

- Run tests: `pytest`
- Update job embeddings: `python scripts/update_job_embeddings.py`
- Format code: `black .`

## Deployment

This application is configured for deployment on Fly.io. Deploy using:

```bash
fly deploy
```

## Project Structure

- `app/`: Main application code
  - `services/`: Core business logic services
  - `tasks/`: Background tasks and workers
- `scripts/`: Utility scripts
- `tests/`: Test suite
- `logs/`: Application logs

## License

MIT
