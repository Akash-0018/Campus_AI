# Campus AI Frontend

Modern React.js (TypeScript) frontend for the Campus AI recruitment platform.

## Tech Stack

- **Framework**: React 18
- **Language**: TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios
- **State Management**: React Query
- **Routing**: React Router v6
- **UI Components**: Custom + Radix UI primitives

## Setup

### Install Dependencies

```bash
npm install
# or
yarn install
# or
bun install
```

### Environment Variables

Create a `.env` file:

```env
VITE_API_URL=http://localhost:8000
```

### Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Production Build

```bash
npm run build
```

### Linting

```bash
npm run lint
```

## Project Structure

```
src/
├── components/         # Reusable React components
│   ├── Layout.tsx     # Main layout with navigation
│   └── ProtectedRoute.tsx  # Route protection
├── pages/             # Page components
│   ├── LoginPage.tsx
│   ├── RegisterPage.tsx
│   ├── User/          # User (JobSeeker) pages
│   ├── Recruiter/     # Recruiter pages
│   └── Admin/         # Admin pages
├── contexts/          # React contexts
│   └── AuthContext.tsx # Authentication context
├── hooks/             # Custom React hooks
│   └── useAuth.ts     # Auth hook
├── lib/              # Utilities
│   └── api.ts        # Axios API client
├── App.tsx           # Main app component
├── main.tsx          # Entry point
└── index.css         # Global styles
```

## Authentication

The app uses JWT tokens stored in localStorage:
- `token`: JWT access token
- `userId`: User ID
- `role`: User role (admin, recruiter, user)

Protected routes check for token and role.

## Key Pages

### User (Job Seeker)
- **Dashboard**: Overview and getting started
- **Chat**: Conversational requirements collection
- **Matches**: View matched candidate profiles

### Recruiter
- **Dashboard**: Upload and management stats
- **Resumes**: Upload candidate resumes
- **Profile**: Edit company information

### Admin
- **Dashboard**: System statistics
- **Users**: Manage all users
- **Recruiters**: Manage recruiter accounts

## API Integration

Uses Axios client configured in `src/lib/api.ts`:
- Base URL from `VITE_API_URL` env variable
- JWT token automatically added to requests
- Error handling and interceptors

## Styling

Using Tailwind CSS utility classes. Custom components use semantic HTML with Tailwind.

## Contributing

- Follow TypeScript strict mode
- Use meaningful component names
- Keep components focused and reusable
- Add JSDoc comments for complex logic

## Deployment

### Vercel/Netlify

1. Push to Git repository
2. Connect repository
3. Set `VITE_API_URL` environment variable
4. Deploy

### Manual

```bash
npm run build
# Deploy dist/ folder to any static hosting
```

## Troubleshooting

### API Connection Issues

- Check `VITE_API_URL` in `.env`
- Ensure backend is running on correct port
- Check browser console for CORS errors

### Build Errors

- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Check Node.js version (requires Node 18+)

### Port Already in Use

- Change Vite port in `vite.config.ts`
- Or kill process on port 5173

## License

Campus AI - All Rights Reserved
