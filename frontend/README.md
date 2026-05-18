# Frontend (Carval.ai)

React 19 + Vite SPA. See the [root README](../README.md) for the full picture.

## Scripts

```bash
npm run dev            # Vite dev server on :5173 with /api proxy to :8000
npm run build          # production build into dist/ (used by the backend Dockerfile)
npm run lint           # ESLint
npm run cypress:open   # interactive E2E
npm run cypress:run    # headless E2E
```

## Notable folders

- `src/pages/`         — Landing, Login, Register, Dashboard, Valuation, Admin
- `src/components/`    — shared UI (Navbar, AiThinking overlay, ValuationResult hero, admin/*)
- `src/hooks/usePollingStatus.js` — polls a status endpoint while a job is running
- `src/lib/errors.js`  — `showErrorToast(err, fallback)` — central error → toast adapter
- `src/api/`           — axios clients (`/auth`, `/valuations`, `/subscription`, `/admin`)

## Production build

In production the SPA is **not** served by its own container. Vite builds into
`frontend/dist/`, which the backend Dockerfile copies into the FastAPI image
and exposes via `StaticFiles` with an SPA fallback. Same origin, no CORS, no
nginx hop.
