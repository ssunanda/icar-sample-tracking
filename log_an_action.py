"""
Log an action on an existing sample
------------------------------------
Second page of the DELIMIT app: search for a sample already registered
via the main page, see its event history, and log a new event
(Ship / Receive / Sample modified or altered / Data acquisition / Other) against
it. This only ever creates a new Sample Event child record - it never
touches the parent Sample record itself.

Questions or issues? Contact sunanda@exsitu.bio
"""

import pandas as pd
import streamlit as st

from odr_common import (
    ICAR_INSTITUTIONS,
    ODR_ADMIN_URL,
    ODR_EVENT_FIELDS,
    ODR_EVENT_TYPE_OPTIONS,
    ODR_FIELDS,
    ODR_SAMPLE_EVENT_DATABASE_UUID,
    USER_GUIDE_URL,
    error,
    odr_field_value,
    odr_get_record,
    odr_institution_option_uuid,
    odr_push_child_record,
    odr_search_all_records,
    odr_upload_file,
    success,
    today_str,
    warning,
)

st.title("Log an action")
st.caption("Find an existing sample and log something that happened to it - shipping, receiving, "
           "modifying/processing, or collecting instrument data.")
st.caption(f"You can find all samples and their respective IDs on the [DELIMIT ODR database]({ODR_ADMIN_URL}) "
           "(requires logging in with the shared institution ODR account).")
st.caption(f"Need more help? See the [full user guide]({USER_GUIDE_URL}).")


def event_field_value(fields, name):
    for f in fields:
        if f.get("field_name") != name:
            continue
        if "value" in f:
            return f["value"] or ""
        if "values" in f:
            return ", ".join(v["name"] for v in f["values"] if v.get("selected"))
    return ""


# ── Find the sample ─────────────────────────────────────────────────
# Searchable dropdown (Streamlit's selectbox filters as you type) built
# directly from ODR (confirmed working live 2026-09-26), not the
# register Sheet - every entry here is a real ODR record, so there's
# no more "not found" or "no ODR record linked" case to handle; those
# were only possible with the Sheet as an intermediate, possibly-stale
# index. Includes subsamples - they're looked up by their own full
# suffixed ID (e.g. cool-buffalo-water-A), same as a top-level sample.
try:
    all_records = odr_search_all_records()
except Exception as e:
    all_records = []
    warning(f"Couldn't load the sample list for search: {e}")

sample_options = {}  # display label -> sample/subsample ID
sample_by_id = {}     # sample/subsample ID -> {"record_uuid", "description"}
for record in all_records:
    fields = record.get("fields", [])
    sid = odr_field_value(fields, ODR_FIELDS["subsample_id"]) or odr_field_value(fields, ODR_FIELDS["sample_id"])
    if not sid:
        continue
    desc = odr_field_value(fields, ODR_FIELDS["description"])
    label = f"{sid} — {desc}" if desc else sid
    sample_options[label] = sid
    sample_by_id[sid] = {"record_uuid": record.get("record_uuid", ""), "description": desc}

selected_label = st.selectbox(
    "Sample ID",
    options=sorted(sample_options, key=lambda label: sample_options[label]),
    index=None,
    placeholder="Start typing a sample ID or description to search...",
    help="Search by sample ID (e.g. cool-buffalo-water or cool-buffalo-water-A) or its description.",
)
sample_id_input = sample_options.get(selected_label, "")
find_clicked = st.button("Find sample")

if find_clicked:
    if not sample_id_input:
        error("Search for and select a sample first.")
        st.session_state.pop("log_action_record_uuid", None)
    else:
        match = sample_by_id[sample_id_input]
        st.session_state["log_action_sample_id"] = sample_id_input
        st.session_state["log_action_record_uuid"] = match["record_uuid"]
        st.session_state["log_action_description"] = match["description"]

# ── Show what was found + event history + the logging form ─────────

record_uuid = st.session_state.get("log_action_record_uuid")
if record_uuid:
    if st.session_state.get("log_action_last_event"):
        success(st.session_state.pop("log_action_last_event"))
    success(f"Found: `{st.session_state['log_action_sample_id']}` — "
               f"{st.session_state.get('log_action_description', '')}")

    try:
        record = odr_get_record(record_uuid)
    except Exception as e:
        record = None
        warning(f"Couldn't load event history: {e}")

    if record is not None:
        events = record.get("records", [])
        st.subheader(f"Event history ({len(events)})")
        if events:
            rows = [{
                "Date":         event_field_value(e.get("fields", []), "Date of Action"),
                "Event Type":   event_field_value(e.get("fields", []), "Event Type"),
                "Recorded by":  event_field_value(e.get("fields", []), "Recorded by (Name)"),
                "Location":     event_field_value(e.get("fields", []), "Location"),
                "Notes":        event_field_value(e.get("fields", []), "Notes"),
            } for e in events]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.caption("No events logged yet.")

    st.divider()
    st.subheader("Log a new action")
    st.caption("Fields marked with * are required.")

    with st.form("log_action_form", enter_to_submit=False):
        event_type = st.selectbox(
            "Event type *",
            ["Ship", "Receive", "Sample modified or altered", "Data acquisition",
             "Data pre-processed", "Short-term storage", "Long-term storage",
             "Disposed/Consumed", "Lost", "Damaged", "Other"],
            help=(
                "Ship: sent somewhere else. Receive: arrived at a new location. "
                "Sample modified or altered: physically altered, cut, treated, or otherwise changed. "
                "Data acquisition: instrument data collected from it. "
                "Data pre-processed: raw instrument data was cleaned/prepared, not yet fully analyzed. "
                "Short-term storage / Long-term storage: put into storage. "
                "Disposed/Consumed: no longer exists (used up or discarded). "
                "Lost: can't be located. Damaged: harmed but still exists. "
                "Other: anything not covered above - use Notes to explain."
            ),
        )
        loc = st.text_input(
            "Location *",
            help=(
                "Where the sample physically is right now (or where this action happened), "
                "specific enough that someone could find it - e.g. \"Freezer 2, Shelf B, "
                "Berkeley lab\" or \"In transit to Carnegie\"."
            ),
        )
        rname = st.text_input(
            "Recorded by: full name *",
            help="First and last name of the person recording this action.",
        )
        remail = st.text_input(
            "Recorded by: email address *",
            help="An email address that reaches the person recording this action.",
        )
        rinst = st.selectbox(
            "Recorded by: institution *", ICAR_INSTITUTIONS,
            help="Which ICAR-affiliated institution the person recording this action belongs to.",
        )
        rnotes = st.text_area(
            "Notes (optional)",
            help=(
                "Anything else worth recording about this action - e.g. a shipping tracking "
                "number, instrument settings, or context for whoever looks at this next."
            ),
        )
        files = st.file_uploader(
            "Attach file(s) (optional)",
            accept_multiple_files=True,
            help="Instrument data, documents, etc. If a file is in a proprietary format, "
                 "mention that below and include an open-format version too if you have one.",
        )
        file_notes = st.text_input(
            "File format notes (optional)",
            help="If any file above uses a proprietary format (e.g. .wdf, .spc), briefly note "
                 "what software/instrument is needed to open it, and whether an open-format "
                 "version (e.g. .csv) is included too.",
        )
        photos = st.file_uploader(
            "Photos (optional)",
            type=["png", "jpg", "jpeg", "heic", "gif"],
            accept_multiple_files=True,
            help="Photos related to this action, if you have any handy - not required.",
        )
        log_submitted = st.form_submit_button("Log action", type="primary", use_container_width=True)

    if log_submitted:
        missing = [f for f, v in [("location", loc), ("recorded by name", rname),
                                   ("recorded by email", remail)] if not v.strip()]
        if missing:
            error(f"Please fill in: {', '.join(missing)}")
            st.stop()

        event_fields = [
            {"field_uuid": ODR_EVENT_FIELDS["event_type"],
             "values": [{"template_radio_option_uuid": ODR_EVENT_TYPE_OPTIONS[event_type], "selected": 1}]},
            {"field_uuid": ODR_EVENT_FIELDS["date_of_action"], "value": today_str()},
            {"field_uuid": ODR_EVENT_FIELDS["location"], "value": loc.strip()},
            {"field_uuid": ODR_EVENT_FIELDS["recorded_by_name"], "value": rname.strip()},
            {"field_uuid": ODR_EVENT_FIELDS["recorded_by_email"], "value": remail.strip()},
        ]
        inst_option_uuid = odr_institution_option_uuid(rinst)
        if inst_option_uuid:
            event_fields.append({
                "field_uuid": ODR_EVENT_FIELDS["recorded_by_institution"],
                "values": [{"template_radio_option_uuid": inst_option_uuid, "selected": 1}],
            })
        combined_notes = rnotes.strip()
        if file_notes.strip():
            combined_notes = (combined_notes + "\n\n" if combined_notes else "") + f"File format notes: {file_notes.strip()}"
        if combined_notes:
            event_fields.append({"field_uuid": ODR_EVENT_FIELDS["notes"], "value": combined_notes})

        with st.spinner("Logging action..."):
            try:
                event = odr_push_child_record(record_uuid, ODR_SAMPLE_EVENT_DATABASE_UUID, event_fields)
                for f in files:
                    odr_upload_file(
                        event["record_uuid"], ODR_SAMPLE_EVENT_DATABASE_UUID, ODR_EVENT_FIELDS["data_file"],
                        f.getvalue(), f.name, f.type or "application/octet-stream",
                    )
                for photo in photos:
                    odr_upload_file(
                        event["record_uuid"], ODR_SAMPLE_EVENT_DATABASE_UUID, ODR_EVENT_FIELDS["images"],
                        photo.getvalue(), photo.name, photo.type or "application/octet-stream",
                    )
                # Stashed in session_state, not shown directly here - st.rerun()
                # below discards anything rendered in this run before the
                # browser paints it, so a plain success() call right before a
                # rerun never actually reaches the user (same trap
                # registration.py avoids with "last_registration").
                st.session_state["log_action_last_event"] = f"Logged: {event_type} on {st.session_state['log_action_sample_id']}"
                # st.toast() specifically survives a rerun that immediately
                # follows it (unlike success()/error()/etc.) - a floating,
                # attention-grabbing confirmation regardless of scroll
                # position, so it's obvious something happened without
                # needing to scroll up to the success() panel above. Added
                # 2026-09-27 so people stop re-clicking "Log action" to
                # check if it worked.
                st.toast("Logged!", icon="✅")
                st.rerun()
            except Exception as e:
                error(f"Couldn't log this action: {e}")

st.divider()
st.caption("Questions or issues? Contact sunanda@exsitu.bio")
