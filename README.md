# AI Job Matching Agent

A local job-matching application for candidates. It stores a structured profile, ranks jobs that have verified skill requirements, and uses Gemini only to embed skills and explain scores that the application has already calculated.

The live job provider is Adzuna for India and the United Kingdom. Listings without structured skill requirements stay visible, but they are not given a match score.

## Key features

- Account registration, login, and logout, with passwords stored as PBKDF2 hashes and sessions stored as token hashes.
- Account setup for an older passwordless profile. This requires a one-time administrator-issued claim code. Email and name alone cannot claim a profile.
- Smart Profile Builder on My Profile, with education, skills, career preferences, and location preferences.
- Discover Jobs, with search and filters over the stored catalogue.
- Match Insights for jobs that have verified skill requirements.
- Saved jobs for the signed-in candidate.
- Resume Centre for a session-scoped PDF review. The PDF is not stored permanently.
- A job preparation journal for the signed-in candidate.

## Technology stack

- Python 3.12
- FastAPI and Uvicorn for the API
- Streamlit for the browser application
- PostgreSQL on Supabase, accessed with SQLAlchemy and psycopg
- Google Gemini for skill embeddings and match explanations

## Architecture

The Streamlit application calls the FastAPI process. FastAPI is the only process that opens the database. The browser sends the session token to the API. Candidates can read and update only their own profile, matches, saved jobs, and preparation journal.

```text
Streamlit  -->  FastAPI  -->  Supabase PostgreSQL
                    |
                    +--> Gemini embeddings and explanations
                    +--> Adzuna catalogue import commands
```

## Matching

Each rankable job is scored out of 100:

- 70 points for skills. Exact matches count. A related skill counts only when its cosine similarity is at least 0.75.
- 20 points when a preferred role appears in the job title.
- 10 points when a preferred location appears in the job location.

Gemini does not choose the score. It embeds skill text and writes an explanation of the score the formula already produced. Jobs marked unmatchable, or jobs whose provider did not supply skill requirements, are left out of ranked results. Adding a category does not make a job matchable.

Industry preferences can be chosen in Discover filters. They do not add match points. Remote preference is stored separately and does not add match points.

## AI integration

Gemini has two jobs:

- Embed candidate skills and job skill requirements for the semantic portion of the 70-point skill score.
- Explain a ranked match from the score breakdown.

The full resume text is not sent to Gemini. Resume Centre keeps the extracted text in the Streamlit session for that visit.

## Adzuna

The import commands search Adzuna for India (`in`) and the United Kingdom (`gb`). The stored catalogue includes manually seeded sample jobs, an earlier keyword import, and one category import of the newest listings in each official category. Adzuna listings keep the provider title, company, location, country, description snippet, category, external id, listing URL, and posting date when the provider supplied them.

Salary amounts are stored only when the provider supplies a currency. Predicted salaries are ignored. The current category import had salaries without a currency, so those amounts were not stored. Employment type and workplace are not stored columns.

Use of Adzuna is subject to Adzuna's developer terms and attribution requirements. This application does not grant rights to redistribute the listings beyond that agreement.

## Database

The main tables are:

- `candidates`, including profile text, skill and preference lists, experience, and a password hash.
- `jobs`, including source, external id, country, URL, posting time, matchability, and, after the category migration, provider category label and tag.
- `saved_jobs`, linking one candidate to one job.
- `auth_sessions`, storing session-token hashes and expiry.
- `claim_tokens` and `claim_guards`, created on the next API startup for one-time claim codes and claim lockouts.
- `preparation_plans` and `preparation_tasks`.
- `job_sync_logs` and `provider_categories` for import history and the category catalogue.

## Local setup

From the project directory, create a virtual environment with Python 3.12 and install the pinned packages:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` on your machine. Do not commit it. The variable names are:

- `DATABASE_URL`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `GEMINI_EMBEDDING_MODEL`
- `GEMINI_SKILL_SIMILARITY_THRESHOLD`
- `ADZUNA_APP_ID`
- `ADZUNA_APP_KEY`
- `CORS_ORIGINS`

The frontend reads `API_URL` and `COOKIE_SECURE` from its environment first, then from Streamlit secrets. Locally both can stay unset. The API then stays at `http://127.0.0.1:8001`, and the session cookie is not marked `Secure`, so it works on local HTTP.

### Backend

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8001
```

`GET /` returns `{"status": "ok"}` when the process is up.

### Frontend

```powershell
.\.venv\Scripts\python.exe -m streamlit run frontend/app.py --server.port 8501
```

Open `http://127.0.0.1:8501`.

## Migrations

Run these yourself, in order, only when that part of the database is missing. They add columns or tables. They do not delete rows.

```powershell
.\.venv\Scripts\python.exe backend\migrate_job_source.py
.\.venv\Scripts\python.exe backend\migrate_job_categories.py
.\.venv\Scripts\python.exe backend\migrate_candidate_profile.py
```

The source and category migrations have already been applied to the current Supabase database. The candidate-profile migration has not. Apply it before restarting the API. The current model reads those profile columns, and a restart before the migration will make profile requests fail.

Authentication, claim-code, and preparation tables are created when the API process starts. That startup step does not rewrite candidate or job rows.

To issue a claim code for a passwordless profile:

```powershell
.\.venv\Scripts\python.exe backend\issue_claim_token.py --email name@example.com
```

The command prints the code once. The database stores only its hash. The code expires after one hour and cannot be used twice. Five failed attempts lock further claim attempts for 15 minutes. Password login is not locked by those failures.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest frontend backend/tests -q --tb=line --ignore=backend/tests/test_live_embeddings.py
```

`backend/tests/test_live_embeddings.py` calls Gemini. Run it only when you intend to use the live key.

## Deployment

The prepared targets are:

- API: a Render web service using `render.yaml`. It installs `requirements.txt`, binds to `0.0.0.0`, and listens on the platform `PORT`. Render checks `GET /`.
- Frontend: Streamlit Community Cloud, with the entry file `frontend/app.py`, `runtime.txt`, and the same `requirements.txt`.
- Database: the existing Supabase PostgreSQL database, through `DATABASE_URL`.

Set the Render environment variables in the Render dashboard. `render.yaml` lists the names and does not contain values. Set `CORS_ORIGINS` to the Streamlit site origin, for example the `https://` address Streamlit Community Cloud assigns. You can list more than one origin, separated by commas.

In Streamlit Community Cloud secrets, use this form. Do not commit the file.

```toml
API_URL = "https://ai-job-matching-api.onrender.com"
COOKIE_SECURE = true
```

`COOKIE_SECURE` may be the boolean `true` or a string such as `"true"`. An environment variable with the same name overrides the secret. Leave both unset for local HTTP.

Do not put secret values in Git.

Nothing in this repository deploys itself. Pushing code does not start Render or Streamlit until those services are connected.

## Known limitations

- Adzuna listings without structured skill requirements remain unmatchable. They can appear in Discover with no match score.
- The category labels from the latest import are stored in PostgreSQL. The API job model does not yet map those columns, so Discover still shows them as not categorised until that mapping is added and the API is restarted.
- Only Adzuna for India and the United Kingdom is integrated. Other providers and other Adzuna countries are not searched automatically.
- Imports run from commands. There is no scheduled synchronisation.
- Salary, currency, employment type, and workplace are shown only when those values are actually stored. Missing values are not invented.
- There is no email-delivery service. Passwordless profiles cannot be claimed until an administrator issues a claim code.
- Resume files and extracted resume text are not kept after the session ends.
- The candidate-profile migration still has to be applied before the API is restarted.
