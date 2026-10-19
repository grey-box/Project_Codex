# Medical Codex frontend

React, TypeScript, Vite and Tailwind. The client currently calls the local API at
`http://localhost:8000` (see `src/services/api.ts`). Run `npm ci` and `npm run dev`
to start the frontend. The repository Docker configuration starts the full stack.

## Checks

- `npm test` — 17 population-stream tests using TypeScript and Node's test runner.
- `npm run lint` — ESLint across the frontend.
- `npm run build` — TypeScript and the production Vite build.
- `npm run test:ui` — Playwright workspace regression tests. Run
  `npx playwright install chromium` once first. The tests start Vite automatically
  on port 9402 and intercept API calls; no backend, credentials or data ingestion
  are required.

For an existing local Chromium installation, set
`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` to its executable when running UI tests.
The checked behavior includes keyboard result selection, filter reset restoring
cached records, translation destination changes, stale responses, loading and
error recovery, localized workspace copy, and four responsive widths.

See [workspace design and repository review](../docs/workspace-review.md) for
Purist/Mobbin references, scope and backend integration follow-ups.
