"""
Log an action on an existing sample
------------------------------------
Second page of the DELIMIT app: search for a sample already registered
via the main page, see its event history, and log a new event
(Ship / Receive / Modify or Process / Data acquisition / Other) against
it. This only ever creates a new Sample Event child record - it never
touches the parent Sample record itself.

Questions or issues? Contact sunanda@exsitu.bio
"""

import streamlit as st
import pandas as pd

from odr_common import (
    REGISTER_FILE_ID, ODR_SAMPLE_EVENT_DATABASE_UUID, ODR_EVENT_FIELDS,
    ODR_EVENT_TYPE_OPTIONS, ICAR_INSTITUTIONS, read_csv, today_str, odr_institution_option_uuid,
    odr_get_record, odr_push_child_record, success, error, warning,
)


st.title("Log an action")
st.caption("Find an existing sample and log something that happened to it - shipping, receiving, "
           "modifying/processing, or collecting instrument data.")
st.caption("You can find all samples and their respective IDs on the Open Data Repository.")


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

sample_id_input = st.text_input("Sample ID", help="e.g. cool-buffalo-water or cool-buffalo-water-A").strip()
find_clicked = st.button("Find sample")

if find_clicked:
    if not sample_id_input:
        error("Enter a sample ID first.")
        st.session_state.pop("log_action_record_uuid", None)
    else:
        try:
            reg = read_csv(REGISTER_FILE_ID)
        except Exception as e:
            error(f"Couldn't read the register: {e}")
            reg = pd.DataFrame()

        match = reg[reg["sampleID"] == sample_id_input] if "sampleID" in reg.columns else pd.DataFrame()
        if match.empty:
            error(f'No sample with ID "{sample_id_input}" found in the register.')
            st.session_state.pop("log_action_record_uuid", None)
        else:
            row = match.iloc[0]
            record_uuid = row.get("record_uuid", "")
            if not record_uuid or pd.isna(record_uuid):
                error("This sample doesn't have an ODR record linked to it yet "
                         "(registered before ODR integration was added, or the ODR push failed "
                         "at registration time) - can't log an action against it.")
                st.session_state.pop("log_action_record_uuid", None)
            else:
                st.session_state["log_action_sample_id"] = sample_id_input
                st.session_state["log_action_record_uuid"] = record_uuid
                st.session_state["log_action_description"] = row.get("description", "")

# ── Show what was found + event history + the logging form ─────────

record_uuid = st.session_state.get("log_action_record_uuid")
if record_uuid:
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

    with st.form("log_action_form", enter_to_submit=False):
        event_type = st.selectbox(
            "Event type *",
            ["Ship", "Receive", "Modify or Process", "Data acquisition", "Other"],
        )
        loc = st.text_input("Location *")
        rname = st.text_input("Recorded by: name *")
        remail = st.text_input("Recorded by: email *")
        rinst = st.selectbox("Recorded by: institution *", ICAR_INSTITUTIONS)
        rnotes = st.text_area("Notes (optional)")
        st.caption("File attachments (e.g. instrument data) aren't supported here yet - "
                   "add them directly on the record in ODR for now.")
        log_submitted = st.form_submit_button("Log Action", type="primary", use_container_width=True)

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
        if rnotes.strip():
            event_fields.append({"field_uuid": ODR_EVENT_FIELDS["notes"], "value": rnotes.strip()})

        with st.spinner("Logging action..."):
            try:
                odr_push_child_record(record_uuid, ODR_SAMPLE_EVENT_DATABASE_UUID, event_fields)
                success(f"Logged: {event_type} on {st.session_state['log_action_sample_id']}")
                st.rerun()
            except Exception as e:
                error(f"Couldn't log this action: {e}")

st.divider()
st.caption("Questions or issues? Contact sunanda@exsitu.bio")
