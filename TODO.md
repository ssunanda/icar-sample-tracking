# Next steps

- [ ] Discuss with the data subgroup which fields belong in ODR (Physical/
      Morphological, Water-ness, Organic Characterization option lists
      are still undefined, see `setup.md` and the taxonomy mindmap)
- [ ] Streamlit user guide for the team
- [ ] ODR user guide for the team
- [ ] Record a video walking through the full sample registration process
- [ ] Ask Nate for a meeting to walk through the whole project
- [ ] Ask Nate for WordPress site permissions
- [ ] Set up the WordPress site for the dataset
- [ ] Add a permissions layer on the WordPress site
- [ ] Rotate the shared app password monthly (manual - see
      `ACCESS_CONTROL_HISTORY.md`; update it in `.streamlit/secrets.toml`
      locally, push to Secret Manager with `gcloud secrets versions add`,
      then redeploy)
- [ ] Get the team real ODR credentials/accounts. Right now the ODR
      record link generated after registering (e.g. from the QR code)
      redirects to an ODR login page for anyone without ODR access -
      confirmed with Hans, everything up through registration works,
      only the ODR link itself needs a real login. The link format we
      generate (`#/view/<id>`) may also not be the correct public URL
      even for the dataset's own public-facing page - worth
      re-investigating once accounts exist to test with, but getting
      real accounts is the actual fix either way.
