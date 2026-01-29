# Campus AI Backend README

## Overview

Campus AI is an AI-powered recruitment platform built with FastAPI and React.js. It helps organizations identify the best candidates using vector embeddings and semantic search.

## Features

### Three User Roles:
1. **Admin**: Manage users, recruiters, and view system statistics
2. **Recruiter**: Upload resumes, edit profiles, and manage candidates
3. **User**: Chat with AI agent to describe requirements, view matched candidates

### Core Capabilities:
- **Resume Parsing**: Automatic extraction and analysis of resume content
- **Vector Embeddings**: Uses ChromaDB for semantic matching
- **Intelligent Matching**: Matches user requirements with resumes using embeddings
- **Chat Interface**: Conversational requirement collection (5-6 requirements)
- **Top Matches**: Returns top 2 profile matches based on requirements

## Tech Stack

### Backend:
- **Framework**: FastAPI
- **Database**: SQLite (development) / PostgreSQL (production)
- **Vector DB**: ChromaDB
- **Embeddings**: Sentence Transformers
- **ORM**: SQLModel
- **Authentication**: JWT
- **ML**: Scikit-learn, PyPDF2, python-docx

### Frontend:
- **Framework**: React.js (TypeScript)
- **Styling**: Tailwind CSS
- **Components**: Shadcn/ui, Radix UI
- **HTTP Client**: Axios
- **State Management**: React Query
- **Routing**: React Router

## Project Structure

```
Campus AI/
├── backend/
│   ├── agents/              # Requirement collection agent
│   ├── database/            # Database models and repositories
│   ├── models/              # Pydantic/SQLModel models
│   ├── routes/              # API endpoints
│   ├── services/            # Business logic services
│   │   ├── embeddings_service.py       # ChromaDB integration
│   │   ├── resume_parsing_service.py   # Resume parsing
│   │   └── matching_service.py         # Resume matching logic
│   ├── utils/               # Utilities and config
│   ├── app.py              # Main FastAPI application
│   ├── requirements.txt     # Python dependencies
│   └── docker-compose.yml  # Docker configuration
│
└── frontend/
    ├── src/
    │   ├── components/      # React components
    │   ├── pages/          # Page components
    │   ├── hooks/          # Custom hooks
    │   ├── contexts/       # React contexts
    │   ├── lib/            # Utility functions
    │   └── App.tsx         # Main App component
    ├── package.json
    └── vite.config.ts
```

## Setup Instructions

### Backend Setup

1. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**:
```bash
cd backend
pip install -r requirements.txt
```

3. **Create .env file**:
```bash
cp .env.example .env
```

4. **Update .env with your configuration**:
```
API_PORT=8000
DATABASE_URL=sqlite:///./campus_ai.db
JWT_SECRET=your-secret-key
CHROMA_PERSISTENT_PATH=./chroma_data
```

5. **Run the application**:
```bash
python app.py
```

The API will be available at `http://localhost:8000`
API documentation available at `http://localhost:8000/docs`

### Frontend Setup

1. **Install dependencies**:
```bash
cd frontend
npm install  # or yarn install / bun install
```

2. **Create .env file**:
```bash
VITE_API_URL=http://localhost:8000
```

3. **Run development server**:
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user

### Users
- `GET /api/users/{user_id}` - Get user profile
- `PUT /api/users/{user_id}` - Update user profile
- `GET /api/users/admin/list` - Admin: List all users

### Recruiters
- `POST /api/recruiters/profile` - Create recruiter profile
- `GET /api/recruiters/{recruiter_id}` - Get recruiter profile
- `PUT /api/recruiters/{recruiter_id}` - Update recruiter profile

### Resumes
- `POST /api/resumes/upload` - Upload and parse resume
- `GET /api/resumes/{resume_id}` - Get resume details
- `GET /api/resumes/recruiter/{recruiter_id}` - Get recruiter's resumes

### Chat & Matching
- `POST /api/chat/message` - Send message to requirements agent
- `POST /api/chat/get-matches` - Get matched candidates
- `GET /api/chat/status/{user_id}` - Get chat status

### Admin
- `GET /api/admin/dashboard/stats` - Dashboard statistics
- `GET /api/admin/users/list` - List all users
- `GET /api/admin/recruiters/list` - List all recruiters
- `PUT /api/admin/users/{user_id}/status` - Activate/deactivate user
- `PUT /api/admin/recruiters/{recruiter_id}/verify` - Verify recruiter

## Key Features Implementation

### Resume Parsing
The `ResumeParsingService` extracts:
- Skills (from predefined keywords)
- Years of experience
- Education level
- Location
- Summary

Supports: PDF, DOCX, TXT formats

### Vector Embeddings
The `EmbeddingsService` using ChromaDB:
- Converts resume text to embeddings
- Stores embeddings for semantic search
- Searches for similar resumes based on user requirements

### Intelligent Matching
The `MatchingService`:
- Calculates similarity scores
- Scores on skills, experience, location, education
- Returns top 2 matches with detailed scoring

### Requirements Agent
The `RequirementsAgent`:
- Collects 5-6 requirements through conversation
- Validates and stores user input
- Creates embeddings for intelligent matching

## Database Schema

### Users Table
- user_id, username, email, password_hash, full_name, role, is_active, is_verified, etc.

### Recruiters Table
- recruiter_id, user_id, company_name, company_email, job_title, location, etc.

### Resumes Table
- resume_id, recruiter_id, candidate_name, file_path, skills, experience, education, chroma_collection_id, etc.

### Requirements Table
- requirement_id, user_id, skills, experience_years, education_level, location, keywords, embedding, chroma_query_id, etc.

### Match Results Table
- match_id, requirement_id, resume_id, match_score, rank, matched_skills, skill_match_percentage, etc.

## Authentication

Uses JWT (JSON Web Tokens) for authentication:
- `JWT_SECRET`: Secret key for token signing
- `JWT_ALGORITHM`: HS256
- `JWT_EXPIRATION_DAYS`: 30 days default

## Error Handling

Comprehensive error handling with HTTP status codes:
- 400: Bad Request
- 401: Unauthorized
- 404: Not Found
- 500: Internal Server Error

## Testing

Run tests using pytest:
```bash
pytest tests/
pytest tests/ -v --cov=
```

## Development

### Adding New Models
1. Create model in `models/` directory
2. Create repository in `database/` directory
3. Register in models/__init__.py

### Adding New Routes
1. Create route file in `routes/` directory
2. Import and include router in `app.py`
3. Add route to this README

### Adding New Services
1. Create service file in `services/` directory
2. Implement service class with required methods
3. Create global instance and getter function

## Deployment

### Using Docker (Optional):
```bash
docker-compose up -d
```

### Production Checklist:
- [ ] Change JWT_SECRET in .env
- [ ] Use PostgreSQL instead of SQLite
- [ ] Enable HTTPS/SSL
- [ ] Set up proper CORS origins
- [ ] Configure email service for notifications
- [ ] Set up logging and monitoring
- [ ] Configure backup strategy

## Troubleshooting

### ChromaDB Issues
- Clear `./chroma_data` directory and restart
- Check write permissions in chroma directory

### Resume Parsing Issues
- Ensure file is readable format (PDF/DOCX/TXT)
- Check file size is reasonable
- Review error logs for specific errors

### Database Issues
- For SQLite: Delete `.db` file and restart (will reinitialize)
- For PostgreSQL: Check connection string and credentials
- Verify database server is running

## Contributing

Follow these guidelines:
- Use type hints in Python
- Follow PEP 8 style guide
- Write descriptive commit messages
- Add docstrings to functions
- Test new features

## License

Campus AI - All Rights Reserved

## Support

For issues and support:
1. Check the troubleshooting section
2. Review API documentation at `/docs`
3. Check application logs
4. Contact development team
