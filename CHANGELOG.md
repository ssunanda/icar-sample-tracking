# Changelog

Dated log of notable changes to this repo/app. Newest first. For
pending/planned work, see this repo's GitHub Issues (migrated from
`TODO.md` on 2026-09-27 - older entries below still reference
`TODO.md` as it existed on that date, left as-is since they're a
historical record).

- **Added `remove_odr_events.py`**, a maintenance script for removing
  stray child (Sample Event) records from an ODR sample without
  touching the others - written after live-verification testing
  accidentally logged 5 stray test events against a real production
  sample (Andrew Mattioda's `dazzling-tiger-of-essence`) instead of a
  `[TEST]`-marked one. Sunanda removed those manually in the ODR
  website UI rather than trust this script's untested deletion path
  on a real record - **not yet verified live**, needs testing against
  a `[TEST]` record first. See the script's own docstring.
- **Reconciled ODR Event Type/Attachment field changes** made directly
  in ODR: "Modify or Process" renamed to "Sample modified or altered"
  (same option UUID, confirmed - renaming an option keeps it like
  renaming a field does), new option "Data pre-processed" added, and
  the "Attachment" field renamed to "Data file" (same field_uuid).
  Updated `log_an_action.py`'s dropdown/help text and
  `ODR_EVENT_TYPE_OPTIONS`/`ODR_EVENT_FIELDS` in `odr_common.py` to
  match. Verified live: submitted a real "Data pre-processed" event
  via browser test, confirmed in ODR it landed correctly.
- **Added a toast confirmation to sample registration too** (matches
  the Log an Action toast added earlier today) - a brief "✅
  Registered!" pop-up right when registration completes, alongside
  the existing success panel. Placed inside the `if submitted:` block
  (not next to the persistent success panel), so it fires once, not
  on every rerun while the result is still showing (e.g. clicking
  "Download label PNG"). Verified live via browser test.
- **Fixed a leaked implementation detail**: the cached
  `odr_search_all_records()` call was showing "Running
  odr_search_all_records()." as its spinner caption during
  registration - a raw Python function name, not something a
  non-technical registrant should see. Now shows "Checking ODR..."
  instead (`show_spinner=` on the `@st.cache_data` decorator).

## 2026-09-27

- **Wired direct ODR querying into the app, replacing the register
  Sheet as the lookup layer** (closes GitHub Issue #1). New helpers in
  `odr_common.py`: `odr_search_all_records()` (paginated, cached 30s),
  `odr_field_value()`, `odr_existing_sample_ids()`.
  - `registration.py`: uniqueness/subsample-parent checks now query
    ODR directly instead of reading the Sheet.
  - `log_an_action.py`: the sample search dropdown is now built
    directly from ODR - every entry is a real record, so the old "no
    ODR record linked" error case is gone (it could only happen via
    the Sheet as an indirect, possibly-stale index).
  - The register Sheet is still written to (not read from) as a
    human-browsable backup log - not fully retired.
  - Verified with a real end-to-end browser test (Playwright): logged
    in, searched and found a real ODR sample via Log an Action, and
    submitted one full test registration (`hulking-masterful-hippogriff`)
    - all worked with no errors, ODR record created correctly.
  - Added unit tests for the new lookup logic in
    `tests/test_odr_common_logic.py`.

- **Pinned all dependency versions** in `requirements.txt` (including
  `cryptography`, a transitive dependency of `google-auth` not
  imported directly anywhere) after a floating version silently broke
  local Sheets access with no code change to explain it - see the
  private key fix below and `TODO.md`.
- **Added an automated test suite** (`pytest`, `tests/`) covering the
  pure-logic pieces: sample/subsample ID generation, ODR institution
  UUID lookups, event-field parsing. No network calls - doesn't
  replace `TESTING.md`'s manual pass, complements it.
- **Added linting** (`ruff`, config in `pyproject.toml`), curated to
  skip flagging this codebase's intentional patterns (broad `except
  Exception` for graceful degradation, the local lambda helper in
  `make_label()`) rather than using a default-strict ruleset.
- **Fixed the local `gcp_service_account.private_key` parse failure**
  and **confirmed the direct ODR search endpoint works live**
  (`POST /dataset/{dataset_uuid}/search/{limit}/{offset}.json`) -
  full details in `TODO.md`. Not yet wired into the app - it still
  reads/writes the register Sheet today.
- Cleaned up the register sheet: removed `durable-caracal-of-lightning`
  (already deleted from ODR).
- Added `remove_register_row.py`, a small maintenance script for this
  kind of cleanup going forward.
- **Added CI** (`.github/workflows/ci.yml`) - runs `pytest` + `ruff`
  on every push/PR. No secrets needed since the test suite makes no
  network calls.
- **Documented a deploy-tagging convention and Cloud Run rollback
  procedure** in `setup.md`. Rollback steps are written from how
  Cloud Run traffic-splitting generally works, not yet verified live
  against this specific service (see `TODO.md`).
- **Added `backup_register.py`** for the register sheet - a single
  rolling backup (not dated history, see `TODO.md` for why) written
  into the previously-unused summary file.
- **Migrated `TODO.md` to GitHub Issues** (17 issues: the open items
  already in `TODO.md`, plus 3 discussed earlier this session but
  never actually logged anywhere - the sample-count matrix, the Hazen
  Lab bulk-import, and per-instrument importers). `TODO.md` is now a
  stub pointing to Issues.
- **First CI run failed immediately** - `ModuleNotFoundError` on
  `registration`/`odr_common`/`log_an_action`. Locally tested with
  `python3 -m pytest`, which auto-adds the repo root to `sys.path`;
  CI runs plain `pytest`, which doesn't. Fixed with an explicit
  `pythonpath` setting in `pyproject.toml` instead of relying on
  invocation style. Confirmed by re-running the exact CI command
  locally before pushing the fix.

## 2026-09-16

Pilot round is live with real users; first round of bug fixes/feature
requests since launch.

- **Fixed "Log an action" swallowing its own success message.**
  `log_an_action.py` called `success(...)` immediately before
  `st.rerun()`, which discards anything rendered in that run before the
  browser paints it - so the confirmation never actually reached the
  user after logging an action. Now stashed in `session_state` and
  shown after the rerun, same pattern `registration.py` already used
  for its own post-submit result.
- **Added a searchable sample picker to "Log an action."** Replaced the
  free-text "type the exact sample ID" box with a searchable dropdown
  (built from the register sheet, includes subsamples) that filters by
  ID or description as you type - removes a whole class of
  case-sensitive typo errors from manual entry.
- **Added a pointer to the Raman resources** (requirements doc,
  databases, instruments list) already added to the DELIMIT Project
  Guide, on both app pages.
- **Added user-facing guidance for deleting a record or logged
  action** to `USER_GUIDE.md` - there's still no delete button in the
  app (on purpose), so this just documents "email Sunanda" as the
  actual process.
- **Fixed stale documentation of the register sheet's `sampleID`
  column** in `setup.md`/`TESTING.md` - both claimed a subsample's row
  stores its *parent's* bare ID in `sampleID`, but the code has always
  stored the subsample's own suffixed ID there (e.g.
  `cool-buffalo-water-A`), with `parent_sample_id` holding the bare
  parent ID separately. This is what `log_an_action.py`'s lookup
  actually relies on; only the docs were wrong.

## 2026-09-08

- **ODR schema fully built out and verified.** Added the 5 new Event
  Type options (Short-term storage, Long-term storage,
  Disposed/Consumed, Lost, Damaged) and wired them into
  `ODR_EVENT_TYPE_OPTIONS`/`log_an_action.py`. Finished building
  Physical/Morphological, Water-ness, Organic Characterization, and
  the full Alteration and Diagenesis breakdown in ODR - all field
  types/options/names cross-checked live against ODR and captured
  accurately in `TODO.md`, including 7 places where the live build
  deviated from the original plan (see `TODO.md` for the full list -
  most notably Mass changed from mg to grams, and Pressure/Temperature
  at Formation got fixed after earlier deviations).
- **Removed "Mass: ___ mg" from the printed label** (`registration.py`
  `make_label()`), since Mass is now recorded in grams in ODR and no
  longer matches that hardcoded mg blank.
- **Added ODR search link and Project Guide guidance to the
  registration page.** "Open Data Repository (ODR)" now links to the
  public search/display view; added a best-judgment guidance note
  pointing to the DELIMIT Project Guide (Google Doc). Lowercased
  "Registration" in the browser tab title.
- **Fixed a Cloud Run deploy failure.** Buildpacks couldn't find an
  entrypoint for the Streamlit app ("provide a main.py or app.py file
  or set an entrypoint...") - added a `Procfile` as the permanent fix.
  Root cause of the confusion during troubleshooting: Cloud Shell's
  home directory (`~`) has its own old, stale checkout of this repo
  separate from `~/icar-sample-tracking` - see `setup.md` "Redeploying
  after a code change" for the fix (always `cd
  ~/icar-sample-tracking` first).
- **Compiled a full DELIMIT sample ontology glossary** (definitions
  for every term in the Coggle mind-map, organized to match the
  diagram's branch structure) for the DELIMIT Project Guide (Google
  Doc). Flagged that the Bioticity branch of the mind-map (Formation,
  Biogenicity, Metabolism, Extancy, Phylogeny, Habitat/Niche) isn't
  built in ODR yet - logged in `TODO.md` as needed soon, but
  explicitly deferred until after the 2026-09-08 team talk.
- **Cleaned up the register Google Sheet** to match ODR after Sunanda
  deleted all ODR sample records and re-registered a single fresh
  example (`godlike-starfish-of-will`) for the doc guide's
  screenshots. The sheet had 15 stale rows left over from deleted
  records; trimmed to the 1 row that matches what's actually live in
  ODR.
- Drafted the Troubleshooting and Glossary section of the DELIMIT
  Project Guide (Google Doc), pulled from the actual error
  messages/behavior in `app.py`/`registration.py`/`log_an_action.py`.
