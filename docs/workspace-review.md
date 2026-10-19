# Medical Codex workspace refresh — IC2

## Design and behavior

The workspace keeps Grey-box evergreen and Source Sans 3. Search has the primary
position, utility tools share a wrapping toolbar, and results sit beside a
translation panel on wide screens. Below 960px the panel follows the results;
phones use medication cards with native selection buttons. Empty, loading,
no-match, request-error and selected states each explain the next action.
Language filters preserve the fetched records so resetting restores matches
without another request. Translation responses are ignored after the selection
or destination changes. Import, OCR and population retain their existing APIs.

Design exploration: [Purist workspace](https://purist.design/file/SprEvCZwabzDFdcZ).
References: [Sprig search and filter hierarchy](https://mobbin.com/screens/561a3aac-ed83-4114-91ee-b0034a366892)
and [Unify results workspace](https://mobbin.com/screens/dde5403f-7fd6-4f4d-9d6f-8bf8c0810e69).
These informed the hierarchy and split layout; no screenshots or third-party
artwork are shipped in the application. Mock medication records remain in tests.

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

Authentication remains a separate integration task with the team's existing
auth work. This refresh adds no authentication implementation or connected-state
claims.

## Validation

`npm test` covers population streams. `npm run test:ui` uses intercepted local API
responses to cover keyboard selection, translation, country changes, reversible
language filters, loading/empty/error/retry states, stale responses, translated
workspace copy, and utility dialogs/dropdowns at 390/768/1024/1440px.
`npm run lint` and `npm run build` are also required. Browser checks exercise
fixtures, not Neo4j, PaddleOCR or external medical-source services.

Implementation and review were assisted by Codex. Team review and live backend
integration remain separate from these automated checks.
