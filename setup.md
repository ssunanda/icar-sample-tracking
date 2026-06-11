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

## Deploy to Streamlit Cloud

1. Push this folder to a GitHub repo (the secrets.toml is gitignored — safe)
2. Go to https://share.streamlit.io → New app
3. Connect your GitHub repo, select `app.py`
4. Before deploying: Settings → Secrets → paste the full contents
   of your secrets.toml
5. Deploy — you'll get a public URL to share with the team

---

## File structure

```
icar_app/
├── app.py              # the whole app
├── requirements.txt    # dependencies
├── .gitignore
└── .streamlit/
    └── secrets.toml    # credentials (never commit this)
```
