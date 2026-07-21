"""
Register a sample
------------------
The "Register a sample" page, run via st.navigation from app.py (which
sets page config and titles this "Register a sample" in the sidebar).
Streamlit runs this script top-to-bottom every time the user
interacts with anything. Keep that in mind when reading the flow:
1. Imports
2. Sample broad type (must live outside st.form - see note below)
3. Registration form
4. What happens on submit

Questions or issues? Contact sunanda@exsitu.bio
"""

import io
import os
import string
from datetime import date

import streamlit as st
import coolname
import qrcode
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from odr_common import (
    REGISTER_FILE_ID, SUMMARY_FILE_ID, ODR_SAMPLE_EVENT_DATABASE_UUID,
    ODR_FIELDS, ODR_SAMPLE_CATEGORY_OPTIONS, ODR_DOMAIN_FIELD_UUID, ODR_DOMAIN_OPTIONS,
    ODR_EVENT_FIELDS, ODR_EVENT_TYPE_OPTIONS,
    ICAR_INSTITUTIONS, read_csv, write_csv, odr_institution_option_uuid, odr_record_url,
    odr_create_record, odr_set_field_value, odr_push_fields, odr_select_option,
    odr_push_child_record, odr_upload_file,
    INK, ACCENT, LABEL_GRAY, PANEL, success, error, warning, render_svg_logo,
)


ACTIONS = [
    "Register new sample",
    "Sample analysis",
    "Sample alteration/processing",
    "Other",
]

SAMPLE_TYPES = ["Organism", "Rock", "Blob", "Ice", "Mixed", "Extract"]
ORGANISM_SUBTYPES = ["Multicellular", "Community", "Microbe"]
ROCK_SUBTYPES = ["Primitive", "Igneous", "Metamorphic", "Sedimentary"]
DOMAIN_OPTIONS = ["Archaea", "Bacteria", "Eukarya"]
MIXED_EXTRACT_CATEGORIES = ["Organism", "Rock", "Blob", "Ice"]

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


def next_subsample_id(parent_id, existing_ids):
    """First unused <parent_id>-<letter> suffix, checking against every
    ID already in the register (subsamples included)."""
    for letter in string.ascii_uppercase:
        candidate = f"{parent_id}-{letter}"
        if candidate not in existing_ids:
            return candidate
    raise ValueError(f"Ran out of subsample letters (A-Z) for {parent_id}")


# ── Label generator ───────────────────────────────────────────────
# Brand colors imported from odr_common. Fonts are bundled in
# static/fonts/ - loaded by absolute path so this works regardless of
# the process's working directory (local run vs. cloud deploy), unlike
# the previous hardcoded /usr/share/fonts/... path, which only
# happened to exist on some Linux dev machines and would have
# silently fallen back to a default font in most real deploys.

FONT_DIR = os.path.join(os.path.dirname(__file__), "static", "fonts")


LABEL_SCALE = 3  # renders at 3x logical size for print-quality sharpness,
                  # same layout/proportions - a 500x160 label at 1x looks
                  # blurry once actually printed or zoomed into.


def make_label(sample_id, type_label, odr_url):
    SC = LABEL_SCALE
    s = lambda n: round(n * SC)
    W, H, QR_SZ = s(500), s(160), s(120)
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([s(1), s(1), W-s(2), H-s(2)], outline=INK, width=s(2))
    draw.rectangle([s(1), s(1), W-s(2), s(26)], fill=ACCENT)
    try:
        fb = ImageFont.truetype(os.path.join(FONT_DIR, "IBMPlexSans-SemiBold.ttf"), s(13))
        fs = ImageFont.truetype(os.path.join(FONT_DIR, "IBMPlexSans-Regular.ttf"), s(9))
        # Sample ID is the single most important thing someone reads off a
        # physical label at a glance, so it gets the most visual weight -
        # but coolname IDs (especially subsamples, which add "-A" etc.)
        # can run long, so shrink to fit rather than overflowing into the
        # QR code area.
        id_max_width = W - QR_SZ - s(12) - s(12) - s(12)
        fm_size = s(23)
        while fm_size > s(12):
            fm = ImageFont.truetype(os.path.join(FONT_DIR, "SpaceMono-Bold.ttf"), fm_size)
            if draw.textlength(sample_id, font=fm) <= id_max_width:
                break
            fm_size -= 1
    except OSError:
        fb = fm = fs = ImageFont.load_default()
    draw.text((s(12), s(5)),  "DELIMIT SAMPLE", font=fb, fill="white")
    draw.text((s(12), s(32)), "SAMPLE ID",   font=fs, fill=LABEL_GRAY)
    draw.text((s(12), s(43)), sample_id,     font=fm, fill=INK)
    draw.text((s(12), s(80)), type_label,    font=fs, fill=LABEL_GRAY)
    draw.text((s(12), s(94)), str(date.today()), font=fs, fill=LABEL_GRAY)
    draw.rectangle([s(1), H-s(28), W-s(2), H-s(2)], fill=PANEL)
    draw.text((s(12), H-s(21)), "Status: _______________    Mass: _________ mg", font=fs, fill=INK)
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4 * SC, border=1)
    qr.add_data(odr_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color=INK, back_color="white").convert("RGB").resize((QR_SZ, QR_SZ))
    img.paste(qr_img, (W - QR_SZ - s(12), s(26)))
    draw.text((W - QR_SZ - s(12) + s(16), s(26) + QR_SZ + s(2)), "ODR record", font=fs, fill=LABEL_GRAY)
    return img


# ── UI ────────────────────────────────────────────────────────────

st.markdown(render_svg_logo("brand/logo_lockup_light.svg", width=380), unsafe_allow_html=True)
st.markdown(f'<hr style="border: none; border-top: 2px solid {ACCENT}; margin: 0.5rem 0 1.25rem;">',
            unsafe_allow_html=True)
st.subheader("Sample Registration")
st.caption("Fill in the form below and click Register. You'll get a unique sample ID and a printable label. "
           "The label has a QR code that links to a new data record on the Open Data Repository.")

# Registration mode lives outside st.form for the same reason sample_type
# does below: picking "Subsample" needs to immediately reveal the parent
# sample ID field, which a form can't do until submit.
st.subheader("What are you registering?")
registration_mode = st.radio(
    "Registration type *",
    ["New sample", "Subsample of an existing sample"],
    key="registration_mode",
    horizontal=True,
)

parent_sample_id_input = ""
if registration_mode == "Subsample of an existing sample":
    parent_sample_id_input = st.text_input(
        "Parent sample ID *",
        help="The existing sample ID this subsample was taken from, e.g. cool-buffalo-water",
    ).strip()

st.divider()

# Sample broad type lives outside st.form: Streamlit forms only rerun the
# script on submit, so a widget inside a form can't reveal other widgets
# conditionally. Putting this selectbox before the form means picking
# "Ice", "Rock", etc. triggers an immediate rerun that reveals the right
# subtype fields below.
st.subheader("Sample broad type")
sample_type = st.selectbox("Sample broad type *", SAMPLE_TYPES, key="sample_type")

subtype = ""
domain = ""
organic = ""
amorphous = ""
aq_soluble = ""
macromolecular = ""
water_ice = ""
ice_state = ""
mixed_extract_categories = []

if sample_type == "Organism":
    subtype = st.selectbox("Organism subtype *", ORGANISM_SUBTYPES, key="subtype_organism")
    domain = st.selectbox("Domain *", DOMAIN_OPTIONS, key="organism_domain")
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
elif sample_type in ("Mixed", "Extract"):
    mixed_extract_categories = st.multiselect(
        f"Which categories make up this {sample_type.lower()} sample? *",
        MIXED_EXTRACT_CATEGORIES,
        key="mixed_extract_categories",
        help="Just which categories are involved - their individual subtype details aren't captured here.",
    )

st.divider()

# st.form() groups all the widgets below into a single submission.
# Without it, Streamlit reruns the script on every widget change,
# which would generate a new sample ID each time.
with st.form("registration_form", enter_to_submit=False):

    st.subheader("About the sample")
    desc = st.text_input("Brief description (10 words or less) *",
                         help="e.g. Bacteria on an agar slant from deep subsurface drill core")

    st.subheader("Who is registering it?")
    reg_col1, reg_col2, reg_col3 = st.columns(3)
    with reg_col1:
        name = st.text_input("Registrant name *")
    with reg_col2:
        email = st.text_input("Registrant email *")
    with reg_col3:
        inst = st.selectbox("ICAR institution *", ICAR_INSTITUTIONS)

    st.subheader("Sample provenance")
    prov_col1, prov_col2 = st.columns(2)
    with prov_col1:
        source_org = st.text_input("Source institution *",
                                   help="e.g. ATCC, Natural History Museum London")
    with prov_col2:
        location = st.text_input("Current location *")
    existing_url = st.text_input("Existing sample URL (optional)",
                                 help="Link to the sample's existing record (IGSN resolver, catalog page, etc.), if one already exists")

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
    is_subsample = registration_mode == "Subsample of an existing sample"
    if is_subsample and not parent_sample_id_input:
        missing.append("parent sample ID")
    if sample_type in ("Mixed", "Extract") and not mixed_extract_categories:
        missing.append(f"which categories make up this {sample_type.lower()} sample")
    if len(desc.split()) > 10:
        error("Brief description must be 10 words or fewer.")
        st.stop()
    if action == "Other" and not action_detail.strip():
        missing.append('action detail (required when "Other" is selected)')
    if missing:
        error(f"Please fill in: {', '.join(missing)}")
        st.stop()

    with st.spinner("Registering sample..."):
        # Read register once - reused for the uniqueness check, the
        # parent-exists check, and as the base to append the new row to.
        try:
            reg = read_csv(REGISTER_FILE_ID)
        except Exception:
            reg = pd.DataFrame()

        existing_ids = set(reg["sampleID"]) if "sampleID" in reg.columns else set()

        if is_subsample:
            if parent_sample_id_input not in existing_ids:
                error(f'No existing sample with ID "{parent_sample_id_input}" found in the register.')
                st.stop()
            sample_id = next_subsample_id(parent_sample_id_input, existing_ids)
            odr_sample_id_value = parent_sample_id_input
            odr_subsample_id_value = sample_id
        else:
            sample_id = unique_sample_id(existing_ids)
            odr_sample_id_value = sample_id
            odr_subsample_id_value = ""

        if sample_type == "Ice":
            type_label = f"Ice ({ice_state})" if ice_state else "Ice"
        elif subtype:
            type_label = f"{sample_type} ({subtype})"
        else:
            type_label = sample_type

        registration_date = str(date.today())

        # Generated once up front with the fallback (non-clickable) URL,
        # so the download button always has something even if the ODR
        # push below fails entirely. Regenerated with the real ODR URL
        # once that's known (see below), so the QR code that actually
        # ships to ODR and to the user points at the real record.
        odr_url = sample_id
        label = make_label(sample_id, type_label, odr_url)
        buf = io.BytesIO()
        label.save(buf, format="PNG")
        buf.seek(0)

        # ── Push to ODR ──────────────────────────────────────────
        # Best-effort: a hiccup here shouldn't lose the registration -
        # the register sheet + label still get created either way, just
        # with a fallback (non-clickable) QR/URL and a visible warning.
        record_uuid = ""
        try:
            record = odr_create_record()
            record_uuid = record["record_uuid"]
            internal_id = record["internal_id"]

            odr_set_field_value(record_uuid, ODR_FIELDS["sample_id"], odr_sample_id_value)
            odr_set_field_value(record_uuid, ODR_FIELDS["subsample_id"], odr_subsample_id_value)
            odr_set_field_value(record_uuid, ODR_FIELDS["description"], desc.strip())
            odr_set_field_value(record_uuid, ODR_FIELDS["poc_name"], name.strip())
            odr_set_field_value(record_uuid, ODR_FIELDS["poc_email"], email.strip())
            odr_set_field_value(record_uuid, ODR_FIELDS["poc_institution"], inst)
            odr_set_field_value(record_uuid, ODR_FIELDS["source_institution"], source_org.strip())
            odr_set_field_value(record_uuid, ODR_FIELDS["source_link"], existing_url.strip())
            odr_set_field_value(record_uuid, ODR_FIELDS["notes"], notes.strip())
            odr_push_fields(record_uuid, [{"field_uuid": ODR_FIELDS["registration_date"], "value": registration_date}])
            odr_select_option(record_uuid, ODR_FIELDS["sample_category"],
                               ODR_SAMPLE_CATEGORY_OPTIONS[sample_type])
            if domain:
                odr_select_option(record_uuid, ODR_DOMAIN_FIELD_UUID, ODR_DOMAIN_OPTIONS[domain])

            # First Sample Event child: this registration itself.
            event_fields = [
                {"field_uuid": ODR_EVENT_FIELDS["event_type"],
                 "values": [{"template_radio_option_uuid": ODR_EVENT_TYPE_OPTIONS["Register"], "selected": 1}]},
                {"field_uuid": ODR_EVENT_FIELDS["date_of_action"], "value": registration_date},
                {"field_uuid": ODR_EVENT_FIELDS["location"], "value": location.strip()},
                {"field_uuid": ODR_EVENT_FIELDS["recorded_by_name"], "value": name.strip()},
                {"field_uuid": ODR_EVENT_FIELDS["recorded_by_email"], "value": email.strip()},
            ]
            inst_option_uuid = odr_institution_option_uuid(inst)
            if inst_option_uuid:
                event_fields.append({
                    "field_uuid": ODR_EVENT_FIELDS["recorded_by_institution"],
                    "values": [{"template_radio_option_uuid": inst_option_uuid, "selected": 1}],
                })
            if notes.strip():
                event_fields.append({"field_uuid": ODR_EVENT_FIELDS["notes"], "value": notes.strip()})
            event = odr_push_child_record(record_uuid, ODR_SAMPLE_EVENT_DATABASE_UUID, event_fields)

            odr_url = odr_record_url(internal_id)
            # Regenerate the label with the real (clickable) ODR URL now
            # that it's known, and attach it to the Register event -
            # "Traveler" language on the field is a good fit for the
            # physical label that travels with the sample.
            label = make_label(sample_id, type_label, odr_url)
            buf = io.BytesIO()
            label.save(buf, format="PNG")
            buf.seek(0)
            # Only attach the label to ODR when this submission is an
            # actual new-sample registration - if someone picked a
            # different action (e.g. "Sample analysis"), the label was
            # already generated and uploaded when the sample was first
            # registered, so doing it again here would just be a
            # redundant duplicate attachment on every later action.
            if action == "Register new sample":
                odr_upload_file(
                    event["record_uuid"], ODR_SAMPLE_EVENT_DATABASE_UUID, ODR_EVENT_FIELDS["attachment"],
                    buf.getvalue(), f"label_{sample_id}.png", "image/png",
                )
            buf.seek(0)
        except Exception as e:
            warning(f"ODR record creation failed, but the sample was still registered locally: {e}")

        new_row = {
            "sampleID":            sample_id,
            "parent_sample_id":    parent_sample_id_input if is_subsample else "",
            "record_uuid":         record_uuid,
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
            "domain":              domain,
            "mixed_extract_categories": ", ".join(mixed_extract_categories),
            "organic":             organic,
            "amorphous":           amorphous,
            "aq_soluble":          aq_soluble,
            "macromolecular":      macromolecular,
            "water_ice":           water_ice,
            "ice_state":           ice_state,
            "registration_date":   registration_date,
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
            warning(f"Summary sheet update skipped: {e}")

        # Stashed in session_state, not shown directly here - clicking
        # the download button below triggers a rerun (like any button),
        # and "submitted" resets to False on that rerun, so anything
        # only shown inside "if submitted" would vanish right as the
        # user clicks download. Storing it lets the result survive
        # reruns until they explicitly dismiss it.
        st.session_state["last_registration"] = {
            "sample_id": sample_id,
            "odr_url": odr_url,
            "label_bytes": buf.getvalue(),
        }

if st.session_state.get("last_registration"):
    result = st.session_state["last_registration"]
    success("Sample registered!")
    st.markdown(f"### `{result['sample_id']}`")
    st.caption(f"ODR record: {result['odr_url']}")
    st.image(result["label_bytes"], caption="Printable label")
    st.download_button(
        label="Download label PNG",
        data=result["label_bytes"],
        file_name=f"label_{result['sample_id']}.png",
        mime="image/png",
    )
    if st.button("Register another sample"):
        del st.session_state["last_registration"]
        st.rerun()

st.divider()
st.caption("Questions or issues? Contact sunanda@exsitu.bio")
