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
