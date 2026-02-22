import pytest
from app.services.shotmap_parser import parse_veo_shotmap

VALID_INPUT = """
Buts
0
Tirs
6
Total des tentatives
6
0% conversion rate.
0% inside box conversion rate.
0% outside box conversion rate.
33% of total attempts inside box.
67% of total attempts outside box.
"""


def test_valid_shotmap_parsing():
    result = parse_veo_shotmap(VALID_INPUT, club_prefix="TEG")
    data = result["data"]

    assert isinstance(result, dict)
    assert data["Buts"] == "0"
    assert data["Tirs"] == "6"
    assert data["Total des tentatives"] == "6"

    percent_values = [v for v in data.values() if v.endswith("%")]
    assert set(["0%", "33%", "67%"]).issubset(set(percent_values))


def test_missing_values():
    incomplete = """
    Buts
    1
    50% conversion rate.
    """
    result = parse_veo_shotmap(incomplete, club_prefix="TEG")
    data = result["data"]

    assert data["Buts"] == "1"
    assert any(v == "50%" for v in data.values())


def test_formatting_variants():
    messy = """
    Buts   
    2 
    Tirs
    10
    40%    conversion rate.  
    """
    result = parse_veo_shotmap(messy)
    data = result["data"]

    assert data["Buts"] == "2"
    assert data["Tirs"] == "10"
    assert any(v == "40%" for v in data.values())


def test_invalid_percent_ignored():
    invalid = """
    Tirs
    5
    conversion rate.
    3a%
    """
    result = parse_veo_shotmap(invalid)
    data = result["data"]

    # La mauvaise ligne "3a%" ne doit pas être présente
    assert all("3a%" not in v for v in data.values())


def test_defends_against_injection():
    malicious = """
    Buts
    1
    <script>alert('x')</script>
    100% conversion rate.
    """
    result = parse_veo_shotmap(malicious)
    for v in result["data"].values():
        assert "<" not in v
        assert "script" not in v.lower()