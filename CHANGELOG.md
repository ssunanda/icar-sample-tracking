# Changelog

Dated log of notable changes to this repo/app. Newest first. For
pending/planned work, see this repo's GitHub Issues (migrated from
`TODO.md` on 2026-09-27 - older entries below still reference
`TODO.md` as it existed on that date, left as-is since they're a
historical record).

## 2026-09-27

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
