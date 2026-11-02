# Backend and branch integration review

Reviewed November 1, 2026 on `codex/branden-stephen-integration` after fetching origin.

## Running application

The root Compose file starts `backend/codex_build/api.py`. The separate
`main.py` application and its drugs, conditions, sources and translation routers
are not registered in this entry point. The frontend calls `/languages`,
`/search`, `/translate`, `/api/login`, `/packs/load`, `/api/populate-sources`
and `/ocrmatching/`.

The local API and Neo4j were stopped. The existing API container originally
mounted a different checkout and used an older image without PyJWT. Recreating
it from this checkout, rebuilding, and adding its missing bcrypt dependency
restored startup. The Vite `/backend` development proxy connects the preview
without expanding backend CORS permissions. For local development, set
`VITE_API_BASE_URL=/backend` in `frontend/.env.development.local`. For the
Docker frontend, set `CODEX_API_PROXY_TARGET=http://api:8000` if using that proxy.
Production deployments must configure `VITE_API_BASE_URL` for their backend.

Live checks passed for API/Neo4j health, search, and all bundled Russian and
Ukrainian translations: 10 Russian entries and 18 Ukrainian entries across
9 Ukrainian terms. Data in these files is demo content, not clinical validation.
The observed database contained 11 Term nodes and no imported Drug or Condition
nodes. External provider ingestion has not been verified. No provider keys
were submitted and no bulk import was started during this review.

## Language fixes

Russian and Ukrainian data options previously selected interface languages
without corresponding UI resource files. Added both resource files, translated
tool dialogs and validation messages, localized country labels, and made the
language menu close after selection. Backend country metadata now follows
Sebastian's country-discovery approach from commit `3814fe2`, retaining this
branch's authentication routes. The frontend uses returned countries and keeps
static mappings only as compatibility fallback for older APIs.

## Branch inventory and remaining integration

All 20 remote branch tips were inventoried. Relevant backend route definitions,
frontend locale resources, dependency files and current feature differences
were compared; archived source-loader branches were checked as historical work.
This is an integration review, not a complete security or clinical audit.

| Branch | Relevant work and integration status |
| --- | --- |
| `branden-branch` | Responsive workspace and basic JWT/account backend; integration baseline. |
| `codex/branden-stephen-integration` | Reconciled responsive workspace, Stephen components and account flow; current review branch. |
| `stephen-nav-bar-ui-branch` | Navigation/login UI cherry-picked with original authorship. Its backend ancestry also contains OCR and dynamic countries but lacks the current login API. |
| `left_nav_bar_ui` | Earlier navigation UI, with OCR/dynamic-country backend ancestry. |
| `sebastian-branch` | Dynamic country mapping, modular demo loading, OCR and Docker startup changes. Do not replace the current API wholesale because it would remove login/access-control routes. |
| `asu-ui-branch` | Shared UI/OCR/dynamic-country lineage and Neo4j health-check change. |
| `acl-branch` | Newer database-backed role checks, user-management safeguards and OCR integration. These updates remain to be reconciled with the current backend. |
| `arshit-frontend-auth` | Authentication/admin-management prototype; current UI uses server-token sign-in, not its full admin interface. |
| `feature/spreadsheet-drug-list` | `/csv` catalogue endpoint returning JSON. Not registered in the current backend. |
| `josh/api-test-infrastructure` | Disposable Neo4j/pytest smoke-test infrastructure. Not integrated; current tests must not wipe the development database. |
| `logan-branch` | OCR pipeline ancestry. Current API has no OCR router or runtime dependencies. |
| `feat/security-encryption-utilities` | Crypto/hash/vault helpers and tests; not wired into current application behavior. |
| `codex/ic2-population-errors` | Earlier responsive UI and population-stream error handling, plus OCR ancestry. |
| `main`, `main-refactored` | Older project baselines. |
| `frontend-demo` | Earlier search/CSV UI work. |
| `configuring-source-loaders`, `rxnorm-api-loader` | Historical source-ingestion implementations. |
| `new-patch-main`, `sofievargas-patch-1` | Historical documentation/API updates. |

OCR is not working in this runtime: `/ocrmatching/` is absent. Importing its
branch also requires reviewing PaddleOCR/model downloads, image validation and
ClamAV configuration. The UI's mocked OCR tests do not demonstrate live OCR.

Population and pack import remain protected and return 401 without a session.
A negative login check also returned 401. Successful real-user login and
provider-authorized ingestion still need account/credential-backed verification.

External source loaders populate a separate Drug/DrugName/Condition schema,
while current search/translation use Term/Translation nodes. Registering or
bridging those query paths is necessary before claiming the entire external
catalogue is searchable in this workspace. `neo4j_sources/db.py` also imports
`config` from the old location, which must be reconciled before enabling the
unused `main.py` router stack.

## Appearance and motion

Light mode retains the approved pale surfaces and forest sidebar. Dark mode
uses neutral charcoal surfaces. Its Search action and selected navigation use
the same forest green; light mode's action is slightly lighter. Native CSS
handles popovers, dialogs, drawer entry, hover and desktop grid collapse.
Language changes use the browser's Web Animations API for a brief fade without
remounting application state. No animation dependency was added. Reduced motion
bypasses those effects. Wrapped navigation labels share left alignment and a
fixed icon column.
