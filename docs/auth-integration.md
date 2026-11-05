# ACL authentication integration

Integrated November 3, 2026 on `codex/branden-stephen-integration` from
[`acl-branch` at `ff6337f`](https://github.com/grey-box/Project_Codex/tree/ff6337fbb227d07b831e874dc8111de36b29a090).
The source's authentication/user-management functions and CLI session flow are
adapted into the existing backend. The current responsive sign-in dialog is
retained. No UI from `arshit-frontend-auth` is included.

## Contract and behavior

- `POST /auth` accepts JSON `{ "email": "...", "password": "..." }` and returns
  `access_token`, `token_type` and `role`. Frontend and CLI use this route.
- Passwords are checked against bcrypt hashes in Neo4j. Tokens expire after
  24 hours. The frontend keeps its bearer token in memory and clears it on
  refresh or sign-out.
- Protected requests reload the user's current database identity and role.
  Deleted users receive 401; a demoted administrator loses administrator access
  even when presenting a previously issued administrator token.
- Administrator-only `/users` operations support create, list, retrieve, update,
  delete and role changes. Self-deletion and removal/demotion of the last
  administrator are rejected by the source branch's checks.
- These administrator API operations are available through the backend and CLI.
  A new administrator-management screen is outside this integration.

Search matching, translation semantics, provider loaders, OCR integration,
deployment ports and CORS policy are not changed by this auth integration.

## Configuration

Set `JWT_SECRET_KEY` to a private, persistent random key in the untracked `.env`
for deployments and multiple workers. When it is absent or blank, the development
API generates a random process-local key, so tokens cannot survive an API restart.

Initial administrator bootstrap is optional. Set both `DEFAULT_ADMIN_EMAIL` and
`DEFAULT_ADMIN_PASSWORD` in `.env` to create the configured account at startup.
Blank or partial configuration does not create an account. Existing accounts are
left intact. The source branch's hardcoded administrator password is not used.
`TESTING=true` disables bootstrap, and `LOAD_DEMO_DATA=false` disables automatic
language-pack loading for isolated tests.

## Verification

Run the ACL integration tests in their own temporary Neo4j service:

```sh
docker compose -p codex-acl-verification -f backend/codex_build/tests/compose.acl.yml up --build --abort-on-container-exit --exit-code-from test-runner
docker compose -p codex-acl-verification -f backend/codex_build/tests/compose.acl.yml down
```

This configuration publishes no database ports, mounts no development database
volume, and stores test data in temporary memory-backed directories. It includes
Ryan's branch integration coverage, metadata/access regression checks and tests
for the explicit administrator bootstrap configuration.

Frontend checks cover the `/auth` contract, token-required sign-in, authenticated
requests, sign-out, protected tool feedback and importing at desktop/phone widths.
The browser scenarios use synthetic intercepted responses. Successful real
database login and administrator operations are verified in the isolated backend
tests; no real user's credentials or account records are needed.

November 3 results: 32 backend tests passed (including three bootstrap
subcases), and all five targeted browser scenarios passed. Frontend lint and
production build passed. The running local API and preview proxy returned healthy
Neo4j status; `/auth` rejected invalid credentials with 401 and `/users` rejected
an unauthenticated request with 401. Temporary test containers were removed after
verification. Successful login to the development database still requires an
existing account or explicitly configured administrator bootstrap credentials.
