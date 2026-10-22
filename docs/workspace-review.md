# Medical Codex workspace refresh — IC2

## Design and behavior

The workspace uses Geist throughout, with quiet gray navigation, fine dividers,
black primary actions and evergreen selection states. The persistent sidebar
contains the existing OCR, population and import controls, while breadcrumbs and
the interface language switcher sit above the workspace. Search and language
filters stay above the results. Results sit beside the translation panel at
1200px and above; the panel follows the results on smaller screens. Below 768px
the sidebar becomes wrapping navigation. Phones use medication cards with native
selection buttons. Empty, loading,
no-match, request-error and selected states each explain the next action.
Language filters preserve the fetched records so resetting restores matches
without another request. Translation responses are ignored after the selection
or destination changes. Import, OCR and population retain their existing APIs.

Design exploration: [Purist workspace](https://purist.design/file/SprEvCZwabzDFdcZ).
References: [Linear navigation](https://mobbin.com/screens/0ac97560-1aef-4907-a356-8c18c749437b),
[Vercel hierarchy](https://mobbin.com/screens/b313e291-3869-43a6-9125-d98cf9f3ccb8),
[Attio tables](https://mobbin.com/screens/2f854791-b0f6-475a-97c3-65e65d5f7581), and
[Vercel sign-in](https://mobbin.com/screens/e839e5dd-ca34-4876-863e-f816ff2757d8).
These informed the hierarchy and split layout; no screenshots or third-party
artwork are shipped in the application. Mock medication records remain in tests.

Geist variable 5.3.0 is self-hosted from Fontsource under the SIL Open Font
License (included in `frontend/src/assets/fonts/OFL-Geist.txt`). Five WOFF2
subsets total about 76 KB and load only for the character ranges used. The
Latin subset is about 29 KB. No runtime dependencies or image assets were added.
The account popup contains sign-in, embedded usage documentation and explicit
Light/Dark choices. The app follows the OS preference initially and stores only
the chosen appearance in local storage. The sidebar uses a simple Codex wordmark;
it is a typographic treatment, not an official supplied logo.

## Repository review

Reviewed the React entry point, all application components, shared controls,
locales, services and types; both FastAPI entry points; the Neo4j translation
service and driver; source ingestion and routers; OCR processing, schemas and
configuration; and Docker/build/test setup. This was a source review, not a
live backend or data-quality certification. Dataset dumps, generated files,
credentials and dependencies were excluded.

Integration follow-ups identified during the review:

- `backend/codex_build/api.py` is the Docker entry point used by the frontend.
  `main.py` exposes another router set with different verbs and response shapes.
  Its database helpers also import bare `config`/`db` modules. Choose and test a
  single supported API before changing the frontend client contract.
- Source ingestion builds `RXN`/`DRUG`/`SNOMED`/`ICD`/`Concept` nodes, while the
  active search/translation driver queries `Term`/`Translation`/`Brand` nodes.
  Confirm how imported sources become searchable; a completed import does not
  establish that connection by itself.
- `ocr/ocrmatching.py` declares `FuzzyMatching` (`results` of required matching
  fields) but returns extracted-text records (`rec_text`, `rec_score`). Align
  extraction, matching and the response model before claiming live OCR works.
- `neo4j_sources/source_data.py` calls `concept_id(...)` inside `drugbank()` while
  assigning that local variable; the helper is named `conceptID`. Its symptom
  helper also reads `source` instead of `symptom`. Exercise a small fixture before
  a full ingest. No source ingestion was started during this UI work.
- `ocr/scan_and_clean_uploadfile.py` joins the client filename directly to the
  quarantine path. Generate a server-owned filename and preserve scan rejection
  status codes before enabling uploads outside a trusted development setup.

The sign-in form uses the `/api/login` email/password and `access_token` contract
from the team's `arshit-frontend-auth` / `acl-branch` work. A missing or rejected
response remains an error; the client requires a nonempty server token before
showing the signed-in email. Tokens stay in memory, attach to existing API calls
and clear on sign-out or refresh. No backend authentication or authorization
rules changed. The current base backend does not include this login endpoint;
live sign-in requires integration with the team's ACL backend. Role management,
server-side session revocation and backend integration are outside this refresh.

## Validation

`npm test` covers population streams. `npm run test:ui` uses intercepted local API
responses to cover keyboard selection, translation, country changes, reversible
language filters, loading/empty/error/retry states, stale responses, translated
workspace copy, loaded Geist faces, and utility dialogs/dropdowns at
390/768/1024/1440px. Additional checks cover persisted appearance, embedded help
and focus restoration, rejected sign-in responses, server-issued token use and
authorization removal on sign-out.
`npm run lint` and `npm run build` are also required. Browser checks exercise
fixtures, not Neo4j, PaddleOCR or external medical-source services.

## OCR upload lifecycle

The scanner accepts nonempty PNG, JPEG and WEBP files up to 10 MB. The chooser
also works with Enter or Space. Replacing an image or closing the dialog aborts
the client request and prevents its results or errors appearing in a later scan.
Preview object URLs are released on replacement, close and component unmount.
Failed requests remain retryable, and a recognized term can still be copied into
the medication search field. Four OCR browser fixtures exercise invalid files,
replacement during a scan, close/reopen, keyboard upload and error recovery.
These checks do not verify live OCR accuracy. Cancellation stops the client
request; a backend job that has already started may continue processing. The
10 MB limit and MIME checks are client controls, not server upload validation.

Implementation and review were assisted by Codex. Team review and live backend
integration remain separate from these automated checks.
