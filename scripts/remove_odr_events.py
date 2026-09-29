"""
For cleaning up stray Sample Event child records without
touching the others - e.g. a browser test that accidentally logged
events against a real production sample instead of a [TEST] one.

Works by exploiting the same fact odr_push_child_record()'s docstring
already warns about: ODR replaces a record's *entire* child-record
set with whatever's POSTed. So "deleting" specific children just
means re-sending the full list minus the ones you want gone, with
every kept child's record_uuid intact (so ODR treats it as unchanged,
not a new record).

NOT YET VERIFIED LIVE as of 2026-09-28 - this exact "send back fewer
children than before" case has never been tested against real ODR.
The one time this was needed for real, the stray events were removed
manually in the ODR website UI instead, specifically to avoid trusting
this untested path on a real production record (Andrew Mattioda's
dazzling-tiger-of-essence). Test this against a [TEST]-marked record
first (e.g. add a couple of throwaway events to one, then remove them
with this script) before trusting it against anything real.

Usage, from the repo root:
    python3 scripts/remove_odr_events.py <record_uuid>

Questions or issues? Contact sunanda@exsitu.bio
"""

import sys
from pathlib import Path

import requests
import streamlit as st

# odr_common.py lives at the repo root, one level up from scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from odr_common import odr_get_record, odr_headers  # noqa: E402


def event_summary(fields):
    def val(name):
        for f in fields:
            if f.get("field_name") != name:
                continue
            if "value" in f:
                return f["value"] or ""
            if "values" in f:
                return ", ".join(v["name"] for v in f["values"] if v.get("selected"))
        return ""
    return (f"{val('Date of Action')} | {val('Event Type')} | "
            f"{val('Recorded by (Full Name)')} | {val('Location')} | {val('Notes')[:60]}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/remove_odr_events.py <record_uuid>")
        sys.exit(1)

    record_uuid = sys.argv[1]
    record = odr_get_record(record_uuid)
    events = record.get("records", [])

    if not events:
        print("No child events on this record. Nothing to do.")
        sys.exit(0)

    print(f"Record {record_uuid} has {len(events)} event(s):\n")
    for i, e in enumerate(events):
        print(f"  [{i}] {event_summary(e.get('fields', []))}")

    raw = input("\nEnter event number(s) to REMOVE (comma-separated), or blank to cancel: ").strip()
    if not raw:
        print("Cancelled, nothing changed.")
        sys.exit(0)

    remove_indices = {int(x.strip()) for x in raw.split(",")}
    keep = [e for i, e in enumerate(events) if i not in remove_indices]
    remove = [e for i, e in enumerate(events) if i in remove_indices]

    print(f"\nWill REMOVE {len(remove)} event(s):")
    for e in remove:
        print(f"  - {event_summary(e.get('fields', []))}")
    print(f"\nWill KEEP {len(keep)} event(s):")
    for e in keep:
        print(f"  - {event_summary(e.get('fields', []))}")

    confirm = input("\nProceed? This rewrites the record's child list. [y/N] ")
    if confirm.strip().lower() != "y":
        print("Aborted, nothing changed.")
        sys.exit(0)

    odr_cfg = st.secrets["odr"]
    resp = requests.post(
        f"{odr_cfg['base_url']}/dataset/record",
        headers=odr_headers(),
        json={"database_uuid": odr_cfg["dataset_uuid"], "record_uuid": record_uuid, "records": keep},
        timeout=30,
    )
    resp.raise_for_status()
    print(f"Done. Record now has {len(keep)} event(s).")


if __name__ == "__main__":
    main()
