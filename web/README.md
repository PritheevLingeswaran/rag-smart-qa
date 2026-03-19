# RAG Smart QA — Frontend

A production-quality Next.js frontend for the RAG Smart QA document intelligence platform.

---

## Stack

| Layer | Technology |
|---|---|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript |
| Auth | Auth.js v5 (NextAuth) |
| Providers | Google OAuth, GitHub OAuth |
| Styling | CSS Modules + CSS Variables |
| Backend | FastAPI (via central API client) |

---

## Quick Start

### 1. Clone and install

```bash
git clone <your-repo>
cd rag-smart-qa
npm install
```

### 2. Configure environment variables

```bash
cp .env.example .env.local
```

Edit `.env.local` and fill in all values:

```env
# Required — generate with: openssl rand -base64 32
AUTH_SECRET=

# GitHub OAuth — create at https://github.com/settings/developers
# Callback URL: http://localhost:3000/api/auth/callback/github
AUTH_GITHUB_ID=
AUTH_GITHUB_SECRET=

# Google OAuth — create at https://console.cloud.google.com/
# Callback URL: http://localhost:3000/api/auth/callback/google
AUTH_GOOGLE_ID=
AUTH_GOOGLE_SECRET=

# FastAPI backend URL
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Optional: server-side API key for backend
BACKEND_API_KEY=

NEXTAUTH_URL=http://localhost:3000
```

### 3. Run the development server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## OAuth Setup

### GitHub

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. New OAuth App
3. **Homepage URL**: `http://localhost:3000`
4. **Authorization callback URL**: `http://localhost:3000/api/auth/callback/github`
5. Copy Client ID and Client Secret → `.env.local`

### Google

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → APIs & Services → Credentials → Create OAuth 2.0 Client ID
3. **Application type**: Web application
4. **Authorized redirect URI**: `http://localhost:3000/api/auth/callback/google`
5. Copy Client ID and Client Secret → `.env.local`

---

## Project Structure

```
src/
├── app/
│   ├── (marketing)/          # Public marketing site
│   │   ├── layout.tsx         # MarketingNav + Footer
│   │   └── page.tsx           # Landing page
│   ├── (auth)/               # Auth pages (no sidebar)
│   │   ├── layout.tsx
│   │   └── signin/page.tsx    # Sign in with Google/GitHub
│   ├── (app)/                # Authenticated app shell
│   │   ├── layout.tsx         # AppSidebar + AppTopBar
│   │   ├── dashboard/
│   │   ├── chat/
│   │   ├── documents/
│   │   │   └── [id]/
│   │   ├── upload/
│   │   ├── summaries/
│   │   └── settings/
│   ├── api/auth/[...nextauth]/ # Auth.js route handler
│   ├── globals.css            # Design tokens + base styles
│   └── layout.tsx             # Root layout
├── auth.ts                    # Auth.js configuration
├── middleware.ts              # Route protection
├── components/
│   ├── ui/
│   │   ├── ThemeProvider.tsx   # Dark/light theme context
│   │   └── ThemeToggle.tsx     # Theme toggle button
│   ├── marketing/
│   │   ├── MarketingNav.tsx
│   │   └── MarketingFooter.tsx
│   └── app/
│       ├── AppSidebar.tsx
│       └── AppTopBar.tsx
├── lib/
│   ├── api.ts                 # FastAPI client (all endpoints)
│   └── utils.ts               # Helpers (formatBytes, etc.)
└── types/
    └── next-auth.d.ts         # Session type augmentation
```

---

## Route Map

| Route | Access | Description |
|---|---|---|
| `/` | Public | Marketing landing page |
| `/signin` | Public | Sign in (Google / GitHub) |
| `/dashboard` | 🔒 Auth | User dashboard |
| `/chat` | 🔒 Auth | Ask questions (+ citations panel) |
| `/documents` | 🔒 Auth | Document library |
| `/documents/[id]` | 🔒 Auth | Document detail |
| `/upload` | 🔒 Auth | Upload documents |
| `/summaries` | 🔒 Auth | AI-generated summaries |
| `/settings` | 🔒 Auth | User settings |

---

## Backend Integration

All API calls go through `src/lib/api.ts`. The client supports:

- Bearer token auth (`Authorization: Bearer <token>`)
- API key auth (`x-api-key: <key>`)
- Automatic error handling via `ApiError`

### Endpoints wired up

```typescript
// Chat
postQuery(body)                    // POST /api/v1/chat/query
getChatSessions()                  // GET  /api/v1/chat/sessions

// Documents
getDocuments()                     // GET  /api/v1/documents
getDocument(id)                    // GET  /api/v1/documents/{id}
getDocumentSummary(id)             // GET  /api/v1/documents/{id}/summary
uploadDocument(file)               // POST /api/v1/documents/upload
deleteDocument(id)                 // DELETE /api/v1/documents/{id}

// Settings
getSettings()                      // GET  /api/v1/settings
updateSettings(settings)           // PATCH /api/v1/settings
```

---

## Design System

- **Color scheme**: Warm gold (`#c8a96e`) accent on deep charcoal (dark) / warm ivory (light)
- **Typography**: Syne (display/headings) + DM Sans (body) + JetBrains Mono (code/meta)
- **Themes**: Dark (default) and light — persisted to `localStorage`, no flash
- **CSS Variables**: All design tokens in `globals.css` under `:root` and `[data-theme]`

---

## Production Deployment

### Vercel (recommended)

```bash
npm install -g vercel
vercel
```

Set all environment variables in the Vercel dashboard. Update OAuth callback URLs to your production domain.

### Environment variables for production

```env
NEXTAUTH_URL=https://yourdomain.com
AUTH_SECRET=<generate-strong-secret>
AUTH_GITHUB_ID=<prod-github-id>
AUTH_GITHUB_SECRET=<prod-github-secret>
AUTH_GOOGLE_ID=<prod-google-id>
AUTH_GOOGLE_SECRET=<prod-google-secret>
NEXT_PUBLIC_API_BASE_URL=https://your-backend.com
```

---

## License

MIT
