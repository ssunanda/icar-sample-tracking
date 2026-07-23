# Setup

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Needs a `.streamlit/secrets.toml` with a Google service account (for the
register/summary Sheets), ODR credentials, and an `[auth]` section for
the app's password gate:

```toml
[auth]
password = "..."   # whatever the current shared team password is
```

See below for the other two sections.

---

## Google service account (one time)

Lets the app read/write the register + summary Google Sheets without
anyone signing in.

1. console.cloud.google.com → new project (or reuse one)
2. APIs & Services → Enable APIs → search "Google Drive API" → Enable
3. APIs & Services → Credentials → Create Credentials → Service Account
4. Click into it → Keys → Add Key → JSON → download it
5. Open that JSON, copy `client_email`, then go share both Google
   Sheets (register + summary) with that email, Editor access
6. Copy the JSON's fields into `.streamlit/secrets.toml` under
   `[gcp_service_account]` — `private_key` needs the full
   `-----BEGIN RSA PRIVATE KEY-----` block, newlines and all

---

## ODR

`.streamlit/secrets.toml` needs:

```toml
[odr]
base_url = "https://www.odr.io/api/v4"   # must be www. - odr.io redirects and the API can't follow a redirected POST
username = "..."
password = "..."
dataset_uuid = "b7d32084573f17d66a6350ba4a2f"   # MMML Sample Repository
```

Field UUIDs for both the parent Sample record and the Sample Event
child are hardcoded in `odr_common.py` — no need to rediscover them by
hand. If the ODR template ever changes (new field, field gets
recreated), pull it fresh:

```bash
curl -s -X POST "$BASE_URL/token" -H "Content-Type: application/json" \
  -d '{"username":"...","password":"..."}'   # → JWT
curl -s "$BASE_URL/template/<dataset_uuid>" -H "Authorization: Bearer <token>"
```

and update the UUIDs in `odr_common.py` to match.

**Gotchas that'll bite you if the template gets edited again:**
- Fields must have their own unique `field_uuid` — cloning a field in
  ODR's Dataset Design UI sometimes copies the UUID instead of
  generating a new one, which makes two different fields silently
  overwrite each other. Delete + re-add rather than clone.
- "Short Text" fields cap out at 32 characters and 500 on write with a
  raw SQL error past that — use "Paragraph Text" instead for anything
  that isn't guaranteed short (descriptions, URLs, names).
- DateTime fields want a bare date (`2026-07-20`), not a timestamp.
- The `/value` endpoint 500s on DateTime fields specifically — use
  `odr_push_fields()` instead of `odr_set_field_value()` for those.
- Pushing a new Sample Event child replaces the *entire* child list if
  you don't include the existing ones — `odr_push_child_record()`
  already handles this (fetches + re-includes existing children), just
  don't bypass it.
- **Renaming a field in ODR keeps its `field_uuid`** — it doesn't
  create a new field. This bit us once: the original top-level "Notes"
  field got renamed to "Sources of Contamination," which silently
  redirected the app's Notes box into the wrong field until caught.
  Always add a genuinely new field for a new concept rather than
  repurposing an old one via rename, unless you're deliberately
  retiring the old meaning.

### What's in Streamlit vs. ODR-only

The registration form only asks for what's needed to create and locate
a sample record — deeper taxonomy is filled in directly in ODR later,
not through the app, so the form stays light. As of 2026-07-22:

**In Streamlit** (`registration.py`): Sample ID/Subsample ID
(generated), Sample Category, Sample Description, Source Link, Source
Institution, Point of Contact (Name/E-mail/Institution), Registration
Date (generated), Notes, plus Location/Event Type on the auto-created
Sample Event.

**ODR-only** (not asked at registration, fill in directly in ODR):
Organism Subcategory/Domain, Rock Subcategory/Amorphous/Organic, Blob
Macromolecular/Water Soluble, Ice Water/State, Origin, Alteration and
Diagenesis, Sources of Contamination, Bioticity. Some of these still
need their value sets defined by the data subgroup (see `TODO.md`).

---

## Deploy to Google Cloud Run

Access control is a **shared team password**, checked in `app.py`
before anything else loads. The app itself is otherwise public
(`--allow-unauthenticated`) — the password is what keeps random
passersby out, not Google identity.

**History, for context** (full troubleshooting trail in
`ACCESS_CONTROL_HISTORY.md` — read that before re-attempting IAP):
this went IAP → password → IAP → password again. Started with
password (Google-account coverage across ~20 people spanning
NASA/Carnegie/Howard/Purdue/Rutgers/ex situ bio was
unknown/inconsistent), switched to IAP once that coverage was
confirmed workable, then switched back to password on 2026-07-22 after
IAP proved unreliable in ways that resisted every diagnostic we tried:
IAM bindings, `run.invoker` on the IAP service agent, the org policy
below, and the OAuth consent screen's Internal/External setting all
checked out correctly, yet some correctly-granted external accounts
(confirmed via direct policy inspection) still got a hard "you don't
have access" from IAP with no useful detail in the logs we could
access. Real per-person attribution already happens at the data layer
(every registration/event captures the actual person's name/email), so
a shared password is a reasonable trade — it just works for everyone,
regardless of institution.

Run this in **Cloud Shell** (console.cloud.google.com → terminal icon,
top right) — `gcloud` is already installed and logged in as you there.

```bash
PROJECT_ID=icar-sample-tracking
REGION=us-central1
SERVICE=delimit-sample-registration

gcloud config set project "$PROJECT_ID"
```

**Billing** needs to be on for the project (Cloud Run/Build/Secret
Manager all require it). Console → Billing → link a card → link that
billing account to the project. Set a budget alert while you're there.
Actual cost for how this app gets used (internal tool, occasional,
~20 people): expect $0–2/month, well inside the free tiers.

**One-time setup:**

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
    secretmanager.googleapis.com

git clone https://github.com/ssunanda/icar-sample-tracking.git
cd icar-sample-tracking
# upload your local .streamlit/secrets.toml into Cloud Shell (⋮ menu → Upload —
# it's a hidden folder so on macOS you may need Cmd+Shift+. to see it in the picker)
mkdir -p .streamlit && mv ~/secrets.toml .streamlit/secrets.toml
# make sure it has an [auth] section with a `password` key - see "Run locally" above

gcloud secrets create delimit-secrets --data-file=.streamlit/secrets.toml
```

**Deploy:**

```bash
gcloud run deploy "$SERVICE" \
    --source . \
    --region "$REGION" \
    --allow-unauthenticated \
    --update-secrets=/app/.streamlit/secrets.toml=delimit-secrets:latest
```

Builds straight from source via Cloud Build (no local Docker needed —
the `Dockerfile` gets picked up automatically). Takes a few minutes
the first time. You'll get back a `*.run.app` URL.

**If `--allow-unauthenticated` fails with something like "not in
permitted organization"** — the GCP org (inherited from the Workspace
the project lives under) has a policy blocking public/`allUsers` IAM
bindings by default. Fix (needs org owner/policy-admin rights):

```bash
cat > /tmp/allow-all.yaml <<'EOF'
name: projects/icar-sample-tracking/policies/iam.allowedPolicyMemberDomains
spec:
  rules:
  - allowAll: true
EOF
gcloud org-policies set-policy /tmp/allow-all.yaml
```

Then re-run the deploy command above.

**Redeploying after a code change:**

```bash
gcloud run deploy "$SERVICE" --source . --region "$REGION"
```

(Secrets stick once set — only redo the secret step if you're rotating
a credential or changing the password.)

---

## Register CSV fields

Two plain `.csv` files in Drive back this app (not native Google
Sheets, so they open as a file preview/download, not the Sheets
editor — Drive file IDs are in `odr_common.py`):
- [Register CSV](https://drive.google.com/file/d/18gy4QKgyGafmTjG4505VCBHUfySvuIed/view) (`REGISTER_FILE_ID`) — one row per registration
- [Summary CSV](https://drive.google.com/file/d/1W7jeb4H0QnhAzh4UHCleqD-ir2jCw60J/view) (`SUMMARY_FILE_ID`) — pivot/count rollup, cosmetic only

Still needed in addition to ODR: the register sheet is how "Log an
action" resolves a typed sample ID to its ODR `record_uuid`, and how
subsample ID generation checks for existing/parent IDs. The summary
sheet is no longer wired up (it tracked subtype-level breakdowns that
Streamlit doesn't collect anymore — see "What's in Streamlit vs.
ODR-only" above) — safe to ignore or repurpose.

`registration.py` writes one row per registration to the register
sheet. Columns:

| Column | Notes |
|---|---|
| `sampleID` | this record's own ID for a top-level sample, or the parent's ID for a subsample (they share this value on purpose — search by it to find a sample + all its subsamples together) |
| `parent_sample_id` | blank unless this is a subsample |
| `record_uuid` | the ODR parent record's UUID |
| `description` | required, ≤10 words |
| `registrant_name`, `registrant_email` | required (labeled "Point of contact" in the UI) |
| `icar_institution` | required, dropdown - `ICAR_INSTITUTIONS` in `odr_common.py` |
| `source_institution` | optional |
| `existing_sample_url` | optional |
| `current_location` | required |
| `action` | always "Register new sample" for rows written by `registration.py`; historical rows may have other values from before "Log an action" existed as a separate page |
| `notes` | optional |
| `sample_type` | Organism / Rock / Blob / Ice / Mixed / Extract |
| `registration_date` | auto |
| `URL` | the real ODR record URL |

---

## File structure

```
icar-sample-tracking/
├── app.py                  # entry point - page config + nav router, that's it
├── registration.py         # "Register a sample" page - the actual app
├── pages/1_Log_an_action.py  # "Log an action" page
├── odr_common.py           # shared ODR/Sheets helpers, field UUIDs, brand colors
├── static/fonts/           # bundled IBM Plex Sans + Space Mono
├── brand/                  # DELIMIT logo SVGs + design reference
├── Dockerfile, .dockerignore
├── requirements.txt
├── archive/                # old reference code/CSVs, not used by the app
└── .streamlit/
    ├── config.toml         # DELIMIT theme (local dev only - cloud deploy sets theme via CLI flags, see Dockerfile)
    └── secrets.toml        # never commit this
```
