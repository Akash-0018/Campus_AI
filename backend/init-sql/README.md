# Campus AI Database Initialization

## Tables created:
- users: User accounts (Admin, Recruiter, User)
- recruiters: Recruiter profiles
- admins: Admin profiles
- resumes: Resume documents
- requirements: User job requirements
- match_results: Matching results between requirements and resumes

## Initialization steps:

1. All tables are created automatically when the application starts via SQLModel ORM
2. ChromaDB persistent storage is initialized at `./chroma_data` directory
3. Resume upload directory is initialized at `./uploads/resumes` directory

## Database Schema notes:
- Uses SQLite locally for development
- Can switch to PostgreSQL for production
- All models use SQLModel for type safety and validation
- Automatic timestamp fields (created_at, updated_at) on all models
