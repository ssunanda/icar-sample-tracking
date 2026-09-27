"""
Tests for the pure field-parsing logic in log_an_action.py - turns
ODR's raw field JSON into what the event-history table displays.
"""

import log_an_action


def test_event_field_value_text_field():
    fields = [{"field_name": "Location", "value": "Berkeley lab"}]
    assert log_an_action.event_field_value(fields, "Location") == "Berkeley lab"


def test_event_field_value_missing_value_returns_empty_string():
    fields = [{"field_name": "Notes", "value": None}]
    assert log_an_action.event_field_value(fields, "Notes") == ""


def test_event_field_value_select_field_joins_selected_only():
    fields = [{
        "field_name": "Event Type",
        "values": [
            {"name": "Ship", "selected": 1},
            {"name": "Receive", "selected": 0},
        ],
    }]
    assert log_an_action.event_field_value(fields, "Event Type") == "Ship"


def test_event_field_value_field_not_found_returns_empty_string():
    fields = [{"field_name": "Location", "value": "Berkeley lab"}]
    assert log_an_action.event_field_value(fields, "Notes") == ""
