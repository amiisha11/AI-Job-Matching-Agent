# AI Job Matching Agent

A beginner-friendly job matcher. Streamlit will collect a candidate profile, FastAPI will store profiles and jobs in PostgreSQL (Supabase), Python will rank jobs by skills and preferences, and Gemini will explain the top matches.

**Phase 1 is the project skeleton only.** The Python files describe their future jobs. They do not start a server, connect to a database, or call an API yet.

## Prerequisites

- Python 3.12
- PowerShell (already installed on Windows)

This PC’s `python` command is Python 3.15. Uvicorn’s PyYAML dependency has no Windows installer for 3.15 yet, so the virtual environment uses Python 3.12.14, which is already installed. You do not need a Supabase project or a Gemini API key to finish Phase 1. Those are used in later phases.

## Folder structure

```text
AI-Job-Matching-Agent/
├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── settings.py
│   ├── seed.py
│   ├── requirements.txt
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── candidates.py
│   │   └── jobs.py
│   └── services/
│       ├── __init__.py
│       ├── matching.py
│       └── ai_service.py
├── frontend/
│   └── app.py
├── data/
│   └── sample_jobs.csv
├── .env.example
├── .gitignore
└── README.md
```

`.env` is created on your machine from `.env.example`. Git ignores it. `.venv` is the virtual environment and is also ignored.

## What each file is for

| File | Purpose |
| --- | --- |
| `backend/__init__.py` | Marks `backend` as a Python package so later code can import it. |
| `backend/main.py` | Will create the FastAPI app, load settings, allow the Streamlit page to call the API, and attach the routes. |
| `backend/database.py` | Will open PostgreSQL using `DATABASE_URL` and hand each request a database session. |
| `backend/models.py` | Will define the candidate, job, and saved-job tables, plus the JSON shapes the API accepts and returns. |
| `backend/settings.py` | Will read `DATABASE_URL` and `GEMINI_API_KEY` from `.env`. This is the only place configuration is loaded. |
| `backend/seed.py` | Will load `data/sample_jobs.csv` into the jobs table once. |
| `backend/requirements.txt` | Pins the Python packages this project needs. |
| `backend/routes/__init__.py` | Marks `routes` as a Python package. |
| `backend/routes/candidates.py` | Will save a profile by email, return it, list saved jobs, save or unsave a job, and return matches. |
| `backend/routes/jobs.py` | Will list jobs and add a job. |
| `backend/services/__init__.py` | Marks `services` as a Python package. |
| `backend/services/matching.py` | Will score jobs from skill overlap and preferences. No HTTP and no Gemini calls. |
| `backend/services/ai_service.py` | Will be the only file that calls Gemini, to explain why a job matches. |
| `frontend/app.py` | Will be the whole Streamlit screen. It will talk only to FastAPI. |
| `data/sample_jobs.csv` | Column headers for the sample job catalog. Rows are added in a later phase. |
| `.env.example` | Placeholder variable names. Safe to commit. Copy it to `.env`. |
| `.env` | Your local secrets. Git ignores this file. Do not put real keys in any other file. |
| `.gitignore` | Tells Git to skip `.env`, virtual environments, Python cache files, and secret files. |
| `README.md` | This setup guide. |

## Setup

Run these commands from the project folder: `C:\Users\ASUS\Desktop\AI-Job-Matching-Agent`.

### 1. Check Python 3.12

```powershell
py -V:Astral\CPython3.12.14 --version
```

You should see `Python 3.12.14`. This selects the 3.12 interpreter instead of the default 3.15 `python` command.

### 2. Create a virtual environment

```powershell
py -V:Astral\CPython3.12.14 -m venv .venv
```

This creates a `.venv` folder with its own Python and `pip`. Project packages stay inside that folder instead of mixing with other projects. `.gitignore` already excludes `.venv`.

### 3. Activate the virtual environment

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

The prompt should start with `(.venv)`. If PowerShell blocks the script, allow it for this window only, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Command Prompt uses a different activator:

```cmd
.venv\Scripts\activate.bat
```

Activation lasts for that terminal window. Open a new terminal later and run the activate command again before `pip` or `python`.

### 4. Install the dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

The first command updates the installer inside `.venv`. The second command reads `backend/requirements.txt` and installs FastAPI, Uvicorn, SQLAlchemy, the PostgreSQL driver, python-dotenv, the Gemini client, Streamlit, and requests.

### 5. Create your local environment file

```powershell
Copy-Item .env.example .env
```

This copies the placeholders into `.env`. Leave the placeholders as they are for Phase 1. You will replace them when the database and Gemini phases begin. Do not commit `.env`.

### 6. Verify the environment

```powershell
python -c "import fastapi, uvicorn, sqlalchemy, psycopg, dotenv, streamlit, requests, google.genai; print('environment ok')"
```

`environment ok` means the packages import. Phase 1 is working. Nothing is supposed to start a server yet.

## What Phase 1 does not include

No API routes, database tables, ranking, Gemini calls, or Streamlit screens. Confirm Phase 1 before starting Phase 2 (database connection, tables, and sample jobs).
