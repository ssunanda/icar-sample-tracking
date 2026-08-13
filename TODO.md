# Next steps

- [ ] Discuss with the data subgroup which fields belong in ODR (Physical/
      Morphological, Water-ness, Organic Characterization option lists
      are still undefined, see `setup.md` and the taxonomy mindmap)
- [x] Streamlit user guide for the team (`USER_GUIDE.md`, written for
      non-technical users, 2026-08-02)
- [ ] ODR user guide for the team (data subgroup only - not everyone
      gets an ODR account, decided 2026-08-02, see below)
- [ ] Record a video walking through the full sample registration process
- [ ] Ask Nate for a meeting to walk through the whole project -
      priority items to raise: the publish-permission grant needed
      below, and whether there's a real "change record's public
      status" or search API he knows isn't documented elsewhere
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
