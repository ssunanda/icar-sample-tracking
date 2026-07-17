# ODR Integration Code

All code that interfaces with the Open Data Repository (ODR) API lives in this
folder. The rest of the repo (`SCOBI_*.ipynb`, `raw_main/data/`) handles local
data acquisition and parsing; this folder handles everything that leaves the
local machine.

## Layout

```
odr/
├── client/      Core ODR REST client (auth, CRUD, file upload)
├── upload/      Scripts that push records & files to ODR
├── sync/        Bidirectional sync (local <-> ODR) with conflict resolution
├── debug/       One-off scripts probing auth endpoints & API quirks
├── notebooks/   Interactive ODR client tester
├── docs/        Design docs for sync + metadata systems
└── samples/     JSON snapshots of record structures (reference for field shape)
```

## `client/` — API wrapper

| File | Purpose |
|---|---|
| `ODR_API_Client.py` | `ODRAPIClient` class. Token auth with auto-refresh, `get_dataset`, `get_record`, `create_record`, `push_record`, `upload_file`, `set_field_value`, `extract_and_download_all_files`. Every HTTP call goes through `_make_request()` so tokens refresh transparently. |

## `upload/` — push scripts (newest first)

| File | Date | Purpose |
|---|---|---|
| **`test_push_real_record.py`** | **Feb 20** | **Most recent push script.** Creates a record in dataset `063c0d3d…`, sets `Source ID` + `Source Links`, then uploads `isotopic/magnetite/Pillinger_1999.csv`. End-to-end reference for new uploads. |
| `upload_complete_all_fields.py` | Jan 8 | Full-field upload: populates every metadata field on a record (sample class/subclass, citation, data file). |
| `upload_complete_record.py` | Jan 8 | Earlier version of the full-field uploader. |
| `batch_upload_to_odr.py` | Jan 8 | Iterates `defs/all_raw_records.csv`, creates a record per row, uploads the associated CSV. Bulk entry point. |
| `test_single_upload.py` | Jan 8 | Smoke test for the single-record upload path. |
| `test_push_record.py` | Jan 6 | Earliest push experiment. |
| `update_pillinger_record.py` | Jan 6 | Patches an existing record in place (example of modify-and-push-back). |
| `add_sample_type_options.py` | Jan 6 | Admin helper: adds new option values to `Sample Type` radio field. |

## `sync/`

| File | Purpose |
|---|---|
| `SCOBI_sync_manager.py` | Original bidirectional sync (MD5 + `.scobi_sync_cache.json`). Six change states; four conflict strategies. |
| `SCOBI_sync_manager_v2.py` | Revision adding parallel sync. Both are still present — v2 is not yet canonical. |
| `example_sync.py` | Worked example of sync usage. |

## `debug/`

Throwaway scripts from Jan 7 debugging session: `debug_odr_api.py`,
`debug_odr_minimal.py`, and three auth probes (`test_auth_endpoints.py`,
`test_jwt_endpoints.py`, `test_session_auth.py`). Safe to delete once the
auth flow is stable.

## `docs/`

- `SYNC_DESIGN.md` — sync architecture, state diagram, edge cases.
- `SYNC_README.md` — user-facing sync quickstart.
- `METADATA_GUIDE.md` / `LOCAL_METADATA_SYSTEM.md` — metadata field conventions.

## `samples/`

- `sample_record.json` — a populated record fetched from ODR.
- `complete_record_structure.json` — template showing every field a record can carry.

## Most recent push code

`odr/upload/test_push_real_record.py` (Feb 20, 2026) is the newest code that
actually pushes data to ODR. It is the canonical reference for the
create-record → add-metadata → upload-file flow.
