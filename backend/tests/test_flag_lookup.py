"""
Unit tests for flag_lookup utility.
"""

import pytest
from app.utils.flag_lookup import get_flag_from_mmsi, get_flag_info


def test_get_flag_info_known_country():
    res = get_flag_info("PAN")
    assert res is not None
    assert res["code"] == "PAN"
    assert res["name"] == "Panama"
    assert res["emoji"] == "🇵🇦"


def test_get_flag_info_case_insensitive():
    res = get_flag_info("lbr")
    assert res is not None
    assert res["code"] == "LBR"
    assert res["name"] == "Liberia"
    assert res["emoji"] == "🇱🇷"


def test_get_flag_info_unknown_code():
    res = get_flag_info("XYZ")
    assert res is not None
    assert res["code"] == "XYZ"
    assert res["name"] == "XYZ"
    assert res["emoji"] == "🏴"


def test_get_flag_info_empty():
    assert get_flag_info(None) is None
    assert get_flag_info("") is None


def test_get_flag_from_mmsi_known_mid():
    # Panama MID 351, 355
    res = get_flag_from_mmsi(355123456)
    assert res is not None
    assert res["code"] == "PAN"
    assert res["name"] == "Panama"

    # Liberia MID 636
    res_lbr = get_flag_from_mmsi("636012345")
    assert res_lbr is not None
    assert res_lbr["code"] == "LBR"
    assert res_lbr["name"] == "Liberia"

    # Marshall Islands MID 538
    res_mhl = get_flag_from_mmsi(538001234)
    assert res_mhl is not None
    assert res_mhl["code"] == "MHL"
    assert res_mhl["name"] == "Marshall Islands"


def test_get_flag_from_mmsi_unknown_mid():
    res = get_flag_from_mmsi("999123456")
    assert res is not None
    assert res["code"] == "UNK"
    assert res["name"] == "Unknown"
    assert res["emoji"] == "🏳️"


def test_get_flag_from_mmsi_invalid():
    assert get_flag_from_mmsi(None) is None
    assert get_flag_from_mmsi("12") is None
