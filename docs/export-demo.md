# Export demo for November 5

The export opens from **Export data** under **Manage data** in the left sidebar. It is
an integrated modal with dataset selection, Generic/Brand choice, optional
inclusive alphabetical name bounds, and five selectable columns per dataset.
The optional preview and separate data screen are omitted.

## Meeting action items

### Implementation

- [x] Build the responsive pop-out export modal using existing form controls.
- [x] Switch column checkboxes between Initial Data and RxNorm.
- [x] Connect dataset, name type and name range to the teammate's export query.
- [x] Project checked columns into a downloadable UTF-8 CSV.
- [x] Check empty results, failed requests, range validation and mobile layouts.
- [x] Open [PR #9](https://github.com/grey-box/Project_Codex/pull/9) from
  `codex/medication-export-modal` into our current working branch,
  `codex/branden-stephen-integration`. Owner: Branden.
- [ ] Review the implementation and meeting notes with the team. Owner: Branden.
- [ ] Get the RxNorm column screenshot from the teammate for visual comparison.
  Owner: Branden. The current backend schema already establishes the five keys,
  so this is not an implementation blocker.
- [ ] Demo the basic export to Nathan on Thursday, November 5. Owner: team.
- [ ] Record Nathan's feedback as next-sprint tasks. Owner: team.
- [ ] Post standup updates more frequently. Owner: team, ongoing.

### Later

- [ ] Normalize column names across datasets.
- [ ] Add dataset options and column definitions as new datasets are supported.

## Teammate integration

Bevin's `/csv` route and query helpers come from
[`feature/spreadsheet-drug-list` at `5cd857f`](https://github.com/grey-box/Project_Codex/tree/5cd857f).
The existing ACL backend remains intact.

Gregorio's `convertJsonToCsv` and `downloadCsv` helpers and 13 conversion tests
come from commit [`16b64c6`](https://github.com/grey-box/Project_Codex/commit/16b64c662f70c9fc82bff987ddc29f4ef7c0626f)
on [`feature/drug-list-export-g01`](https://github.com/grey-box/Project_Codex/tree/feature/drug-list-export-g01).
The integration does not add his standalone sample-data test page. The helper's
control-character regex has a focused lint exception to retain its formula
protection; the test import uses this workspace's compiled test layout.

Gregorio's branch still has an older RxNorm query that returns normalized
ingredient/brand fields. Bevin's November 3 update returns the original RxNorm
properties. This modal follows Bevin's newer contract and reuses Gregorio's
schema-independent CSV helpers, avoiding a merge that restores the old schema.

| Dataset | Backend source value | Columns |
| --- | --- | --- |
| Initial Data | `demo` | `generic_name`, `brand_name`, `country`, `original_language`, `translated_language` |
| RxNorm | `rxnorm` | `conceptID`, `ds`, `name`, `rxcui`, `tty` |

The UI sends `GET /csv` with `source`, `name_type`, `start_name` and `end_name`.
Blank bounds are omitted. Both bounds are inclusive and case-insensitive, using
the backend's lexical comparison of full names. In Initial Data, `name_type`
chooses the generic or brand field used for the range; both columns remain
available for export. RxNorm selects `IN` ingredient or `BN` brand records.
Column selection is applied during CSV conversion, preserving database keys.

Requests are cancellable when closing the modal. Empty responses and errors
produce toasts and no file. The modal keeps settings for retry. CSV conversion
retains escaping, formula protection and the UTF-8 BOM from Gregorio's helpers.

## Demo preparation

The current local Neo4j API returns 102 Initial Data rows; an exact inclusive
`ibuprofen` to `ibuprofen` range returns 11. The local RxNorm export currently
returns zero records. To demonstrate RxNorm with actual data, the backend team
must load that dataset first. Synthetic RxNorm records are used only in the
isolated database and browser tests, never as production fallback data.

Open the modal, pick the dataset and name type, enter optional full-name bounds,
choose columns, and select **Download CSV**. Confirm the file's headers match
the selected dataset and that unchecked columns are absent. Then test a name
range with no matches to show the recoverable feedback.

## Verification commands

```sh
cd frontend
npm run lint
npm run build
npm test
npm run test:ui
```

All 52 browser scenarios passed across the complete run and a targeted rerun.
The optional live export check also passed, downloading an 11-row CSV through
the real preview/API/Neo4j path without intercepted responses.

Run an optional live download check against the local preview without
intercepted API data:

```sh
CODEX_LIVE_EXPORT_URL=http://127.0.0.1:9403/ npm run test:ui -- tests/browser/live-export.spec.ts --workers=1
```

From the repository root, verify the backend using its disposable Neo4j service:

```sh
docker compose -p codex-export-verification -f backend/codex_build/tests/compose.acl.yml up --build --abort-on-container-exit --exit-code-from test-runner
docker compose -p codex-export-verification -f backend/codex_build/tests/compose.acl.yml down
```

All 40 backend tests and 30 unit tests passed. The backend run includes eight
export cases for real query execution, inclusive bounds, brand filtering,
RxNorm properties/types, empty results and invalid filters, plus the existing
authentication/bootstrap/metadata regression checks.
