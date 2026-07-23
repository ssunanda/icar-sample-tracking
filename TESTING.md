# Testing guide (for the maintainer)

Manual pass to run through after any change to `registration.py` /
`odr_common.py` / `log_an_action.py` — no automated test suite,
this is what "does it actually work" means here.

## 1. Start it

```bash
source .venv/bin/activate   # or your venv
streamlit run app.py
```

Opens at `http://localhost:8501`. Watch the terminal for tracebacks
while you click through — Streamlit prints Python errors there, not
always obviously in the browser.

- [ ] **Password gate check:** confirm `http://localhost:8501` shows
      the password screen first, not the form. Also check
      `http://localhost:8501/log_an_action` (Streamlit's URL slug
      for `log_an_action.py`) directly in the browser — it must
      **also** show the password screen, not the page itself. If it
      shows the page directly, something is auto-exposing it again
      (e.g. it got moved back into a folder named `pages/`) and the
      password gate is being bypassed - see `ACCESS_CONTROL_HISTORY.md`.
- [ ] **Lockout check:** enter the wrong password 5 times in a row →
      5th attempt should say "locked out for 15 minutes," and even the
      *correct* password should be rejected while locked out. Don't
      actually wait 15 minutes to confirm it clears - just confirm the
      lockout itself triggers correctly.

## 2. Sample category

- [ ] All 6 options (Organism/Rock/Blob/Ice/Mixed/Extract) selectable,
      no extra fields appear for any of them — the form stays flat.
      (Subtype-level detail is ODR-only now, not in Streamlit — see
      "What's in Streamlit vs. ODR-only" in `setup.md`.)

## 3. Subsample mode

- [ ] Pick "Subsample of an existing sample," enter a sample ID that
      doesn't exist → submit → get a clear "not found" error
- [ ] Enter a real parent ID → generates `<parent>-A`; submit a second
      subsample of the same parent → generates `-B` (increments, no
      collision)
- [ ] Register CSV row for a subsample: `sampleID` = parent's ID,
      `parent_sample_id` = filled in — confirms the sharing convention
      (search by `sampleID` to find a family together)

## 4. Validation checks (submit without saving real data first)

- [ ] Leave a required field blank (e.g. point of contact name) → submit →
      "Please fill in: ..." naming the right field(s), nothing written
      to the register (check the Sheet row count didn't change)
- [ ] Type an 11+ word description → submit → get the word-count error

## 5. A real end-to-end submission

- [ ] Fill in a complete, valid form (use "TEST" in the description so
      it's easy to find and delete later)
- [ ] Submit → confirm you get: a sample ID, a label image on screen,
      a working "Download label PNG" button, and no tracebacks in the
      terminal
- [ ] Open the label PNG → confirm the ID, type label, today's date,
      and QR code all look right, and the QR code actually opens the
      sample's ODR record in a browser
- [ ] In ODR, confirm: the new record exists with the fields you
      entered, a "Register" event exists under it with the label image
      attached
- [ ] Open the register Google Sheet → confirm a new row appeared with
      everything in the right columns, including `record_uuid` and the
      real ODR `URL`
- [ ] Click "Register another sample" → confirm the result panel
      clears and the form resets

## 6. Log an action page

- [ ] Search the TEST sample from above by ID → confirm its "Register"
      event shows up in the history
- [ ] Log a new event (pick anything but "Register" — that's not an
      option here on purpose) → submit → confirm no tracebacks
- [ ] Re-search the same sample → confirm **both** events now show
      (this is the "child records aren't additive" bug we hit once —
      re-verify it stays fixed if you touch `odr_push_child_record`)

## 7. Uniqueness check

- [ ] Submit two new (non-subsample) samples back to back → confirm
      different sample IDs

## 8. Cleanup after testing

No delete button anywhere. Remove test rows from the register +
summary Google Sheets, and delete test records from ODR (search
"TEST" in Sample ID) once you're done.
