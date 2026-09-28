# Setup

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

If you're changing code (not just running the app), install the dev
tools too and see "Tests and linting" below:

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

**All dependency versions are pinned** in `requirements.txt` (and
`cryptography` is pinned explicitly even though it's only a
transitive dependency of `google-auth`, not imported directly
anywhere) - a floating `cryptography` version silently changed how it
parses the `gcp_service_account.private_key` PEM and broke local
Sheets access on 2026-09-26 with no code change to explain why (see
`TODO.md`). If you bump a version on purpose, re-run the full manual
test pass in `TESTING.md` before trusting it.

**Always run `app.py`, never `registration.py` or `log_an_action.py`
directly** - `app.py` is the only file with the password gate in it.
Running either of the other two files directly skips login entirely.

Needs a `.streamlit/secrets.toml` with a Google service account (for the
register/summary Sheets), ODR credentials, and an `[auth]` section for
the app's password gate:

```toml
[auth]
password = "..."   # whatever the current shared team password is
```

See below for the other two sections.

**If you just cloned this repo and hit `StreamlitSecretNotFoundError:
No secrets found`** - this is expected, not a bug. `.streamlit/secrets.toml`
holds real credentials, so it's gitignored and never comes through
`git clone`/`git pull` at all; every fresh clone needs its own copy
created locally. Fix:

1. Create the file at `.streamlit/secrets.toml` inside your clone (make
   the `.streamlit` folder if it doesn't exist yet).
2. Ask **sunanda@exsitu.bio** for the actual contents (the real
   password, Google service account key, and ODR credentials) and
   paste them in - don't try to generate your own Google service
   account or ODR credentials from scratch, this app is meant to share
   one set. Ask her to send it through a secure channel, not
   plaintext email/Slack.
3. It needs all three sections - `[auth]`, `[gcp_service_account]`,
   and `[odr]` - matching the format shown in this doc. Missing any
   one of them will cause errors in the parts of the app that need it
   (e.g. missing `[auth]` breaks login, missing `[odr]` breaks
   registering samples).

---

## Tests and linting

Automated tests (`pytest`, in `tests/`) cover the pure-logic pieces -
sample/subsample ID generation, ODR field lookups, event-field
parsing. They don't touch the network (no ODR or Google Sheets calls)
and don't replace `TESTING.md`'s manual pass, which is still the only
thing that actually exercises the UI, the real ODR/Sheets integration,
and the label image. Run them:

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

Linting (`ruff`, config in `pyproject.toml`) catches real bugs
(unused imports, undefined names) and import ordering. It's
deliberately *not* configured to flag broad `except Exception`
blocks or the local `lambda` helper in `make_label()` - both are
intentional patterns here, not bugs, and a default-strict linter
config would just generate noise against them. Run it:

```bash
ruff check .          # report only
ruff check . --fix    # auto-fix what's safe to (import order, etc.)
```

Neither of these runs automatically yet (no CI) - remember to run
both before committing.

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
   `[gcp_service_account]`. `private_key` needs the full
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
child are hardcoded in `odr_common.py`, no need to rediscover them by
hand. If the ODR template ever changes (new field, field gets
recreated), pull it fresh:

```bash
curl -s -X POST "$BASE_URL/token" -H "Content-Type: application/json" \
  -d '{"username":"...","password":"..."}'   # → JWT
curl -s "$BASE_URL/template/<dataset_uuid>" -H "Authorization: Bearer <token>"
```

and update the UUIDs in `odr_common.py` to match.

**Gotchas that'll bite you if the template gets edited again:**
- Fields must have their own unique `field_uuid`. Cloning a field in
  ODR's Dataset Design UI sometimes copies the UUID instead of
  generating a new one, which makes two different fields silently
  overwrite each other. Delete + re-add rather than clone.
- "Short Text" fields cap out at 32 characters and 500 on write with a
  raw SQL error past that. Use "Paragraph Text" instead for anything
  that isn't guaranteed short (descriptions, URLs, names).
- DateTime fields want a bare date (`2026-07-20`), not a timestamp.
- The `/value` endpoint 500s on DateTime fields specifically. Use
  `odr_push_fields()` instead of `odr_set_field_value()` for those.
- Pushing a new Sample Event child replaces the *entire* child list if
  you don't include the existing ones: `odr_push_child_record()`
  already handles this (fetches + re-includes existing children), just
  don't bypass it.
- **Renaming a field in ODR keeps its `field_uuid`**, it doesn't
  create a new field. This bit us once: the original top-level "Notes"
  field got renamed to "Sources of Contamination," which silently
  redirected the app's Notes box into the wrong field until caught.
  Always add a genuinely new field for a new concept rather than
  repurposing an old one via rename, unless you're deliberately
  retiring the old meaning.

### What's in Streamlit vs. ODR-only

The registration form only asks for what's needed to create and locate
a sample record. Deeper taxonomy is filled in directly in ODR later,
not through the app, so the form stays light. As of 2026-08-18:

**In Streamlit** (`registration.py`): Sample ID/Subsample ID
(generated), Sample Category, Mixed/Extract composition (which of
Organism/Rock/Blob/Ice make it up - Sheet-only, no ODR field for this),
Sample Description, Source Link, Source Institution, Point of Contact
(Name/E-mail/Institution), Registration Date (generated), Notes, plus
Location/Event Type on the auto-created Sample Event.

**ODR-only** (not asked at registration, fill in directly in ODR):
Organism Subcategory/Domain, Rock Subcategory/Amorphous/Organic, Blob
Macromolecular/Water Soluble, Ice Water/State, Origin, Sources of
Contamination, Bioticity, and the full Alteration and Diagenesis
breakdown (Age/Radiation/Temperature at formation/Temperature
experienced/Pressure/Mechanical/Microbial/Chemical - finalized with
the data subgroup 2026-08-18, see `TODO.md` for the exact field list
and options to build). Physical/Morphological, Water-ness, and Organic
Characterization option lists are still undefined (see `TODO.md`).

---

## Deploy to Google Cloud Run

Access control is a **shared team password**, checked in `app.py`
before anything else loads. The app itself is otherwise public
(`--allow-unauthenticated`); the password is what keeps random
passersby out, not Google identity.

**History, for context** (read this before re-attempting IAP):
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
a shared password is a reasonable trade. It just works for everyone,
regardless of institution.

Run this in **Cloud Shell** (console.cloud.google.com → terminal icon,
top right); `gcloud` is already installed and logged in as you there.

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
~20 people): expect $0-2/month, well inside the free tiers.

**One-time setup:**

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
    secretmanager.googleapis.com

git clone https://github.com/ssunanda/icar-sample-tracking.git
cd icar-sample-tracking
# upload your local .streamlit/secrets.toml into Cloud Shell (⋮ menu → Upload;
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

Builds straight from source via Cloud Build (no local Docker needed;
the `Dockerfile` gets picked up automatically). Takes a few minutes
the first time. You'll get back a `*.run.app` URL.

**If `--allow-unauthenticated` fails with something like "not in
permitted organization"**: the GCP org (inherited from the Workspace
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
cd ~/icar-sample-tracking && git pull
gcloud run deploy "$SERVICE" --source . --region "$REGION"
```

**Always `cd ~/icar-sample-tracking` first.** Cloud Shell's home
directory (`~`) has its own old, separate checkout of this code from
before the repo was cloned into `~/icar-sample-tracking` (discovered
2026-09-08: `git pull` from `~` failed with "not a git repository,"
and a deploy run from `~` silently built that stale copy instead of
erroring, so it's easy to not notice you deployed the wrong code).
`git status`/`git log` on the real repo will show you're in the right
place if unsure.

(Secrets stick once set. Only redo the secret step if you're rotating
a credential or changing the password.)

**Tag each deploy** (added 2026-09-27, so a bug report can be pinned
to exactly what was live when it happened - pairs with `CHANGELOG.md`,
which you should update in the same commit):

```bash
git tag v2026-09-27   # date of the deploy, not the tag command
git push origin v2026-09-27
```

**Rolling back a bad deploy:** Cloud Run keeps every previous
revision and can shift traffic back to one instantly, no rebuild
needed - this is the fast fix if a deploy goes bad, faster than
`git revert` + redeploy.

```bash
# List revisions, newest first, to find the last known-good one
gcloud run revisions list --service="$SERVICE" --region="$REGION"

# Send 100% of traffic back to it
gcloud run services update-traffic "$SERVICE" --region="$REGION" \
    --to-revisions=REVISION_NAME=100
```

NOTE: this is documented from how Cloud Run's traffic-splitting
generally works, not verified against this specific service - `gcloud`
isn't available outside Cloud Shell, so it hasn't been tested live
here. Worth doing a real dry run once (roll back to the current
revision, confirm nothing breaks) before you're relying on it during
an actual incident.

**Changing the password** (do this twice a year, see GitHub Issues):

```bash
cd ~/icar-sample-tracking
sed -i 's|password = "OLD_PASSWORD"|password = "NEW_PASSWORD"|' .streamlit/secrets.toml
grep -A1 "\[auth\]" .streamlit/secrets.toml   # confirm it actually changed

gcloud secrets versions add delimit-secrets --data-file=.streamlit/secrets.toml
gcloud run deploy "$SERVICE" --region "$REGION" \
    --update-secrets=/app/.streamlit/secrets.toml=delimit-secrets:latest
```

**Backing up the register sheet:** `python3 scripts/backup_register.py`
(needs `.streamlit/secrets.toml` locally, same as running the app).
No delete button anywhere in the app on purpose, and Sheets' version
history isn't a real backup strategy - this snapshots the register
into the otherwise-unused summary file. It's a single **rolling**
backup (overwritten each run, renamed to show the date), not dated
history - a real service account can't create new Drive files outside
a Shared Drive (confirmed live 2026-09-27: `files.create`/`files.copy`
both 403 "Service Accounts do not have storage quota"). If dated
history ever matters, see the Shared Drive option noted in
`TODO.md`. Not on a schedule yet - run it yourself periodically.

Then update your own local `.streamlit/secrets.toml` to match (so
local dev keeps working), and let the team know the new password
however you'd normally share it (not in this repo, not in Slack/email
in plaintext ideally).

---

## Register CSV fields

Two plain `.csv` files in Drive back this app (not native Google
Sheets, so they open as a file preview/download, not the Sheets
editor). Drive file IDs are in `odr_common.py`:
- [Register CSV](https://drive.google.com/file/d/18gy4QKgyGafmTjG4505VCBHUfySvuIed/view) (`REGISTER_FILE_ID`): one row per registration
- [Summary CSV](https://drive.google.com/file/d/1W7jeb4H0QnhAzh4UHCleqD-ir2jCw60J/view) (`SUMMARY_FILE_ID`): pivot/count rollup, cosmetic only

**As of 2026-09-27, the register sheet is a write-only backup log, not
load-bearing.** Before that, it was the lookup layer "Log an action"
used to resolve a typed sample ID to its ODR `record_uuid`, and how
subsample ID generation checked for existing/parent IDs - both now
query ODR directly instead (`odr_search_all_records()` in
`odr_common.py`). `registration.py` still writes a new row here on
every registration, purely as a human-browsable backup; nothing reads
from it anymore. The summary sheet is repurposed as the rolling
backup destination (see `scripts/backup_register.py`) - it's no longer used
for its original subtype-breakdown purpose (Streamlit doesn't collect
that data anymore, see "What's in Streamlit vs. ODR-only" above).

**Keeping the Sheet in sync with ODR:** since the app only ever adds
rows, drift only happens if someone deletes or edits a record
directly in ODR without also touching the Sheet. This is
event-triggered, not something to run on a schedule - whenever you
delete/edit something in ODR yourself, immediately run
`python3 scripts/remove_register_row.py <sampleID>` to remove the matching
Sheet row (it shows you the row and asks for confirmation before
removing it). Decided 2026-09-27: no periodic/scheduled sync job,
since the Sheet is just a backup log now and the drift this guards
against is low-stakes.

`registration.py` writes one row per registration to the register
sheet. Columns:

| Column | Notes |
|---|---|
| `sampleID` | this record's own ID - a top-level sample's own coolname ID, or a subsample's own suffixed ID (e.g. `cool-buffalo-water-A`). This is what `log_an_action.py` searches on. |
| `parent_sample_id` | blank unless this is a subsample, in which case it's the parent's bare ID (e.g. `cool-buffalo-water`) - use this to find a sample's subsamples together |
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
├── app.py                  # entry point - ALWAYS run this one (`streamlit run app.py`),
│                           # never registration.py directly - it's the only file
│                           # with the password gate, running any other file
│                           # skips login entirely
├── registration.py         # "Register a sample" page, the bulk of the form logic
├── log_an_action.py        # "Log an action" page - deliberately NOT in a pages/
│                           # folder, since Streamlit auto-exposes anything in
│                           # a folder named pages/ as its own URL, bypassing
│                           # app.py's password gate entirely
├── odr_common.py           # shared ODR/Sheets helpers, field UUIDs, brand colors
├── scripts/                # one-off maintenance tools, not part of the app itself -
│                           # run as `python3 scripts/<name>.py` from the repo root
│   ├── backup_register.py
│   ├── remove_register_row.py
│   └── remove_odr_events.py
├── tests/                  # pytest suite - pure logic only, no network calls
├── static/fonts/           # bundled IBM Plex Sans + Space Mono
├── brand/                  # DELIMIT logo SVGs + design reference
├── Dockerfile, .dockerignore
├── requirements.txt
├── archive/                # old reference code/CSVs, not used by the app;
│                           # local-only (gitignored), not in the shared repo
└── .streamlit/
    ├── config.toml         # DELIMIT theme (local dev only - cloud deploy sets theme via CLI flags, see Dockerfile)
    └── secrets.toml        # never commit this
```
