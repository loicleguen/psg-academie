import pytest
from app.services.pass_location_parser import parse_veo_pass_location

VALID_INPUT = """
3%
86%
11%
Défense
Milieu
Attaque
"""


def test_valid_pass_location():
    result = parse_veo_pass_location(VALID_INPUT)
    data = result["data"]

    assert result["type"] == "emplacement_de_la_passe"
    assert data["Défense"] == "3%"
    assert data["Milieu"] == "86%"
    assert data["Attaque"] == "11%"


def test_incomplete_input():
    incomplete = """
50%
30%
Défense
Milieu
Attaque
"""
    with pytest.raises(ValueError):
        parse_veo_pass_location(incomplete)


def test_extra_values_raises():
    extra = """
    3%
    86%
    11%
    Défense
    Milieu
    Attaque
    Note inutile
    """
    with pytest.raises(ValueError):
        parse_veo_pass_location(extra)


def test_incorrect_order_raises():
    bad_order = """
Défense
Milieu
Attaque
3%
86%
11%
"""
    with pytest.raises(ValueError):
        parse_veo_pass_location(bad_order)


def test_non_percent_format():
    invalid_percent = """
3
86%
11%
Défense
Milieu
Attaque
"""
    with pytest.raises(ValueError):
        parse_veo_pass_location(invalid_percent)