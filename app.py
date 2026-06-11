"""
ICAR Sample Registration
------------------------
Streamlit runs this script top-to-bottom every time the user
interacts with anything. Keep that in mind when reading the flow:
1. Page config + imports
2. Google Drive connection
3. Form fields
4. What happens on submit
"""

import io
import base64
from datetime import date

import streamlit as st
import coolname
import qrcode
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload


# ── Page config ───────────────────────────────────────────────────
# This must be the first Streamlit call in the script.
st.set_page_config(
    page_title="ICAR Sample Registration",
    page_icon="🧪",
    layout="centered",
)


# ── Google Drive connection ───────────────────────────────────────
# st.secrets pulls from .streamlit/secrets.toml locally,
# or from the Streamlit Cloud secrets manager when deployed.
# See README.md for how to set this up.

REGISTER_FILE_ID = "1kNwcy5BRkRMim8Tx6duoIAw9y8qUYvt4"
SUMMARY_FILE_ID  = "1iZX2PlplGfvS5rFu16bfQPNT5RlodvXi"
ODR_BASE         = "https://odr.io/ICAR/samples/"

SUMMARY_COL_MAP = {
    "Biotic Yes":       ("bioticity",  "Yes"),
    "Biotic No":        ("bioticity",  "No"),
    "Extant Yes":       ("extancy",    "Yes"),
    "Extant No":        ("extancy",    "No"),
    "Domain Bacteria":  ("domain",     "Bacteria"),
    "Domain Archaea":   ("domain",     "Archaea"),
    "Domain Eukarya":   ("domain",     "Eukarya"),
    "Autotrophic Yes":  ("autotrophy", "Yes"),
    "Autotrophic No":   ("autotrophy", "No"),
    "Altered Yes":      ("alteration", "Yes"),
    "Altered No":       ("alteration", "No"),
    "Origin Earth":     ("origin",     "Earth"),
    "Origin non-Earth": ("origin",     "non-Earth"),
}


@st.cache_resource
def get_drive_service():
    """
    Build and cache the Drive API client.
    @st.cache_resource means this only runs once per session,
    not on every rerun.
    """
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=creds)


def read_csv(file_id):
    service = get_drive_service()
    req = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    dl = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = dl.next_chunk()
    buf.seek(0)
    return pd.read_csv(buf, encoding="utf-8-sig")


def write_csv(file_id, df):
    service = get_drive_service()
    buf = io.BytesIO(df.to_csv(index=False).encode("utf-8-sig"))
    media = MediaIoBaseUpload(buf, mimetype="text/csv", resumable=False)
    service.files().update(fileId=file_id, media_body=media).execute()


def update_summary(register_df):
    summary_df = read_csv(SUMMARY_FILE_ID)
    row_col = summary_df.columns[0]
    for i, row in summary_df.iterrows():
        cat = row[row_col]
        cat_rows = register_df[register_df["category"] == cat]
        for col_header, (reg_col, val) in SUMMARY_COL_MAP.items():
            if col_header in summary_df.columns:
                count = int((cat_rows[reg_col] == val).sum())
                summary_df.at[i, col_header] = count if count > 0 else ""
    write_csv(SUMMARY_FILE_ID, summary_df)


# ── Label generator ───────────────────────────────────────────────

def make_label(sample_id, category, odr_url):
    W, H, QR_SZ = 500, 160, 120
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([1, 1, W-2, H-2], outline="black", width=2)
    draw.rectangle([1, 1, W-2, 26], fill="black")
    try:
        fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
        fm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 16)
        fs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
    except:
        fb = fm = fs = ImageFont.load_default()
    draw.text((12, 6),  "ICAR SAMPLE", font=fb, fill="white")
    draw.text((12, 34), "SAMPLE ID",   font=fs, fill="#888")
    draw.text((12, 50), sample_id,     font=fm, fill="black")
    draw.text((12, 80), category,      font=fs, fill="#555")
    draw.text((12, 92), str(date.today()), font=fs, fill="#aaa")
    draw.rectangle([1, H-28, W-2, H-2], fill="#f5f5f5")
    draw.text((12, H-21), "Status: _______________    Mass: _________ mg", font=fs, fill="#444")
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4, border=1)
    qr.add_data(odr_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB").resize((QR_SZ, QR_SZ))
    img.paste(qr_img, (W - QR_SZ - 12, 26))
    draw.text((W - QR_SZ - 12 + 16, 26 + QR_SZ + 2), "ODR record", font=fs, fill="#888")
    return img


# ── UI ────────────────────────────────────────────────────────────

st.title("🧪 ICAR Sample Registration")
st.caption("Fill in the form below and click Register. You'll get a unique sample ID and a printable label.")

# st.form() groups all the widgets below into a single submission.
# Without it, Streamlit reruns the script on every widget change,
# which would generate a new sample ID each time.
with st.form("registration_form"):

    st.subheader("Who are you?")
    name  = st.text_input("Your name *")
    email = st.text_input("Your email *")
    inst  = st.selectbox("ICAR institution *", [
        "NASA Ames", "Carnegie Science", "JHU", "Howard",
        "Purdue", "Rutgers", "ex situ bio", "Other"
    ])

    st.divider()
    st.subheader("About the sample")
    org  = st.text_input("Sample origin organization *",
                         help="e.g. Natural History Museum, ATCC, Hazen Lab")
    desc = st.text_area("Brief description *",
                        help="e.g. Bacteria on an agar slant from deep subsurface drill core")
    cat  = st.selectbox("Sample category *", [
        "Organism (Multicellular)",
        "Organism (Consortium)",
        "Organism (Microbe)",
        "Organism (Biomolecular)",
        "Rock (Aggregate)",
        "Rock (Grain)",
        "Rock (Mineral)",
        "Rock (Mineraloid)",
        "Fossil (sensu stricto = rock?)",
        "Dirt/Regolith (loose material, incl. fr. asteroids)",
        "Macromolecular Organic Matter",
        "Ice (incl. snow)",
        "Brine (incl. water)",
        "Mixed (Rock/Blob, Dirt/Brine, Organism/Rock, etc.)",
    ])

    st.divider()
    st.subheader("Classification")
    st.caption("Select Unknown / N/A if unsure — you can update later.")

    col1, col2 = st.columns(2)
    with col1:
        bioticity  = st.selectbox("Biotic?",      ["Unknown / N/A", "Yes", "No"])
        extancy    = st.selectbox("Extant?",       ["Unknown / N/A", "Yes", "No"])
        domain     = st.selectbox("Domain",        ["Unknown / N/A", "Bacteria", "Archaea", "Eukarya"])
    with col2:
        autotrophy = st.selectbox("Autotrophic?",  ["Unknown / N/A", "Yes", "No"])
        alteration = st.selectbox("Altered?",      ["Unknown / N/A", "Yes", "No"])
        origin     = st.selectbox("Origin",        ["Unknown / N/A", "Earth", "non-Earth"])

    st.divider()
    submitted = st.form_submit_button("Register Sample", type="primary", use_container_width=True)


# ── On submit ─────────────────────────────────────────────────────
# Everything below only runs when the button is clicked.

def clean(val):
    return "" if val.startswith("Unknown") else val

if submitted:
    # Validate required fields
    missing = [f for f, v in [("name", name), ("email", email),
                               ("origin organization", org), ("description", desc)]
               if not v.strip()]
    if missing:
        st.error(f"Please fill in: {', '.join(missing)}")
        st.stop()

    with st.spinner("Registering sample..."):
        sample_id = "-".join(coolname.generate(3))
        odr_url   = ODR_BASE + sample_id

        new_row = {
            "sampleID":          sample_id,
            "name":              name.strip(),
            "email":             email.strip(),
            "icar_institution":  inst,
            "origin_org":        org.strip(),
            "description":       desc.strip(),
            "category":          cat,
            "bioticity":         clean(bioticity),
            "extancy":           clean(extancy),
            "domain":            clean(domain),
            "autotrophy":        clean(autotrophy),
            "alteration":        clean(alteration),
            "origin":            clean(origin),
            "registration_date": str(date.today()),
            "URL":               odr_url,
        }

        # Read register, append new row, write back
        try:
            reg = read_csv(REGISTER_FILE_ID)
            for col in new_row:
                if col not in reg.columns:
                    reg[col] = ""
        except Exception:
            reg = pd.DataFrame(columns=list(new_row.keys()))

        reg = pd.concat([reg, pd.DataFrame([new_row])], ignore_index=True)
        write_csv(REGISTER_FILE_ID, reg)

        # Update summary sheet
        try:
            update_summary(reg)
        except Exception as e:
            st.warning(f"Summary sheet update skipped: {e}")

        # Generate label
        label = make_label(sample_id, cat, odr_url)
        buf = io.BytesIO()
        label.save(buf, format="PNG")
        buf.seek(0)

    # Show result
    st.success("Sample registered!")
    st.markdown(f"### `{sample_id}`")
    st.caption(f"ODR record: {odr_url}")
    st.image(label, caption="Printable label")
    st.download_button(
        label="Download label PNG",
        data=buf,
        file_name=f"label_{sample_id}.png",
        mime="image/png",
    )
