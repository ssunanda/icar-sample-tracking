# Next steps

- [x] Add 5 new Event Type options in ODR (Short-term storage,
      Long-term storage, Disposed/Consumed, Lost, Damaged) - built and
      wired into `ODR_EVENT_TYPE_OPTIONS`/`log_an_action.py`, 2026-09-07
- [x] **Build Physical/Morphological, Water-ness, Organic
      Characterization, and the full Alteration and Diagenesis
      breakdown in ODR.** All built 2026-09-08. Final state (pulled
      live, not just what was planned - a few fields ended up
      different from the original plan, noted below):
      - Physical/Morphological: Homogeneity (Short Text), **Other
        properties** (Short Text - renamed from "Ductile, friable,
        etc.", same content folded into the description), Crystallinity
        (Short Text), Size (Decimal, cm), Integrity (Single Select:
        Whole/Part/Extract), Mass (Decimal, **grams**, not mg - so it
        no longer matches the "Mass: ___ mg" blank already printed on
        the physical label; not fixed, just noted)
      - Water-ness: Water Activity (Decimal, 0-1 scale), Dominant Bond
        Type (Short Text), Hydration State (Short Text)
      - Organic Characterization: Carbon Counts/Aliphatic/Aromatic
        (Short Text), Kerogen Type (Short Text), Moieties Present
        (Paragraph Text)
      - Alteration and Diagenesis: Age (Decimal, years), Radiation
        (Short Text), Temperature at Formation (Decimal, °C -
        **field name has a typo, missing a space: "...Diagenesis
        -Temperature..."**, not fixed), Temperature Experienced/Tmax
        (Decimal, °C), **Pressure (Short Text, not Decimal as
        planned)**, Mechanical (**Multiple Select**: Aeolian,
        Compaction, Fluvial, Freeze-thaw, Glacial, Impact, Other),
        Microbial (Multiple Select: Biofilm formation, Biomineralization,
        Microbial weathering, Other), Chemical (Multiple Select: Acid
        dissolution, Aqueous, Carbonation, Other, Oxidation)
      - The old top-level "Alteration and Diagenesis" Yes/No/Maybe
        field is gone from the live template - looks like it was
        retired in favor of the detailed breakdown above, resolving
        the earlier open question.
      - Also changed along the way: `Point of Contact (Name)` renamed
        to `Point of Contact (Full Name)` (safe, field_uuid unchanged,
        no code impact); `Rock - Amorphous` and `Rock - Organic` both
        gained a third option, "Partially"; `Origin` reverted from the
        simplified 2-option version back to 3 options (Lab-produced,
        Terrestrial sourced or found, Planetary); `Subsample ID`'s
        placeholder description got filled in properly.
      - All ODR-only, not asked in Streamlit - see `setup.md` "What's
        in Streamlit vs. ODR-only."
- [x] Streamlit user guide for the team (`USER_GUIDE.md`, written for
      non-technical users, 2026-08-02)
- [ ] ODR user guide for the team (data subgroup only - not everyone
      gets an ODR account, decided 2026-08-02, see below)
- [ ] Record a video walking through the full sample registration process
- [ ] Ask Nate for a meeting to walk through the whole project -
      priority items to raise: the publish-permission grant needed
      below, whether there's a real "change record's public status"
      or search API he knows isn't documented elsewhere, and the
      ODR-side bug below (worked around in the app, but ODR should
      still fix the actual endpoint)
- [ ] **Report ODR-side bug to Nate:** `POST /record/{uuid}/{field}/value`
      and `PUT /record/{uuid}/{field}/{option}/selected` both 500 with
      `"Service odr.permissions_management_service not found"` -
      confirmed live 2026-08-18, found by a beta tester. Worked around
      in the app (registration.py now batches everything through
      `POST /dataset/record` instead, which still works), but ODR's
      own endpoints are still broken and should get fixed properly.
      Given the error mentions a permissions service, possibly related
      to recent permissions/publishing changes on ODR's end.
- [ ] Ask Nate for WordPress site permissions
- [ ] Set up the WordPress site for the dataset
- [ ] Add a permissions layer on the WordPress site
- [ ] Rotate the shared app password monthly (manual - see
      `ACCESS_CONTROL_HISTORY.md`; update it in `.streamlit/secrets.toml`
      locally, push to Secret Manager with `gcloud secrets versions add`,
      then redeploy)
- [ ] **Make new ODR records public automatically at creation.** Decided
      2026-08-02: not everyone gets an ODR account (only the data
      subgroup will), so the real fix for "ODR link asks me to log in"
      is auto-publishing, not distributing accounts broadly. Found the
      real API endpoint (`POST /dataset/record/public`, confirmed
      against ODR's own docs and tested live) but the app's ODR
      credential (`odr-scobi-sunanda@odr.io`) currently gets
      `403 Insufficient permissions` calling it - that account can
      create/edit records but not publish them. Needs Nate (or
      whoever manages dataset permissions) to grant that account
      publish rights. Once it works (confirmed by getting something
      other than 403), wire a call to this endpoint into
      `odr_create_record()`'s caller in `registration.py` right after
      a record is created, so it happens automatically on every new
      registration.
- [ ] **Investigate querying ODR directly instead of the Google Sheets
      lookup layer.** Right now "Log an action" and subsample ID
      generation both depend on the register Google Sheet as an index
      (see "Register CSV fields" in `setup.md` for why). There's an
      undocumented-but-real search endpoint found in the archived
      `ODR_API_Client_New.ipynb` notebook
      (`POST /dataset/{dataset_uuid}/search/{limit}/{offset}.json`,
      payload `{"fields": [{"field_uuid": ..., "value": ...}]}`) that
      was never actually tested live - held off testing it while
      other things took priority. If it works, this could let the app
      look up a sample by ID directly in ODR instead of depending on
      the Sheet, removing that whole layer of indirection. Test it
      live before trusting it; the notebook's own version of this had
      bugs and no confirmed real response was ever captured.
