"""
Tests for the pure lookup/formatting helpers in odr_common.py.
Doesn't touch anything that calls the network (ODR API, Google
Drive) - see TESTING.md for the manual checklist that covers those.
"""

import re

import odr_common


def test_odr_institution_option_uuid_translates_nasa_ames():
    # "NASA Ames" in the app's own dropdown maps to ODR's longer name
    # via INSTITUTION_TO_ODR_OPTION before lookup.
    assert odr_common.odr_institution_option_uuid("NASA Ames") == "e2e7a97af87a12be72132289157e"


def test_odr_institution_option_uuid_direct_match():
    assert odr_common.odr_institution_option_uuid("Carnegie Science") == "d25131e55e01adf6eaa7cf441836"


def test_odr_institution_option_uuid_unknown_returns_none():
    assert odr_common.odr_institution_option_uuid("Not A Real Institution") is None


def test_odr_poc_institution_option_uuid_translates_nasa_ames():
    assert odr_common.odr_poc_institution_option_uuid("NASA Ames") == "52a6b94999b0fdcdf483bc68242b"


def test_odr_poc_institution_option_uuid_direct_match():
    assert odr_common.odr_poc_institution_option_uuid("ex situ bio") == "e4e115bb04502f98899217389ed0"


def test_odr_poc_institution_option_uuid_unknown_returns_none():
    assert odr_common.odr_poc_institution_option_uuid("Not A Real Institution") is None


def test_today_str_format():
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", odr_common.today_str())


def test_all_icar_institutions_have_both_uuid_mappings():
    # Every dropdown option in the app must resolve to a real UUID in
    # both option dicts, or a registration/event silently drops that
    # field instead of erroring - catches an institution being added
    # to ICAR_INSTITUTIONS without its ODR option UUIDs.
    for inst in odr_common.ICAR_INSTITUTIONS:
        assert odr_common.odr_institution_option_uuid(inst) is not None, \
            f"{inst!r} has no ODR_RECORDED_BY_INSTITUTION_OPTIONS entry"
        assert odr_common.odr_poc_institution_option_uuid(inst) is not None, \
            f"{inst!r} has no ODR_POC_INSTITUTION_OPTIONS entry"


def test_odr_field_value_text_field():
    fields = [{"field_uuid": "abc", "value": "hello"}]
    assert odr_common.odr_field_value(fields, "abc") == "hello"


def test_odr_field_value_select_field_joins_selected_only():
    fields = [{
        "field_uuid": "abc",
        "values": [
            {"name": "Organism", "selected": 1},
            {"name": "Rock", "selected": 0},
        ],
    }]
    assert odr_common.odr_field_value(fields, "abc") == "Organism"


def test_odr_field_value_missing_field_returns_empty_string():
    fields = [{"field_uuid": "abc", "value": "hello"}]
    assert odr_common.odr_field_value(fields, "does-not-exist") == ""


def _fake_record(sample_id="", subsample_id=""):
    fields = []
    if sample_id:
        fields.append({"field_uuid": odr_common.ODR_FIELDS["sample_id"], "value": sample_id})
    if subsample_id:
        fields.append({"field_uuid": odr_common.ODR_FIELDS["subsample_id"], "value": subsample_id})
    return {"record_uuid": f"uuid-for-{sample_id or subsample_id}", "fields": fields}


def test_odr_existing_sample_ids_top_level_contributes_bare_id(monkeypatch):
    monkeypatch.setattr(odr_common, "odr_search_all_records", lambda: [
        _fake_record(sample_id="cool-buffalo-water"),
    ])
    assert odr_common.odr_existing_sample_ids() == {"cool-buffalo-water"}


def test_odr_existing_sample_ids_subsample_contributes_suffixed_id(monkeypatch):
    # A subsample record's Sample ID field holds the *parent's* bare ID
    # (see registration.py), so only the Subsample ID value should end
    # up in the set - matches the register Sheet's old sampleID
    # column convention.
    monkeypatch.setattr(odr_common, "odr_search_all_records", lambda: [
        _fake_record(sample_id="cool-buffalo-water", subsample_id="cool-buffalo-water-A"),
    ])
    assert odr_common.odr_existing_sample_ids() == {"cool-buffalo-water-A"}


def test_odr_existing_sample_ids_combines_multiple_records(monkeypatch):
    monkeypatch.setattr(odr_common, "odr_search_all_records", lambda: [
        _fake_record(sample_id="cool-buffalo-water"),
        _fake_record(sample_id="cool-buffalo-water", subsample_id="cool-buffalo-water-A"),
        _fake_record(sample_id="dazzling-tiger-of-essence"),
    ])
    assert odr_common.odr_existing_sample_ids() == {
        "cool-buffalo-water", "cool-buffalo-water-A", "dazzling-tiger-of-essence",
    }
