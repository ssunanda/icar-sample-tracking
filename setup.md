# ICAR Sample Registration — Setup

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Service account setup (one time)

This is what lets the app write to Google Drive without asking users to sign in.

**1. Create a Google Cloud project**
- Go to https://console.cloud.google.com
- New project → give it a name (e.g. "ICAR Sample Registration")

**2. Enable the Drive API**
- In your project: APIs & Services → Enable APIs
- Search for "Google Drive API" → Enable

**3. Create a service account**
- APIs & Services → Credentials → Create Credentials → Service Account
- Give it a name (e.g. "icar-sample-app")
- Skip the optional steps, click Done

**4. Download the credentials JSON**
- Click your new service account → Keys tab → Add Key → JSON
- Save the downloaded file somewhere safe

**5. Share your Drive files with the service account**
- Open the credentials JSON, copy the `client_email` value
  (looks like: icar-sample-app@your-project.iam.gserviceaccount.com)
- Go to each of your two CSV files in Google Drive
- Share → paste the service account email → Editor access

**6. Fill in secrets.toml**
- Open `.streamlit/secrets.toml`
- Copy the values from your downloaded JSON into the matching fields
- The `private_key` value should include the full
  `-----BEGIN RSA PRIVATE KEY-----` block

---

## ODR setup (in progress, not yet wired into the app)

Samples registered here are meant to also show up in [ODR](https://odr.io)
(the "MMML Sample Repository" project). That push is not implemented in
`app.py` yet - see `archive/ODR_Interface_code/` for reference client code from a
different project that uses the same API, and the status below.

**Secrets format** - add this block to `.streamlit/secrets.toml`:
```toml
[odr]
base_url = "https://www.odr.io/api/v4"   # must be www. - odr.io redirects and most clients (incl. ours) can't follow a redirected POST
username = "..."
password = "..."
dataset_uuid = "..."                     # the ICAR/MMML dataset UUID - see status below
```

**Status as of this handoff:**
- Auth flow (`POST /token` with `username`/`password` → bearer JWT) is
  now **confirmed working with the real ICAR/MMML credential**
  (`odr-scobi-sunanda@odr.io`) - verified 2026-07-16 with a direct
  `curl` against `https://www.odr.io/api/v4/token` (HTTP 200, valid JWT
  returned). The old NCSU credential is kept in secrets.toml as
  `[odr-old-test]` for reference only.
- `dataset_uuid` is **confirmed correct**: `b7d32084573f17d66a6350ba4a2f`,
  taken from the address bar of the dataset's own admin page
  (`https://www.odr.io/b7d32084573f17d66a6350ba4a2f#/admin/type/landing/947`).
  Confirmed 2026-07-16 by hitting `GET /api/v4/template/<uuid>` and
  `POST /api/v4/dataset/<uuid>/search/<limit>/<offset>.json` - both
  return `403 Insufficient permissions` (not 404), meaning the API
  recognizes the dataset, it's just that this account isn't yet granted
  access to it.
  (Note: `ODR_API_Client.py`'s `get_dataset(uuid)` hits
  `GET /dataset/<uuid>` with query params, which 404s - that route
  shape is wrong/stale. The correct route, per
  `archive/ODR_Interface_code/ODR_API_Client_New.ipynb` (a collaborator's newer
  client, uploaded 2026-07-16), is path-based:
  `GET /dataset/<uuid>/<limit>/<offset>`.)
- **Permissions confirmed fixed** (2026-07-16, after asking the admin):
  `GET /api/v4/template/<uuid>` and `GET /api/v4/dataset/<uuid>/10/0`
  both now return real data - `"name":"MMML Sample Repository"`, 2
  existing records. Auth, dataset UUID, and account access are all
  working end to end.
- **New blocker found while pulling the template: duplicate field
  UUIDs.** `GET /template/<uuid>` lists 17 fields, but 6 of them share
  `field_uuid`s with other, different fields:
  - `Sample Description`, `Source`, `Source Link` → all
    `09080b4aa6f0d5cfe2a47f0a4929`
  - `Point of Contact (Name)`, `(E-mail)`, `(Institution)`,
    `Registration Date` → all `ea314aa9a85c88cfbb44ba7dd18b`

  Each has a distinct `internal_id`, so they're genuinely separate
  fields in the template, just set up with copy-pasted `field_uuid`s.
  Since `set_field_value` (and the API generally) addresses fields by
  `field_uuid`, this is ambiguous as-is - writing to "Source Link"
  would currently be indistinguishable from writing to "Source" or
  "Sample Description". This needs to be fixed on the ODR side (the
  dataset is explicitly labeled "Test sample repository for the MMML
  ICAR", so likely just needs the template redone properly) before the
  field-mapping work below is safe to do.
- Once that's fixed, the integration is: create a record in the dataset,
  set its fields to match the register row, push it.
  `archive/ODR_Interface_code/client/ODR_API_Client.py` has `create_record`,
  `set_field_value`, and `push_record` for this - it needs the ICAR
  field-name → ODR field UUID mapping worked out (discoverable via
  `get_dataset(dataset_uuid)` on an existing record, same as
  `discover_radio_options()` in `archive/ODR_Interface_code/upload/batch_upload_to_odr.py`).

---

## Deploy to Google Cloud Run

This deploys the app as a container on Cloud Run. Access control is a
**shared team password** baked into the app itself (`app.py`, checked
against `st.secrets["auth"]["password"]`) — not Google-account-based
IAP, which was tried first and dropped: the ~20 people who need access
span institutions (NASA, Carnegie, Howard, Purdue, Rutgers, ex situ
bio) with inconsistent Google account coverage, and IAP would have
locked some of them out. Real per-person attribution already happens
at the data layer (every registration/event captures the actual
person's name/email), so the login screen's only job is keeping the
URL from being wide open, which a shared password does fine for that.

Run everything below in **Cloud Shell** (console.cloud.google.com →
terminal icon, top right) — it has `gcloud` pre-installed and already
authenticated as you, so no local setup is needed. If you'd rather run
this from your own terminal, install the
[gcloud CLI](https://cloud.google.com/sdk/docs/install) first and run
`gcloud auth login`.

Fill in `PROJECT_ID` (your GCP project) and `REGION` (e.g.
`us-central1`) once at the top and reuse them throughout:

```bash
PROJECT_ID=your-project-id
REGION=us-central1
SERVICE=delimit-sample-registration

gcloud config set project "$PROJECT_ID"
```

### 0. Billing

Cloud Run/Build/Secret Manager all require billing enabled on the
project. If you haven't already: Console → Billing → link a payment
method to create a Billing Account, then link it to this project:

```bash
gcloud billing accounts list   # note the ACCOUNT_ID
gcloud billing projects link "$PROJECT_ID" --billing-account=ACCOUNT_ID
```

Realistic cost for this app's actual usage pattern (internal tool,
occasional use by ~20 people): likely $0–2/month, comfortably within
Cloud Run/Build/Secret Manager's free tiers. Worth setting a budget
alert anyway (Billing → Budgets & alerts) as a safety net.

### 1. Enable the required APIs (one-time)

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
    secretmanager.googleapis.com
```

### 2. Put secrets.toml into Secret Manager

Don't commit `secrets.toml` or bake it into the container image — store
it as a secret and mount it at deploy time instead. Your local
`secrets.toml` needs an `[auth]` section with the team password added
at the top (see `app.py` for how it's checked):

```toml
[auth]
password = "..."
```

Get the file into Cloud Shell (Cloud Shell's "⋮" menu → Upload - note
`.streamlit/` is a hidden folder, so macOS's file picker won't show it
unless you press Cmd+Shift+. to reveal hidden files, or copy the file
to a visible location first and upload that instead), then:

```bash
gcloud secrets create delimit-secrets --data-file=.streamlit/secrets.toml
```

(If the secret already exists and you're rotating a credential or the
password, use
`gcloud secrets versions add delimit-secrets --data-file=.streamlit/secrets.toml`
instead, then redeploy so Cloud Run picks up the new version.)

### 3. Deploy

This builds the container from source (via Cloud Build - no local
Docker needed, the `Dockerfile` in the repo root is used automatically)
and deploys it, publicly reachable but gated by the app's own password
screen:

```bash
gcloud run deploy "$SERVICE" \
    --source . \
    --region "$REGION" \
    --allow-unauthenticated \
    --update-secrets=/app/.streamlit/secrets.toml=delimit-secrets:latest
```

If `Setting IAM Policy...warning` shows up in the output (a real thing
that happened once), run the fallback command it suggests:

```bash
gcloud run services add-iam-policy-binding "$SERVICE" \
    --region="$REGION" --member=allUsers --role=roles/run.invoker
```

Cloud Build takes a few minutes the first time. You'll get back a
`*.run.app` URL - that's the app, share it (and the password,
separately) with the team.

**Two real deploy bugs found and fixed while setting this up, for
context if something looks similar in the future:**
- An earlier version mounted the secret volume straight into
  `.streamlit/secrets.toml` alongside a baked-in `config.toml` for the
  DELIMIT theme, and tried to copy the secret into a *different* path
  at container startup to avoid Cloud Run replacing the whole
  `.streamlit/` directory with the mounted volume. Both `cp` and `cat`
  failed for this specific copy on Cloud Run's sandboxed runtime with
  filesystem errors ("file was replaced while being copied", then
  "write error: Invalid argument") that never showed up in local
  testing. Fix: don't bake `config.toml` into the image at all - mount
  the secret directly at its natural path instead, and set the theme
  via `streamlit run`'s own `--theme.*` CLI flags in the `Dockerfile`'s
  `CMD` (an officially supported Streamlit config source). One real
  cost: the custom bundled fonts (IBM Plex Sans / Space Mono, via
  `[[theme.fontFaces]]`) aren't expressible as CLI flags, so the
  deployed web UI's font differs slightly from local dev - the printed
  label PNG is unaffected, since that loads the same font files
  directly via PIL regardless of Streamlit's theme system.
- A brand-new GCP project's default Compute service account lacked
  `storage.objectViewer` and `artifactregistry.writer` - both needed
  for `gcloud run deploy --source .`'s build pipeline to read the
  uploaded source and push the built image. If you see permission
  errors mentioning `*-compute@developer.gserviceaccount.com`, grant
  it those two roles at the project level and retry.

### Redeploying after a code change

```bash
gcloud run deploy "$SERVICE" --source . --region "$REGION"
```

(No need to repeat the secrets/IAM flags — those stick once set. Only
re-run step 2 + a redeploy if you're rotating a credential or the team
password in secrets.toml.)

---

## Register CSV fields

`app.py` writes one row per registration to the sheet at `REGISTER_FILE_ID`.
Columns:

| Column | Notes |
|---|---|
| `sampleID` | auto-generated 3-word coolname slug (e.g. `eager-bullmastiff-of-tact`); checked against existing IDs in the register for uniqueness |
| `description` | required, enforced ≤10 words |
| `registrant_name`, `registrant_email` | required |
| `icar_institution` | required, dropdown - see `ICAR_INSTITUTIONS` in `app.py` |
| `source_institution` | required, e.g. ATCC, Natural History Museum |
| `existing_sample_url` | optional - link to the sample's existing record (IGSN resolver, catalog page, etc.), if one already exists |
| `current_location` | required |
| `action` | required, dropdown (`ACTIONS` in `app.py`); if "Other" is picked, stores the free-text detail instead |
| `notes` | optional - hazards, protocol links, etc. |
| `sample_type` | required, one of `SAMPLE_TYPES` in `app.py`: Organism / Rock / Blob / Ice / Mixed / Extract |
| `subtype` | conditional on `sample_type` - Organism: Multicellular/Community/Microbe; Rock: Primitive/Igneous/Metaphoric/Sedimentary; blank for Blob/Ice/Mixed/Extract |
| `organic`, `amorphous` | Rock only, Yes/No |
| `aq_soluble`, `macromolecular` | Blob only, Yes/No |
| `water_ice`, `ice_state` | Ice only - Yes/No, and Solid/Liquid |
| `registration_date` | auto |
| `URL` | auto - `ODR_BASE + sampleID` |

The summary sheet (`SUMMARY_FILE_ID`) is a pivot: one row per `sample_type`,
counting how many of that type match each `(column, value)` pair listed in
`SUMMARY_COL_MAP` in `app.py`. Only columns that already exist in the actual
Google Sheet get filled in, so add a column there matching a `SUMMARY_COL_MAP`
key to start tracking it. `archive/test_summary.csv` shows the expected shape.

---

## File structure

```
icar-sample-tracking/
├── app.py                  # entry point - page config + st.navigation router only
├── registration.py         # "Register a sample" page (the real app logic)
├── pages/
│   └── 1_Log_an_action.py  # "Log an action" page
├── odr_common.py           # shared ODR/Sheets helpers + brand colors - used by both pages
├── static/fonts/           # bundled IBM Plex Sans + Space Mono .ttf files (OFL-licensed)
├── brand/                  # DELIMIT logo SVGs (light/dark) + design reference
├── requirements.txt        # Python dependencies
├── Dockerfile              # container build for Cloud Run deploy
├── .dockerignore
├── archive/                # reference-only material, not used by the app
│   ├── test_register.csv   #   local reference for the register CSV schema
│   ├── test_summary.csv    #   local reference for the summary CSV schema
│   └── ODR_Interface_code/ #   reference client code for the ODR push - see "ODR setup" above
├── .gitignore
└── .streamlit/
    ├── config.toml         # DELIMIT theme (committed - no secrets in here)
    └── secrets.toml        # credentials (never commit this)
```