# Changelog

Dated log of notable changes to this repo/app. Newest first. For
pending/planned work, see `TODO.md`.

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
