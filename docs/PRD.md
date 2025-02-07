# Updated Product Requirements Document (PRD)

## 1. Product Overview

**Product Name:**  
AI‑Powered Accounting Job Matching Bot

**Vision:**  
To simplify the job search process for accounting professionals by leveraging AI to analyze CVs and generate highly relevant job matches—all while preserving data integrity in an existing PostgreSQL database shared with [accountingfirmjobs.com](https://accountingfirmjobs.com). The system must be modular, robust, and support detailed error logging for rapid diagnosis.

**Mission:**  
Build a scalable, maintainable, and production‑ready system (developed from scratch in Windsurf) that integrates:
- Telegram bot interactions (with separate development and production bots),
- A REST API using FastAPI,
- AI‑driven CV processing and analysis using OpenAI,
- Semantic job search via vector embeddings (using pgvector),
- An admin dashboard (built in Streamlit) for monitoring,
- Background tasks for periodic updates.

The system will work with an existing PostgreSQL database (shared with accountingfirmjobs.com) so that any schema or migration changes preserve current data and avoid complications.

---

## 2. Key Features and Use Cases

### A. Telegram Bot Interface
- **Use Cases:**
  - A user initiates a conversation via Telegram to search for accounting jobs.
  - A user uploads a CV (PDF/DOC/DOCX) to receive personalized job recommendations.
  - The bot guides users through multi‑step flows (e.g., job search, setting preferences).
- **Key Commands:**
  - `/start`: Registers and welcomes the user.
  - `/upload_cv`: Initiates the CV upload and processing workflow.
  - `/search_jobs`: Begins a guided job search conversation.
  - `/preferences`: Allows users to set or update job preferences.
  - `/help`: Displays available commands and usage guidance.
  - `/test_db`: *(Admin-only)* Tests database connectivity and verifies shared data.

### B. API and Backend Services (FastAPI)
- **Use Cases:**
  - Expose REST endpoints for job search, job details, health checks, and Prometheus metrics.
  - Serve as the backend for the admin dashboard.
- **Key Endpoints:**
  - `GET /`: A health-check endpoint.
  - `POST /search/`: Accepts search queries and returns semantic job matches.
  - `GET /jobs/{job_id}`: Returns detailed information about a job.
  - `GET /health` and `GET /metrics`: Expose system and performance metrics.

### C. CV Processing & AI Integration
- **Use Cases:**
  - Users upload their CV to receive an AI‑generated analysis (including key skills, experience, and role suggestions).
  - Extract structured job preferences from free‑text queries.
- **Key Functions:**
  - Extract text from PDFs (using *pdfplumber*) and Word documents (using *python‑docx*).
  - Use OpenAI GPT‑3.5 Turbo to generate summaries and structured data.
  - Generate CV embeddings using OpenAI’s *text‑embedding‑ada‑002*.

### D. Embedding and Semantic Search
- **Use Cases:**
  - Enable semantic search by comparing vector embeddings of job listings and user profiles.
  - Run background tasks to update job embeddings without disrupting live operations.
- **Key Functions:**
  - Generate and update embeddings using OpenAI.
  - Perform similarity searches using pgvector.
  - Record user search history and job match scores for continuous improvement.

### E. Admin Dashboard (Streamlit)
- **Use Cases:**
  - Monitor key metrics such as active users, job searches, and system errors.
  - Validate database connectivity and review detailed logs.
- **Key Features:**
  - Display real‑time metrics.
  - Provide options for log export and filtering.
  - Offer clear visibility into error events and system alerts for prompt intervention.

### F. Robust Error Handling and Logging
- **Use Cases:**
  - Capture and log errors with full context (e.g., request IDs, user IDs, input parameters, and stack traces).
  - Provide fallback responses to users when errors occur.
- **Key Requirements:**
  - Every module must wrap critical operations in try/except blocks.
  - Use centralized, structured JSON logging across the system.
  - Log errors with comprehensive context and trigger graceful fallback responses.

---

## 3. System Architecture Overview

### High-Level Components

1. **API Server (FastAPI):**  
   - Exposes endpoints for job search, job details, health checks, and metrics.
   - Uses middleware for request tracking and comprehensive error logging.

2. **Telegram Bot Service:**  
   - Handles asynchronous command and message processing using *python‑telegram‑bot*.
   - Maintains separate configurations for development and production bots via environment variables.
   - Routes users to appropriate workflows (e.g., CV upload, job search).

3. **CV and AI Module:**  
   - Processes CV uploads (PDF and DOCX) and extracts text.
   - Uses OpenAI for analysis and extracting structured job preferences.
   - Generates CV embeddings for semantic matching.

4. **Embedding and Semantic Search Service:**  
   - Generates vector embeddings for jobs and CVs.
   - Uses pgvector for similarity comparisons.
   - Runs background tasks to update embeddings while logging performance and errors.

5. **Database Layer:**  
   - Uses an asynchronous SQLAlchemy engine.
   - Works with an existing PostgreSQL database (shared with accountingfirmjobs.com).
   - **Models include:**  
     - **AccountingFirm & Job:** Read‑only models for job board data.  
     - **User, UserSearch, UserConversation, JobMatch, JobEmbedding:** Bot‑specific models.
   - Schema/migration changes must preserve existing data.

6. **Admin Dashboard:**  
   - Built with Streamlit to display real‑time metrics, logs, and health checks.
   - Provides insights into system errors and database status.

7. **Background Tasks:**  
   - Periodically update job embeddings and perform maintenance tasks.
   - Log batch processing results and errors for performance tracking.

8. **Logging & Configuration:**  
   - A central configuration module loads environment variables from a `.env` file.
   - All components use structured JSON logging with sensitive data filters.
   - Detailed logs and error contexts are maintained for rapid troubleshooting.

---

## 4. Technical Stack

- **Backend:** FastAPI, asynchronous SQLAlchemy, Uvicorn/Gunicorn  
- **Database:** PostgreSQL (production; shared with accountingfirmjobs.com), SQLite (for testing)  
- **ORM:** SQLAlchemy (async engine)  
- **Bot Integration:** python‑telegram‑bot (dual configuration: development and production)  
- **AI & Embeddings:** OpenAI GPT‑3.5 Turbo, text‑embedding‑ada‑002  
- **Vector Search:** pgvector  
- **Dashboard:** Streamlit  
- **Deployment:** Fly.io (configured via fly.toml)  
- **Testing:** Pytest, pytest‑asyncio  
- **Logging:** Structured JSON logging (via python‑json‑logger) with custom filters  
- **Environment Management:** python‑dotenv

---

## 5. Deployment and Environment Strategy

### Fly.io Deployment
- Use **fly.toml** to configure app settings, primary region, build settings, and rolling updates.
- Plan schema migrations carefully to avoid disrupting the existing shared PostgreSQL data.

### Environment Variables
- Critical keys: `TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`, `DATABASE_URL`, `ENVIRONMENT`, `ADMIN_IDS`.
- Maintain separate tokens/configurations for development and production using an environment variable (e.g., `BOT_ENV`).

### Data Preservation
- Since the PostgreSQL database is shared with accountingfirmjobs.com, ensure any migrations are backward‑compatible and preserve existing records.
- Perform a full schema review and create migration scripts that update only non‑critical parts.

### CI/CD and Testing
- Automate testing and deployments (e.g., with GitHub Actions).
- Validate changes in a staging environment that mimics production before deploying to production.

---

## 6. Success Metrics

- **User Engagement:** Number of active Telegram users and job searches per week.
- **Match Relevance:** Positive user feedback on job match quality.
- **System Stability:** High uptime and low error rates (as monitored via Prometheus and logs).
- **Data Integrity:** No data loss or corruption in the shared PostgreSQL database.
- **Deployment Efficiency:** Seamless transitions with minimal downtime.

---
