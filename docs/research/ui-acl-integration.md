# UI Research: Integrating the Access List (ACL) API

Author: Branden Chong (Codex UI, codex-asu-cidse2026f)
Date: 10/10/2026
Branches reviewed: `sebastian-branch` (e2c0270), `logan-branch` (d74af9c), `acl-branch` (7b12430)

## Goal

The Access List team (codex-asu-cidse2026w) has added login and role checks to the
FastAPI backend on `acl-branch`. This document records what the UI needs to change
to work with it, and which existing UI branch is the best base for that work.

## 1. State of the UI branches

| Branch | Front end shape | API calls | Notes |
|---|---|---|---|
| `sebastian-branch` | Split into components (`components/search`, `results`, `translation`, `import`, `populate`, `layout`, `ui`) | Mostly in `src/services/api.ts`, but `ImportLanguageModal.tsx` and `PopulateDropdown.tsx` call `fetch` directly | Tailwind v4, typed responses in `src/types/codex.ts` |
| `logan-branch` | One `App.tsx` (1,021 lines) plus `App.css` (742 lines) | All `fetch` calls inline in `App.tsx` | Newest features: OCR upload (`/ocrmatching/`), choose which languages load, search limited to selected languages |
| `acl-branch` | One `App.tsx` (769 lines), an older copy of Logan's UI | Inline in `App.tsx` | Backend has the new auth code; front end has no auth changes |

All three use React 19, TypeScript 5.9, Vite 8 and i18next, and run the dev server on port 9000.

`API_BASE_URL = 'http://localhost:8000'` is hard coded in several files on every branch.

## 2. What the ACL API exposes (acl-branch)

| Method | Path | Who can call it |
|---|---|---|
| GET | `/health`, `/languages` | anyone |
| POST | `/search`, `/translate` | anyone |
| GET | `/audit/{term}` | anyone |
| POST | `/api/login` | anyone, returns a token |
| POST | `/packs/load` | medical professional, administrator |
| POST | `/api/populate-sources` | medical professional, administrator |
| POST, GET | `/users` | administrator |
| GET, PATCH, DELETE | `/users/{email}` | administrator |
| GET, PUT | `/users/{email}/role` | administrator |

Login flow:

1. `POST /api/login` with `{ "email", "password" }`.
2. Response: `{ "access_token", "token_type": "bearer", "role" }`.
3. Protected calls send `Authorization: Bearer <access_token>`.
4. Tokens are HS256 JWTs that last 24 hours (`ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24`).

Error codes the UI has to handle:

| Code | Meaning | What the UI should do |
|---|---|---|
| 401 | Missing, invalid or expired token, or wrong password | Clear the token and show the login screen |
| 403 | Logged in, but the role is not allowed | Show "You don't have access to this", and hide the control |
| 404 | User not found (user admin screens) | Inline message |
| 409 | User already exists on create | Inline message on the form |
| 400 | Wrong file type on `/packs/load` | Inline message on the import dialog |
| 500 | Server or Neo4j error | Generic error banner |

## 3. Problems found

1. **The UI never sends a token.** No branch sets an `Authorization` header. Once
   `acl-branch` is merged, "Import language pack" and "Populate sources" will fail
   with 401 for everyone.
2. **No login screen exists** on any UI branch.
3. **Role names don't match.** `require_roles` lowercases the user's role and
   compares it with `"medical professional"` and `"administrator"`. The example on
   `UserCreateRequest` uses `"role": "Admin"`, and `role` is a free text `str`, so a
   user created from that example gets 403 on every protected route. Suggest the
   API team use a fixed list (enum) of roles, and the UI use a dropdown instead of
   free text.
4. **CORS conflict between branches.** `acl-branch` allows only
   `http://localhost:9000`. `logan-branch` allows 9000 to 9004, because Logan's
   change lets the dev server move to the next free port. Merging the two must
   keep the wider list, or the UI breaks whenever port 9000 is busy.
5. **Fallback JWT secret.** If `JWT_SECRET_KEY` is not set in `.env`, the API signs
   tokens with `"super-secret-fallback-key"`. Fine for local dev, but it should
   fail loudly in any shared deployment.
6. **Duplicated API base URL.** Should move to one place, read from
   `import.meta.env.VITE_API_BASE_URL` with `http://localhost:8000` as the default.

## 4. Recommendation

Build the ACL work on **Sebastian's component structure**, since it already has a
`services/api.ts` layer, and port Logan's OCR and language selection into it as
components.

Proposed tasks for the UI team:

1. Move every `fetch` into `services/api.ts` behind one helper that adds the
   `Authorization` header and turns 401 and 403 into typed errors.
2. Add an auth context (`AuthProvider`) that holds the token and role. Keep the
   token in memory and `sessionStorage`, not `localStorage`, so it clears when the
   tab closes.
3. Add a login page that calls `POST /api/login`.
4. Hide or disable Import and Populate unless the role is medical professional or
   administrator.
5. Add an admin "Users" page for the `/users` endpoints (list, create, change role,
   delete).
6. Until the API is merged, use a stub mode (`VITE_API_STUB=true`) where the
   service layer returns 200 OK with sample data, as Nathan suggested on 10/08.

Questions for the API team (to agree on the contract):

- What are the exact role strings, and will they be an enum?
- Will there be a `GET /api/me` so the UI can restore a session from a saved token?
- Is there a refresh token, or does the user log in again after 24 hours?
- Can CORS allow ports 9000 to 9004 to match the UI dev setup?
