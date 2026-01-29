# Campus AI - Complete Guide

## Overview

**Campus AI** is a comprehensive AI-powered recruitment platform built with FastAPI (backend), React.js (frontend), and ChromaDB for intelligent candidate matching.

## System Architecture

### Technology Stack

**Backend:**
- FastAPI 0.104+
- SQLModel (SQLAlchemy ORM)
- SQLite/PostgreSQL
- ChromaDB (Vector Database)
- Sentence Transformers (Embeddings)
- JWT Authentication

**Frontend:**
- React 18 + TypeScript
- Vite (Build Tool)
- Tailwind CSS
- React Router
- React Query
- Axios

**Infrastructure:**
- Docker & Docker Compose
- GCP Integration (optional)

## Quick Start

### Backend Setup (5 minutes)

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Run application
python app.py
```

Backend runs on `http://localhost:8000`
API docs available at `http://localhost:8000/docs`

### Frontend Setup (5 minutes)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env

# Run development server
npm run dev
```

Frontend runs on `http://localhost:5173`

## Features & Functionality

### 1. User Role System

#### Admin Role
- Dashboard with system statistics
- Manage all users (activate/deactivate)
- Verify recruiter accounts
- View recruitment analytics

#### Recruiter Role
- Upload candidate resumes (PDF, DOCX, TXT)
- Company profile management
- Automatic resume parsing
- Resume vector embedding
- Track resume uploads and views

#### User (Job Seeker) Role
- Conversational AI chat
- Specify 5-6 job requirements
- Intelligent candidate matching
- View top 2 matched candidates
- Candidate profile details

### 2. Resume Processing Pipeline

**Upload Flow:**
1. Recruiter uploads resume file
2. File format validation (PDF/DOCX/TXT)
3. Text extraction from document
4. Automatic parsing:
   - Skills extraction
   - Experience years
   - Education level
   - Location
   - Summary generation

**Embedding Flow:**
1. Parsed resume text converted to embeddings
2. Stored in ChromaDB collection
3. Indexed for semantic search
4. Metadata saved to SQLite

### 3. Requirements Collection Agent

**7-Step Process:**
1. User initiates chat
2. Agent asks about technical skills (Requirement 1)
3. Agent asks about experience required (Requirement 2)
4. Agent asks about education level (Requirement 3)
5. Agent asks about location preference (Requirement 4)
6. Agent asks about certifications/tools (Requirement 5)
7. Agent asks about additional preferences (Requirement 6)
8. System creates embeddings for requirements
9. Searches ChromaDB for matches

**User Interaction:**
```
Agent: "What programming languages or technical skills are you looking for?"
User: "Python, JavaScript, React"
[Requirement 1/6 collected]

Agent: "How many years of experience should the candidate have?"
User: "5-7 years"
[Requirement 2/6 collected]
...
Agent: "Thank you! Your profile is complete. We're finding the best matches for you..."
```

### 4. Intelligent Matching Engine

**Matching Algorithm:**
- Semantic similarity search via ChromaDB
- Multiple scoring factors:
  - **Skills Match** (70%): Exact skill overlap
  - **Experience Match** (10%): Years alignment
  - **Education Match** (10%): Qualification match
  - **Location Match** (10%): Geographic fit

**Returns:**
- Top 2 candidates ranked by score
- Detailed match breakdown
- Skill matching percentage
- Candidate full profile information

### 5. Vector Embeddings & ChromaDB

**Collections:**
- `resumes`: All uploaded resume embeddings
- `requirements`: User job requirement embeddings

**Operations:**
- Add documents with metadata
- Semantic similarity search
- Vector persistence
- Metadata filtering

## Database Schema

### Users Table
```python
- user_id (PK)
- username, email, password_hash
- full_name, role (admin/recruiter/user)
- is_active, is_verified
- profile_image_url, bio, phone_number
- created_at, updated_at, last_login
```

### Recruiters Table
```python
- recruiter_id (PK)
- user_id (FK -> users)
- company_name, company_email, company_website
- job_title, department, location
- company_description
- total_resumes_reviewed, is_verified
- verification_date, created_at, updated_at
```

### Resumes Table
```python
- resume_id (PK)
- recruiter_id (FK -> recruiters)
- candidate_name, candidate_email, candidate_phone
- file_path, file_name, file_size, file_type
- skills (JSON), experience, education, location
- summary, chroma_collection_id
- is_active, views_count, match_count
- created_at, updated_at
```

### Requirements Table
```python
- requirement_id (PK)
- user_id (FK -> users)
- skills, experience_years, education_level
- location, keywords (JSON)
- additional_preferences
- requirement_count (0-6)
- is_complete, is_matched
- embedding (JSON), chroma_query_id
- created_at, updated_at
```

### Match Results Table
```python
- match_id (PK)
- requirement_id (FK), resume_id (FK)
- match_score (0-1), rank
- matched_skills (JSON), skill_match_percentage
- experience_match, location_match
- was_viewed, view_date
- was_contacted, contact_date, feedback
- created_at, updated_at
```

## API Endpoints

### Authentication (`/api/auth`)
- `POST /register` - User registration
- `POST /login` - User login

### Users (`/api/users`)
- `GET /{user_id}` - Get user profile
- `PUT /{user_id}` - Update profile
- `GET /admin/list` - List all users (Admin)

### Recruiters (`/api/recruiters`)
- `POST /profile` - Create recruiter profile
- `GET /{recruiter_id}` - Get profile
- `PUT /{recruiter_id}` - Update profile

### Resumes (`/api/resumes`)
- `POST /upload` - Upload resume
- `GET /{resume_id}` - Get resume details
- `GET /recruiter/{recruiter_id}` - List recruiter's resumes

### Chat & Matching (`/api/chat`)
- `POST /message` - Send requirement message
- `POST /get-matches` - Get matched candidates
- `GET /status/{user_id}` - Get chat status

### Admin (`/api/admin`)
- `GET /dashboard/stats` - Dashboard statistics
- `GET /users/list` - List users
- `GET /recruiters/list` - List recruiters
- `PUT /users/{user_id}/status` - Toggle user active status
- `PUT /recruiters/{recruiter_id}/verify` - Verify recruiter

## File Upload & Storage

**Resume Storage:**
- Path: `./uploads/resumes/`
- Format: `{recruiter_id}_{candidate_name}_{timestamp}.{ext}`
- Supported: .pdf, .docx, .txt
- Size limit: Configurable (default: unlimited)

**ChromaDB Storage:**
- Path: `./chroma_data/`
- Format: Parquet + DuckDB
- Persistence: Automatic

## Configuration

### Environment Variables

#### Backend (`.env`)
```env
# API
API_HOST=0.0.0.0
API_PORT=8000
API_ENV=development

# Database
DATABASE_URL=sqlite:///./campus_ai.db
DB_POOL_MIN=5
DB_POOL_MAX=20

# Security
JWT_SECRET=your-super-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_DAYS=30

# ChromaDB & Embeddings
CHROMA_PERSISTENT_PATH=./chroma_data
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# CORS
FRONTEND_URL=http://localhost:5173
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# GCP (Optional)
GCP_PROJECT_ID=your-project-id
GCP_CREDENTIALS_PATH=./gcp-credentials.json
```

#### Frontend (`.env`)
```env
VITE_API_URL=http://localhost:8000
```

## Deployment

### Docker Deployment

```bash
# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop
docker-compose down
```

### Production Checklist

- [ ] Change `JWT_SECRET` to strong random value
- [ ] Switch from SQLite to PostgreSQL
- [ ] Enable HTTPS/SSL certificates
- [ ] Configure production CORS origins
- [ ] Set up email service (SendGrid, AWS SES)
- [ ] Configure error logging (Sentry, DataDog)
- [ ] Set up uptime monitoring
- [ ] Create database backups
- [ ] Configure CDN for static assets
- [ ] Implement rate limiting

## Development Workflow

### Adding New Features

1. **Backend:**
   - Create model in `models/`
   - Create repository in `database/`
   - Create service in `services/` if needed
   - Create routes in `routes/`
   - Update `app.py` to include routes

2. **Frontend:**
   - Create page in `pages/`
   - Create components in `components/`
   - Create hooks if needed
   - Update routes in `App.tsx`
   - Style with Tailwind CSS

### Database Changes

1. Update model in `models/`
2. SQLModel automatically creates tables on startup
3. For production migrations, consider using Alembic

## Testing

### Backend Tests
```bash
cd backend
pytest tests/
pytest tests/ -v --cov
```

### Frontend Tests
```bash
cd frontend
npm run test  # Not configured in template, add if needed
```

## Performance Optimization

### Backend
- Database connection pooling
- ChromaDB caching
- JWT token validation
- Request validation with Pydantic

### Frontend
- React Query caching
- Code splitting with lazy routes
- Image optimization
- CSS minification in build

## Security Measures

- JWT authentication
- Password hashing (SHA256)
- CORS configuration
- Input validation
- SQL injection prevention (SQLModel)
- HTTPS ready

## Troubleshooting

### Backend Issues

**ChromaDB Connection Error:**
```bash
# Clear and reinitialize
rm -rf ./chroma_data
python app.py
```

**Database Locked (SQLite):**
```bash
# Stop application
# Delete .db file
rm campus_ai.db
# Restart
```

**Import Errors:**
```bash
pip install -r requirements.txt --force-reinstall
```

### Frontend Issues

**Port Already in Use:**
```bash
# Change port in vite.config.ts
# Or kill process:
# Windows: netstat -ano | findstr :5173 && taskkill /PID <PID>
# Mac/Linux: lsof -i :5173 && kill <PID>
```

**API Connection Error:**
- Check backend is running
- Verify `VITE_API_URL` in `.env`
- Check browser console for CORS errors

## Contributing Guidelines

1. Follow project structure
2. Use type hints (TypeScript/Python)
3. Write descriptive commits
4. Test before pushing
5. Document complex logic
6. Follow existing code style

## License

Campus AI - All Rights Reserved

## Support & Contact

For issues and feature requests:
- Check README files in respective folders
- Review API documentation at `/docs`
- Check logs for error details
- Contact development team

---

**Built with ❤️ using FastAPI, React, and ChromaDB**
