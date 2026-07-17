"""
ICAR Sample Registration
------------------------
Streamlit runs this script top-to-bottom every time the user
interacts with anything. Keep that in mind when reading the flow:
1. Page config + imports
2. Google Drive connection
3. Sample broad type (must live outside st.form - see note below)
4. Registration form
5. What happens on submit

Questions or issues? Contact sunanda@exsitu.bio
"""

import io
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
    page_icon=None,
    layout="centered",
)


# ── Google Drive connection ───────────────────────────────────────
# st.secrets pulls from .streamlit/secrets.toml locally,
# or from the Streamlit Cloud secrets manager when deployed.
# See setup.md for how to set this up.

REGISTER_FILE_ID = "18gy4QKgyGafmTjG4505VCBHUfySvuIed"
SUMMARY_FILE_ID  = "1W7jeb4H0QnhAzh4UHCleqD-ir2jCw60J"
ODR_BASE         = "https://odr.io/ICAR/samples/"

ICAR_INSTITUTIONS = [
    "NASA Ames",
    "Carnegie Science",
    "Johns Hopkins University",
    "Howard University",
    "Purdue University",
    "Rutgers University",
    "ex situ bio",
]

ACTIONS = [
    "Register new sample",
    "Sample analysis",
    "Sample alteration/processing",
    "Other",
]

SAMPLE_TYPES = ["Organism", "Rock", "Blob", "Ice", "Mixed", "Extract"]
ORGANISM_SUBTYPES = ["Multicellular", "Community", "Microbe"]
ROCK_SUBTYPES = ["Primitive", "Igneous", "Metaphoric", "Sedimentary"]

# Row = sample_type, columns = counts of matching (field, value) pairs
# within that sample_type. Only columns that actually exist in the
# Google Sheet's summary tab get filled in - add rows/columns there
# to match this map as the sheet evolves.
SUMMARY_COL_MAP = {
    "Organism - Multicellular": ("subtype", "Multicellular"),
    "Organism - Community":     ("subtype", "Community"),
    "Organism - Microbe":       ("subtype", "Microbe"),
    "Rock - Primitive":         ("subtype", "Primitive"),
    "Rock - Igneous":           ("subtype", "Igneous"),
    "Rock - Metaphoric":        ("subtype", "Metaphoric"),
    "Rock - Sedimentary":       ("subtype", "Sedimentary"),
    "Rock Organic Yes":         ("organic", "Yes"),
    "Rock Organic No":          ("organic", "No"),
    "Rock Amorphous Yes":       ("amorphous", "Yes"),
    "Rock Amorphous No":        ("amorphous", "No"),
    "Blob AqSoluble Yes":       ("aq_soluble", "Yes"),
    "Blob AqSoluble No":        ("aq_soluble", "No"),
    "Blob Macromolecular Yes":  ("macromolecular", "Yes"),
    "Blob Macromolecular No":   ("macromolecular", "No"),
    "Ice Water Yes":            ("water_ice", "Yes"),
    "Ice Water No":             ("water_ice", "No"),
    "Ice Solid":                ("ice_state", "Solid"),
    "Ice Liquid":               ("ice_state", "Liquid"),
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
        cat_rows = register_df[register_df["sample_type"] == cat]
        for col_header, (reg_col, val) in SUMMARY_COL_MAP.items():
            if col_header in summary_df.columns:
                count = int((cat_rows[reg_col] == val).sum())
                summary_df.at[i, col_header] = count if count > 0 else ""
    write_csv(SUMMARY_FILE_ID, summary_df)


def unique_sample_id(existing_ids):
    """Generate a 3-word coolname slug, regenerating on the astronomically
    unlikely chance it collides with one already in the register."""
    sample_id = "-".join(coolname.generate(3))
    while sample_id in existing_ids:
        sample_id = "-".join(coolname.generate(3))
    return sample_id


# ── Label generator ───────────────────────────────────────────────

def make_label(sample_id, type_label, odr_url):
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
    draw.text((12, 80), type_label,    font=fs, fill="#555")
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

st.title("ICAR Sample Registration")
st.caption("Fill in the form below and click Register. You'll get a unique sample ID and a printable label.")

# Sample broad type lives outside st.form: Streamlit forms only rerun the
# script on submit, so a widget inside a form can't reveal other widgets
# conditionally. Putting this selectbox before the form means picking
# "Ice", "Rock", etc. triggers an immediate rerun that reveals the right
# subtype fields below.
st.subheader("Sample broad type")
sample_type = st.selectbox("Sample broad type *", SAMPLE_TYPES, key="sample_type")

subtype = ""
organic = ""
amorphous = ""
aq_soluble = ""
macromolecular = ""
water_ice = ""
ice_state = ""

if sample_type == "Organism":
    subtype = st.selectbox("Organism subtype *", ORGANISM_SUBTYPES, key="subtype_organism")
elif sample_type == "Rock":
    subtype = st.selectbox("Rock subtype *", ROCK_SUBTYPES, key="subtype_rock")
    col1, col2 = st.columns(2)
    with col1:
        organic = st.radio("Organic?", ["Yes", "No"], key="rock_organic", horizontal=True)
    with col2:
        amorphous = st.radio("Amorphous?", ["Yes", "No"], key="rock_amorphous", horizontal=True)
elif sample_type == "Blob":
    col1, col2 = st.columns(2)
    with col1:
        aq_soluble = st.radio("AqSoluble (water soluble)?", ["Yes", "No"], key="blob_aqsoluble", horizontal=True)
    with col2:
        macromolecular = st.radio("Macromolecular?", ["Yes", "No"], key="blob_macromolecular", horizontal=True)
elif sample_type == "Ice":
    col1, col2 = st.columns(2)
    with col1:
        water_ice = st.radio("Water ice?", ["Yes", "No"], key="ice_water", horizontal=True)
    with col2:
        ice_state = st.radio("State", ["Solid", "Liquid"], key="ice_state", horizontal=True)

st.divider()

# st.form() groups all the widgets below into a single submission.
# Without it, Streamlit reruns the script on every widget change,
# which would generate a new sample ID each time.
with st.form("registration_form"):

    st.subheader("About the sample")
    desc = st.text_input("Brief description (10 words or less) *",
                         help="e.g. Bacteria on an agar slant from deep subsurface drill core")

    st.divider()
    st.subheader("Who is registering it?")
    name  = st.text_input("Registrant name *")
    email = st.text_input("Registrant email *")
    inst  = st.selectbox("ICAR institution *", ICAR_INSTITUTIONS)

    st.divider()
    st.subheader("Sample provenance")
    source_org = st.text_input("Source institution *",
                               help="e.g. ATCC, Natural History Museum London")
    existing_url = st.text_input("Existing sample URL (optional)",
                                 help="Link to the sample's existing record (IGSN resolver, catalog page, etc.), if one already exists")
    location = st.text_input("Current location *")

    st.divider()
    st.subheader("Action & notes")
    action = st.selectbox("Action being taken *", ACTIONS)
    action_detail = st.text_input("If \"Other\", please specify")
    notes = st.text_area("Notes (optional)", help="Hazards, links to protocols, etc.")

    st.divider()
    submitted = st.form_submit_button("Register Sample", type="primary", use_container_width=True)


# ── On submit ─────────────────────────────────────────────────────
# Everything below only runs when the button is clicked.

if submitted:
    missing = [f for f, v in [("registrant name", name), ("registrant email", email),
                               ("brief description", desc), ("source institution", source_org),
                               ("current location", location)]
               if not v.strip()]
    if len(desc.split()) > 10:
        st.error("Brief description must be 10 words or fewer.")
        st.stop()
    if action == "Other" and not action_detail.strip():
        missing.append('action detail (required when "Other" is selected)')
    if missing:
        st.error(f"Please fill in: {', '.join(missing)}")
        st.stop()

    with st.spinner("Registering sample..."):
        # Read register once - reused both for the uniqueness check
        # below and as the base to append the new row to.
        try:
            reg = read_csv(REGISTER_FILE_ID)
        except Exception:
            reg = pd.DataFrame()

        existing_ids = set(reg["sampleID"]) if "sampleID" in reg.columns else set()
        sample_id = unique_sample_id(existing_ids)
        odr_url   = ODR_BASE + sample_id

        if sample_type == "Ice":
            type_label = f"Ice ({ice_state})" if ice_state else "Ice"
        elif subtype:
            type_label = f"{sample_type} ({subtype})"
        else:
            type_label = sample_type

        new_row = {
            "sampleID":            sample_id,
            "description":         desc.strip(),
            "registrant_name":     name.strip(),
            "registrant_email":    email.strip(),
            "icar_institution":    inst,
            "source_institution":  source_org.strip(),
            "existing_sample_url": existing_url.strip(),
            "current_location":    location.strip(),
            "action":              action_detail.strip() if action == "Other" else action,
            "notes":               notes.strip(),
            "sample_type":         sample_type,
            "subtype":             subtype,
            "organic":             organic,
            "amorphous":           amorphous,
            "aq_soluble":          aq_soluble,
            "macromolecular":      macromolecular,
            "water_ice":           water_ice,
            "ice_state":           ice_state,
            "registration_date":   str(date.today()),
            "URL":                 odr_url,
        }

        for col in new_row:
            if col not in reg.columns:
                reg[col] = ""

        reg = pd.concat([reg, pd.DataFrame([new_row])], ignore_index=True)
        write_csv(REGISTER_FILE_ID, reg)

        # Update summary sheet
        try:
            update_summary(reg)
        except Exception as e:
            st.warning(f"Summary sheet update skipped: {e}")

        # Generate label
        label = make_label(sample_id, type_label, odr_url)
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

st.divider()
st.caption("Questions or issues? Contact sunanda@exsitu.bio")
