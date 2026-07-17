# Testing guide (for the maintainer)

Manual pass to run through after any change to `app.py`, since there's no
automated test suite yet — this is what "does it actually work" means here.

## 1. Start it

```bash
source .venv/bin/activate   # or your venv
streamlit run app.py
```

Opens at `http://localhost:8501`. Watch the terminal for tracebacks while
you click through — Streamlit prints Python errors there, not always
obviously in the browser.

## 2. Walk through every sample broad type

For each of the 6 options in **Sample broad type**, confirm the right extra
fields appear immediately (no submit needed — picking the type alone
should reveal them):

- [ ] **Organism** → subtype dropdown (Multicellular/Community/Microbe)
- [ ] **Rock** → subtype dropdown (Primitive/Igneous/Metaphoric/Sedimentary)
      + Organic Yes/No + Amorphous Yes/No
- [ ] **Blob** → AqSoluble Yes/No + Macromolecular Yes/No
- [ ] **Ice** → Water ice Yes/No + Solid/Liquid
- [ ] **Mixed** → no extra fields
- [ ] **Extract** → no extra fields

## 3. Validation checks (submit without saving real data first)

- [ ] Leave a required field blank (e.g. registrant name) → submit → get
      "Please fill in: ..." naming the right field(s), and **nothing
      written to the register** (check the Google Sheet row count didn't
      change)
- [ ] Type an 11+ word description → submit → get the word-count error
- [ ] Pick action = "Other" but leave the detail box blank → submit → get
      the "action detail required" error
- [ ] Pick action = "Other" with a detail filled in → submit → confirm
      the register's `action` column stores your detail text, not
      the literal word "Other"

## 4. A real end-to-end submission

- [ ] Fill in a complete, valid form for one sample type (pick one you
      haven't used for real data before, e.g. use "TEST" in the
      description so it's easy to find and delete later)
- [ ] Submit → confirm you get: a sample ID, the ODR record caption, a
      label image on screen, and a working "Download label PNG" button
- [ ] Open the label PNG → confirm the ID, type label (e.g. "Rock
      (Igneous)"), today's date, and QR code all look right
- [ ] Open the register Google Sheet directly → confirm a new row
      appeared with all the fields you entered in the right columns
- [ ] Open the summary Google Sheet → confirm the count for that sample's
      row/column combination went up by 1 (only applies to columns that
      already exist in that sheet — see `SUMMARY_COL_MAP` in `app.py`)

## 5. Uniqueness check

- [ ] Submit two samples back to back → confirm they get different
      sample IDs (this is automatic, just confirming nothing's broken)

## 6. Cleanup after testing

Since there's no "delete" button in the app, remove any test rows you
added directly in the Google Sheet (register + summary) once you're done,
so they don't pollute the real data.

## Not yet testable

Pushing a registered sample into ODR itself isn't wired up yet (blocked
on credentials — see "ODR setup" in `setup.md`), so there's nothing to
test there until that's unblocked.
