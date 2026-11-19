# Medical Codex frontend

React, TypeScript, Vite and Tailwind. Run `npm ci` and `npm run dev` from this
directory. Vite uses port 9000. The API defaults to `http://localhost:8000`.
Set `VITE_API_BASE_URL` to use a different API host.

The Purist workspace is integrated into `branden-branch`. Its backend, access
controls, backend tests and existing research notes are preserved. Search,
translation, language loading and optional sign-in retain their existing API
contracts. The OCR interface needs an API that provides `/ocrmatching/`; that
endpoint is not in this branch's backend yet.

## Checks

- `npm test`: population-stream regression tests.
- `npm run lint`: ESLint across the frontend.
- `npm run build`: TypeScript and the production Vite build.
- `npm run test:ui`: Playwright workspace, OCR and responsive browser tests.

Run `npx playwright install chromium` once before the browser tests. To use an
existing Chromium installation, set `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` to its
executable. Tests start Vite on port 9402 and intercept API requests. They do not
need backend credentials and do not ingest data.

See [responsive implementation and verification](../docs/responsive-workspace.md)
for the breakpoints, component map, phone setup and validation scope.
