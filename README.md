# Resume Shortlisting Automation System

An internal HR tool for managing job postings, uploading resumes, and automatically evaluating candidates using AI-powered skill extraction and matching.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Streamlit     │────▶│    FastAPI      │────▶│    Supabase     │
│   Frontend      │     │    Backend      │     │   PostgreSQL    │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │  Google  │ │  OpenAI  │ │  Resume  │
              │  Drive   │ │   API    │ │  Parser  │
              └──────────┘ └──────────┘ └──────────┘
```

## Features

### Job Management
- Create jobs with auto-generated 5-character JOBID (e.g., `A1234`)
- List, search, update, and delete jobs
- Cascading delete for associated resumes and evaluations

### Resume Management
- Upload single or multiple resumes (PDF/DOCX)
- Automatic storage in Google Drive with organized folder structure
- View, download, and delete resumes
- Toast notifications and manual clear buttons for uploads

### AI-Powered Evaluation
- Automatic skill extraction from resumes
- Match scoring against job descriptions
- Status classification: "OK to Proceed" or "Not OK"
- Detailed justification for each evaluation

## Tech Stack

- **Backend**: FastAPI
- **Frontend**: Streamlit
- **Database**: Supabase (PostgreSQL)
- **File Storage**: Google Drive API
- **AI**: OpenAI GPT-4o-mini

## Setup Instructions

### 1. Prerequisites

- Python 3.10+
- Supabase account
- Google Cloud project with Drive API enabled
- OpenAI API key

### 2. Database Setup (Supabase)

1. Create a new Supabase project
2. Run the SQL schema in `backend/app/db/schema.sql` in the Supabase SQL editor
3. Copy your project URL and anon key

### 3. Google Drive Setup

1. Create a Google Cloud project
2. Enable the Google Drive API
3. Create OAuth 2.0 credentials (Web application type)
4. Add `http://localhost:8000/auth/callback` to Authorized redirect URIs
5. (Optional) Add test user emails to OAuth consent screen if app is in testing
6. Download the client_secret.json file and rename to `credentials.json`
7. Place `credentials.json` in the backend directory

### 4. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials:
# - SUPABASE_URL
# - SUPABASE_KEY
# - OPENAI_API_KEY
# - GOOGLE_DRIVE_CREDENTIALS_PATH

# Place your Google credentials file
cp /path/to/your/credentials.json ./credentials.json

# Run the server
uvicorn app.main:app --reload --port 8000
```

### 5. Frontend Setup

```bash
cd frontend

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env if backend is not on localhost:8000

# Run Streamlit
streamlit run app.py
```

## Project Structure

```
resume_shortlisting_automation_system/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── jobs.py          # Job CRUD endpoints
│   │   │   ├── resumes.py       # Resume upload/management
│   │   │   └── evaluations.py   # Evaluation endpoints
│   │   │   └── ai.py            # AI integration endpoints
│   │   ├── core/
│   │   │   ├── config.py        # Settings management
│   │   │   └── logging.py       # Logging setup
│   │   ├── db/
│   │   │   ├── supabase.py      # Database client
│   │   │   └── schema.sql       # Database schema
│   │   ├── models/
│   │   │   └── schemas.py       # Pydantic models
│   │   ├── services/
│   │   │   ├── job_service.py
│   │   │   ├── resume_service.py
│   │   │   ├── resume_parser.py
│   │   │   ├── skill_extractor.py
│   │   │   ├── evaluation_service.py
│   │   │   └── google_drive_service.py
│   │   └── main.py              # FastAPI app
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app.py                   # Streamlit main page
│   ├── pages/
│   │   ├── 1_Jobs.py           # Job management page
│   │   ├── 2_Resumes.py        # Resume management page
│   │   └── 3_Evaluations.py    # Evaluations page
│   ├── api_client.py            # Backend API client
│   ├── requirements.txt
│   └── .env.example
└── README.md
```

## API Endpoints

### Jobs
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/jobs/` | Create a new job |
| GET | `/api/v1/jobs/` | List all jobs |
| GET | `/api/v1/jobs/{job_id}` | Get job by JOBID |
| PUT | `/api/v1/jobs/{job_id}` | Update job |
| DELETE | `/api/v1/jobs/{job_id}` | Delete job |

### Resumes
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/resumes/{job_id}/upload` | Upload single resume |
| POST | `/api/v1/resumes/{job_id}/upload-multiple` | Upload multiple resumes |
| GET | `/api/v1/resumes/{job_id}` | List resumes for job |
| GET | `/api/v1/resumes/download/{resume_id}` | Download resume |
| DELETE | `/api/v1/resumes/{resume_id}` | Delete resume |
| DELETE | `/api/v1/resumes/job/{job_id}/all` | Delete all resumes for job |

### Evaluations
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/evaluations/resume/{resume_id}` | Evaluate single resume |
| POST | `/api/v1/evaluations/job/{job_id}/all` | Evaluate all resumes |
| GET | `/api/v1/evaluations/job/{job_id}` | List evaluations |
| GET | `/api/v1/evaluations/job/{job_id}/summary` | Get summary stats |
| GET | `/api/v1/evaluations/{evaluation_id}` | Get evaluation details |
| POST | `/api/v1/evaluations/resume/{resume_id}/re-evaluate` | Re-evaluate resume |

### AI Integration
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/ai/capabilities` | Get system capabilities |
| POST | `/api/v1/ai/search-resumes` | Search resumes |
| GET | `/api/v1/ai/read-resume/{file_id}` | Read resume content |
| POST | `/api/v1/ai/evaluate-resume` | Evaluate resume |
| GET | `/api/v1/ai/job/{job_id}` | Get job details |
| GET | `/api/v1/ai/job/{job_id}/evaluations` | Get job evaluations |
| GET | `/api/v1/ai/stats` | Get system statistics |

## AI Integration

The Resume Shortlisting Automation System provides AI integration APIs that allow AI models to interact with Google Drive, Supabase database, and evaluation tools.

### Base URL
```
http://localhost:8000/api/v1/ai
```

### Available Endpoints

- **Get System Capabilities** (`GET /capabilities`): Returns available AI integration features
- **Search Resumes** (`POST /search-resumes`): Search for resumes in Google Drive by job ID or filename pattern
- **Read Resume Content** (`GET /read-resume/{file_id}`): Read the full text content of a specific resume file
- **Evaluate Resume** (`POST /evaluate-resume`): Evaluate a resume against job requirements using AI
- **Get Job Details** (`GET /job/{job_id}`): Retrieve detailed information about a specific job posting
- **Get Job Evaluations** (`GET /job/{job_id}/evaluations`): Get all AI evaluations for a specific job
- **Get System Statistics** (`GET /stats`): Get system statistics and counts for context

### Use Cases for AI Models

#### Resume Analysis Workflow
1. Search for relevant resumes
2. Read resume content
3. Evaluate against job requirements
4. Compare candidates

#### Automated Shortlisting
1. Get job requirements
2. Batch evaluate resumes
3. Rank candidates

#### System Monitoring
1. Check system health
2. Monitor job activity

### Response Format

All endpoints return responses in this format:
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully"
}
```

### Integration with AI Models

Use these endpoints in function calling or tool use capabilities for Claude/GPT integration, or make HTTP requests for custom AI applications.

## Database Schema
- `id`: Primary key
- `job_id`: Unique 5-char alphanumeric ID
- `title`: Job title
- `description`: Full job description
- `google_drive_folder_id`: Associated Drive folder
- `created_at`, `updated_at`: Timestamps

### Resumes Table
- `id`: Primary key
- `job_id`: Foreign key to jobs
- `file_name`: Original file name
- `google_drive_file_id`: Drive file ID
- `candidate_name`: Extracted candidate name
- `upload_timestamp`: Upload time

### Evaluations Table
- `id`: Primary key
- `resume_id`: Foreign key to resumes
- `job_id`: Foreign key to jobs
- `match_score`: 0-100 percentage
- `status`: "OK to Proceed" / "Not OK" / "Pending"
- `justification`: AI-generated explanation
- `skills_extracted`: JSON array of skills
- `skills_matched`: JSON array of matched skills
- `experience_years`: Extracted experience
- `education`: Extracted education
- `previous_roles`: JSON array of roles

## Security Considerations

- API keys stored in environment variables
- Supabase Row Level Security enabled
- File validation for uploads (PDF/DOCX only, 10MB max)
- CORS configured for frontend access

## Future Enhancements

- [ ] Resume comparison view
- [ ] AI-generated interview questions
- [ ] Export shortlisted candidates (CSV/Excel)
- [ ] Activity and audit logs UI
- [ ] Multiple HR user support with authentication
- [ ] Email notifications

## 📝 License

Internal use only.
