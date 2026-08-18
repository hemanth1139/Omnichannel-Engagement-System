# HCP Engagement Intelligence Backend

FastAPI backend for the HCP Engagement Intelligence application. This lightweight backend provides aggregated and detailed HCP engagement metrics using an existing machine learning model output table and an HCP profile table on an Amazon RDS database.

## Architecture
- **Framework:** FastAPI
- **Database:** Amazon RDS PostgreSQL
- **ORM:** SQLAlchemy 2.x
- **Data Validation:** Pydantic v2
- **Frontend:** Next.js (via AWS Amplify)

The backend connects only to RDS to query final model outputs. No ML inference or training is performed here.

## Database Tables
1. **HCP Profile Table:** Contains HCP details (Name, Specialty, Location, etc.).
2. **Model Output Table:** Contains pre-calculated ML outputs (Hybrid Engagement Score, Engagement Level, Channel Probabilities, Next Best Channel).

The two tables are joined dynamically via the `hcp_id` column.

## Setup and Running Locally

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   Copy `.env.example` to `.env` and fill in the database URL and table names.
   ```bash
   cp .env.example .env
   ```

4. Run the server:
   ```bash
   uvicorn app.main:app --reload
   ```

5. Visit `/docs` or `/redoc` for Swagger documentation.

## Endpoints

1. `GET /health`: Health check.
2. `GET /api/dashboard`: Overall HCP Engagement metrics for Page 1.
3. `GET /api/hcps/{hcp_id}`: Individual HCP details for Page 2.

## Testing
Run tests using pytest:
```bash
pytest tests/
```

## Production Deployment (AWS EC2)

1. Ensure the PostgreSQL connection string points to the production RDS instance.
2. Configure `CORS_ORIGINS` to contain your specific AWS Amplify domain.
3. Set `APP_ENV=production`.
4. Run the server securely using a process manager like `systemd` or via a container orchestrator.
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
