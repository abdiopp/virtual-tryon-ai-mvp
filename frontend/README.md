# Virtual Try-On Frontend

This folder contains a new Next.js 15 App Router frontend that integrates with the existing backend in the repository root.

## Stack

- Next.js 15
- TypeScript
- Tailwind CSS
- ShadCN-style UI components
- TanStack Query
- Axios
- Zod

## What It Covers

- Backend health dashboard
- Garment generation form
- Virtual try-on upload flow
- Virtual try-on file-path flow
- Local browser history of successful jobs
- Safe local preview of backend-generated files

## Setup

```bash
cd frontend
cp .env.example .env.local
npm install
```

## Environment Variables

- `BACKEND_API_URL` - URL of the existing backend, usually `http://localhost:8000`
- `NEXT_PUBLIC_APP_NAME` - App name shown in the shell
- `NEXT_PUBLIC_API_BASE_PATH` - Public proxy path used by the browser, default `/api/backend`

## Run Locally

Start the backend first, then the frontend:

```bash
# terminal 1
uvicorn app.main:app --host 0.0.0.0 --port 8000

# terminal 2
cd frontend
npm run dev
```

Open `http://localhost:3000`.

## Build

```bash
cd frontend
npm run build
```

## Deployment Notes

- The browser talks only to the Next.js app.
- Next.js proxies API traffic to the backend through `/api/backend/*`.
- The file preview route serves backend-generated files from the local workspace.
- If you deploy frontend and backend separately, ensure the backend path is mounted or adjust the preview strategy accordingly.

## API Integration Approach

- Client components use TanStack Query for loading, error, and retry states.
- Axios is centralized in `lib/api/client.ts`.
- Zod schemas in `lib/schemas.ts` validate all backend request and response payloads.
- All backend calls use the original API shapes, so the backend can remain unchanged.

