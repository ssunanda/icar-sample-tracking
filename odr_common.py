"""
Shared ODR + Google Sheets helpers, used by registration.py and
log_an_action.py. Keeping this in one place means both pages use the
exact same field UUIDs and API call shapes - see setup.md "ODR setup"
for how these were discovered/verified.
"""

import io
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload


REGISTER_FILE_ID = "18gy4QKgyGafmTjG4505VCBHUfySvuIed"

# Cloud Run's system timezone is UTC, not any team member's local time -
# using date.today() directly meant the date on a label/record could
# read as "tomorrow" (or diverge from what a person expects) depending
# on the server's UTC offset from whoever's actually using it at that
# moment. Pinning to one fixed zone makes the date consistent and
# predictable regardless of where the server or the viewer actually is.
APP_TIMEZONE = ZoneInfo("America/Los_Angeles")


def today_str():
    """Today's date (YYYY-MM-DD) in APP_TIMEZONE, not the server's
    system zone. Call this once per registration/event and reuse the
    result everywhere it's needed, rather than calling this multiple
    times within one submission - otherwise two calls straddling a
    midnight rollover could disagree with each other."""
    return str(datetime.now(APP_TIMEZONE).date())
SUMMARY_FILE_ID  = "1W7jeb4H0QnhAzh4UHCleqD-ir2jCw60J"

# ── DELIMIT brand colors ─────────────────────────────────────────
# See brand design guide (shared 2026-07-17) - light scheme. Shared
# here (rather than duplicated per-page) since both the label
# generator and the alert() helper below use them.
INK = "#1A1815"
ACCENT = "#557399"
LABEL_GRAY = "#6E6A62"
PANEL = "#F1EEE8"

# Muted, low-saturation tones that fit the earthy brand palette,
# rather than Streamlit's default bright red/green/orange - but still
# semantically colored (not all-blue), since collapsing success/error/
# warning into one color would cost real usability, not just polish.
SUCCESS_COLOR = "#4B7A5B"
ERROR_COLOR = "#A6483A"
WARNING_COLOR = "#B8863B"


def alert(message, kind="info"):
    """Branded replacement for st.success/error/warning - Streamlit's
    [theme] config has no tokens for alert colors at all, so matching
    the brand here means a small custom component instead of a config
    toggle. Kept semantically colored (not just blue) so errors still
    read as urgent at a glance."""
    color = {"success": SUCCESS_COLOR, "error": ERROR_COLOR, "warning": WARNING_COLOR}.get(kind, ACCENT)
    icon = {"success": "✓", "error": "✕", "warning": "!"}.get(kind, "ℹ")
    st.markdown(
        f"""<div style="border-left: 4px solid {color}; background: {PANEL}; color: {INK};
                    padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1rem;">
        <strong style="color:{color};">{icon}</strong>&nbsp; {message}
        </div>""",
        unsafe_allow_html=True,
    )


def success(message):
    alert(message, "success")


def error(message):
    alert(message, "error")


def warning(message):
    alert(message, "warning")


# ── Logo (SVG, embedded inline) ──────────────────────────────────
# The brand assets are real vector SVGs (exact circle/line/text
# coordinates), so embedding them inline renders pixel-perfect at any
# size - no rasterization or resizing step to introduce blur, unlike
# the earlier PNG-based approach. The crop box below was computed once
# from the actual SVG coordinates (line/circle geometry + real text
# metrics measured with the bundled fonts) to trim the large built-in
# padding in the original 1500x400 canvas - see git history for the
# measurement script if the source SVG changes and this needs redoing.
_LOGO_LOCKUP_CROP = (137.5, 111.0, 1197.0, 362.0)  # x0, y0, x1, y1


def render_svg_logo(path, width):
    """Read an SVG brand asset and return markup for st.markdown that
    displays it tightly cropped (see _LOGO_LOCKUP_CROP) at the given
    display width, aspect-ratio preserved."""
    x0, y0, x1, y1 = _LOGO_LOCKUP_CROP
    box_w, box_h = x1 - x0, y1 - y0
    height = width * box_h / box_w
    svg = open(path).read()
    svg = re.sub(
        r"^<svg[^>]*>",
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height:.0f}" '
        f'viewBox="{x0} {y0} {box_w} {box_h}">',
        svg,
        count=1,
    )
    return svg


# ── ODR field/option UUIDs ────────────────────────────────────────
# Specific to the "MMML Sample Repository" dataset - see setup.md
# "ODR setup" for how they were discovered. `dataset_uuid` itself
# lives in secrets.toml (st.secrets["odr"]), not here.

ODR_APP_BASE = "https://www.odr.io"
ODR_SAMPLE_EVENT_DATABASE_UUID = "3151e59de105502af377f83f3691"

ODR_FIELDS = {
    "sample_id":          "08ab15aec85075a469998f6a9a40",
    "subsample_id":       "1e41ca67825f1b83787dd071da6e",
    "sample_category":    "cc5b641aa7d522428d33ae0e8753",
    "description":        "09080b4aa6f0d5cfe2a47f0a4929",
    "source_link":        "4f407c961f84dc80c5ae751aeedf",
    "source_institution": "17fd8d369d5567317245a3d15467",
    "poc_name":           "ea314aa9a85c88cfbb44ba7dd18b",
    "poc_email":          "bd112ea87c72e8bd7219a1c4bdb7",
    "poc_institution":    "3dd0d84178e7af2f8b0764fffd36",
    "registration_date":  "30a9a4bdf17fa23ad4a823613cca",
    "notes":              "e56f044023477f9eb2a2ec52c0bf",
}

# "Point of Contact (Institution)" changed from Paragraph Text to
# Single Select at some point during ODR field updates (confirmed via
# live template pull 2026-07-22) - needs odr_select_option, not
# odr_set_field_value, unlike the rest of ODR_FIELDS.
ODR_POC_INSTITUTION_OPTIONS = {
    "Carnegie Science":          "84d76818314479c5dc38f7b2154e",
    "NASA Ames Research Center": "52a6b94999b0fdcdf483bc68242b",
    "Rutgers University":        "6ded8618fdbdad2f1bf4741b7ca4",
    "Johns Hopkins University":  "ee4e54bf7c7424a4e3b67561f074",
    "Purdue University":         "0454488c480d3fa9d8c0da230ac6",
    "ex situ bio":               "e4e115bb04502f98899217389ed0",
    "Howard University":         "1d7a46ab321695d8cec329ff5fdf",
}

ODR_SAMPLE_CATEGORY_OPTIONS = {
    "Mixed":    "caf0198cf6421945f954e89dfacb",
    "Blob":     "853a4d8a07b9287f3ce61afd761a",
    "Ice":      "fb6c56f3e5c5c33b577015b5ce68",
    "Organism": "a376d01884051fe16bc9483a8ca8",
    "Rock":     "ee44ca146d451672b190effa36fb",
    "Extract":  "03821c91f2cf871d1351556dcb10",
}

ODR_DOMAIN_FIELD_UUID = "e3969174e2cf5a0714bbe443a838"
ODR_DOMAIN_OPTIONS = {
    "Archaea": "748ef1f2127204067b7a52aea2d9",
    "Bacteria": "2e7133da6947a8d12cf36804a238",
    "Eukarya": "e01cf982cbfd96c359f2cdfa47a6",
}

ODR_EVENT_FIELDS = {
    "event_type":              "a65545e51fe6f1ba836371b08dc3",
    "date_of_action":          "1f8d98dfdb27a588af5ddc1ab2c6",
    "location":                "6002cd01c4942438727974eb8961",
    "recorded_by_name":        "bd92b595703d287c38c5c2908edc",
    "recorded_by_institution": "9e1436281804145e0361a541c8ce",
    "recorded_by_email":       "6659765454241cb6ffc5511e646a",
    "notes":                   "8b6d4300b736cd7ab07867f16d1b",
    "attachment":              "64393655fe1656a79207cb24bb99",
}

ODR_EVENT_TYPE_OPTIONS = {
    "Register":            "2e1ecaae1c914884bd208d3d11b5",
    "Ship":                "d7491e43ab1cd1357ffef6142c22",
    "Receive":             "72b4b156b627d0457612f400e4a9",
    "Modify or Process":   "48793b4c75a3b8ccd820e5fee402",
    "Data acquisition":    "b10d74b84f0d9c7c3a01e2684ec1",
    "Other":               "28c12e5d7e2b22d15b449f1b38b0",
}

ODR_RECORDED_BY_INSTITUTION_OPTIONS = {
    "NASA Ames Research Center": "e2e7a97af87a12be72132289157e",
    "Carnegie Science":          "d25131e55e01adf6eaa7cf441836",
    "Howard University":         "9622cf3fb9f727cb2030bcb7eca2",
    "Johns Hopkins University":  "8a845b45852a474b0223608d16df",
    "ex situ bio":               "9f58b9b708376d8c797804530c62",
    "Rutgers University":        "6c6e839467f77a693506ed033cef",
    "Purdue University":         "4706b047c335442af0605a9de98d",
}

# app.py's institution dropdown uses a shorter name than ODR's dropdown
# for one entry - translate before looking up the Sample Event option.
INSTITUTION_TO_ODR_OPTION = {
    "NASA Ames": "NASA Ames Research Center",
}

ICAR_INSTITUTIONS = [
    "NASA Ames",
    "Carnegie Science",
    "Johns Hopkins University",
    "Howard University",
    "Purdue University",
    "Rutgers University",
    "ex situ bio",
]


# ── Google Drive / Sheets ────────────────────────────────────────

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


def _with_retries(fn, attempts=3, base_delay=1.5):
    """Retry on transient network errors (broken pipes, resets) talking
    to Google's API - these happen occasionally and aren't worth
    surfacing as a crash on the first try."""
    last_exc = None
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            if attempt < attempts - 1:
                time.sleep(base_delay * (attempt + 1))
    raise last_exc


def read_csv(file_id):
    def _do():
        service = get_drive_service()
        req = service.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        dl = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = dl.next_chunk()
        buf.seek(0)
        return pd.read_csv(buf, encoding="utf-8-sig")
    return _with_retries(_do)


def write_csv(file_id, df):
    def _do():
        service = get_drive_service()
        buf = io.BytesIO(df.to_csv(index=False).encode("utf-8-sig"))
        media = MediaIoBaseUpload(buf, mimetype="text/csv", resumable=False)
        service.files().update(fileId=file_id, media_body=media).execute()
    _with_retries(_do)


# ── ODR API ───────────────────────────────────────────────────────

def odr_institution_option_uuid(inst):
    odr_name = INSTITUTION_TO_ODR_OPTION.get(inst, inst)
    return ODR_RECORDED_BY_INSTITUTION_OPTIONS.get(odr_name)


def odr_poc_institution_option_uuid(inst):
    odr_name = INSTITUTION_TO_ODR_OPTION.get(inst, inst)
    return ODR_POC_INSTITUTION_OPTIONS.get(odr_name)


def odr_record_url(internal_id):
    """Build the ODR web UI URL for a record. Confirmed 2026-07-20 by
    navigating to a real record via ODR's own Search and copying the
    resulting URL."""
    dataset_uuid = st.secrets["odr"]["dataset_uuid"]
    return f"{ODR_APP_BASE}/{dataset_uuid}#/view/{internal_id}"


# Self-identifying User-Agent on all ODR requests, rather than the
# default python-requests/x.x - good practice for anyone looking at
# ODR's traffic logs, independent of any bot-filtering concerns.
ODR_USER_AGENT = "DELIMIT-Sample-Registration/1.0 (contact: sunanda@exsitu.bio)"


@st.cache_resource(ttl=3300)
def get_odr_token():
    odr_cfg = st.secrets["odr"]
    resp = requests.post(
        f"{odr_cfg['base_url']}/token",
        json={"username": odr_cfg["username"], "password": odr_cfg["password"]},
        headers={"User-Agent": ODR_USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["token"]


def odr_headers():
    return {
        "Authorization": f"Bearer {get_odr_token()}",
        "Content-Type": "application/json",
        "User-Agent": ODR_USER_AGENT,
    }


def odr_create_record():
    """Create an empty top-level Sample record. Returns the created
    record's JSON (has record_uuid, internal_id)."""
    odr_cfg = st.secrets["odr"]
    resp = requests.post(
        f"{odr_cfg['base_url']}/dataset/{odr_cfg['dataset_uuid']}/record",
        headers=odr_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def odr_get_record(record_uuid):
    odr_cfg = st.secrets["odr"]
    resp = requests.get(
        f"{odr_cfg['base_url']}/dataset/record/{record_uuid}",
        headers=odr_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def odr_set_field_value(record_uuid, field_uuid, value):
    """Short Text / Paragraph Text fields only - the /value endpoint
    500s on DateTime fields (confirmed via live testing, seemingly an
    ODR-side bug), use odr_push_fields for those instead. Single
    Select fields need odr_select_option.

    BROKEN as of 2026-08-18: this endpoint 500s on everything now with
    "Service odr.permissions_management_service not found" - an
    ODR-side server bug, not fixed by anything on our end. No current
    callers in this codebase - registration.py was rewritten to batch
    everything through odr_push_fields instead, which still works.
    Left here (not deleted) in case ODR fixes it and single-field
    calls become worth using again for the extra round trips they'd
    save."""
    if not value:
        return
    odr_cfg = st.secrets["odr"]
    resp = requests.post(
        f"{odr_cfg['base_url']}/record/{record_uuid}/{field_uuid}/value",
        headers=odr_headers(),
        json={"value": value},
        timeout=30,
    )
    resp.raise_for_status()


def odr_push_fields(record_uuid, fields):
    """Set fields on a top-level record via the same 'push' mechanism
    as odr_push_child_record - needed for DateTime fields (the /value
    endpoint doesn't support them) but works for any field type."""
    odr_cfg = st.secrets["odr"]
    resp = requests.post(
        f"{odr_cfg['base_url']}/dataset/record",
        headers=odr_headers(),
        json={"database_uuid": odr_cfg["dataset_uuid"], "record_uuid": record_uuid, "fields": fields},
        timeout=30,
    )
    resp.raise_for_status()


def odr_select_option(record_uuid, field_uuid, option_uuid):
    """Single Select fields on a top-level record.

    BROKEN as of 2026-08-18, same as odr_set_field_value above (same
    underlying ODR-side bug, same "permissions_management_service not
    found" error) - see that docstring. No current callers."""
    odr_cfg = st.secrets["odr"]
    resp = requests.put(
        f"{odr_cfg['base_url']}/record/{record_uuid}/{field_uuid}/{option_uuid}/selected",
        headers=odr_headers(),
        timeout=30,
    )
    resp.raise_for_status()


def odr_push_child_record(parent_record_uuid, child_database_uuid, fields):
    """Create (and populate) a child record - e.g. a Sample Event -
    linked to a parent record, in one call. `fields` is a list of
    dicts already shaped as either {"field_uuid", "value"} (text/date)
    or {"field_uuid", "values": [{"template_radio_option_uuid", "selected": 1}]}
    (single select). Returns the created child record's JSON.

    IMPORTANT (confirmed via live testing 2026-07-20): the "records"
    array in this POST is not additive - ODR replaces the parent's
    *entire* child-record set with whatever's sent, deleting any
    existing children not included. So this always re-fetches the
    parent's current children first and echoes them back (with their
    record_uuid intact, so ODR leaves them alone) alongside the new
    one - otherwise every call would silently wipe prior history."""
    odr_cfg = st.secrets["odr"]
    existing_children = odr_get_record(parent_record_uuid).get("records", [])
    resp = requests.post(
        f"{odr_cfg['base_url']}/dataset/record",
        headers=odr_headers(),
        json={
            "database_uuid": odr_cfg["dataset_uuid"],
            "record_uuid": parent_record_uuid,
            "records": existing_children + [{"database_uuid": child_database_uuid, "fields": fields}],
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["records"][-1]


def odr_upload_file(record_uuid, record_database_uuid, field_uuid, file_bytes, filename, content_type="application/octet-stream"):
    """Upload a file to a File/Image field on a record - top-level or
    child, unlike most other write endpoints (confirmed via live
    testing 2026-07-20, this one isn't restricted to top-level
    records). `record_database_uuid` matters and is easy to get wrong:
    for a top-level Sample record it's the main dataset_uuid
    (st.secrets["odr"]["dataset_uuid"]); for a child record (e.g. a
    Sample Event) it's that child datatype's own database_uuid (e.g.
    ODR_SAMPLE_EVENT_DATABASE_UUID), NOT the parent's. Also:
    `template_field_uuid` must be sent as an empty string, not equal
    to `field_uuid` (despite what the API docs' example implies -
    that combination 400s with "Malformed request syntax")."""
    odr_cfg = st.secrets["odr"]
    resp = requests.post(
        f"{odr_cfg['base_url']}/file",
        headers={"Authorization": f"Bearer {get_odr_token()}", "User-Agent": ODR_USER_AGENT},
        files={"file": (filename, file_bytes, content_type)},
        data={
            "name": filename,
            "dataset_uuid": record_database_uuid,
            "field_uuid": field_uuid,
            "template_field_uuid": "",
            "user_email": odr_cfg["username"],
            "record_uuid": record_uuid,
        },
        timeout=60,
    )
    resp.raise_for_status()
