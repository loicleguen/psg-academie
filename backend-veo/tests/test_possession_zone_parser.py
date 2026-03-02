import pytest
from app.services.possession_zone_parser import parse_veo_possession_zone

VALID_INPUT = """
25%
49%
26%
Défense
Milieu
Attaque
"""


def test_valid_zone_possession():
    result = parse_veo_possession_zone(VALID_INPUT)
    data = result["data"]

    assert isinstance(result, dict)
    assert result["type"] == "zone_de_possession"
    assert data == {
        "Défense": "25%",
        "Milieu": "49%",
        "Attaque": "26%",
    }


def test_invalid_percent_format():
    invalid = """
25
49%
26%
Défense
Milieu
Attaque
"""
    with pytest.raises(ValueError, match="Pourcentage invalide"):
        parse_veo_possession_zone(invalid)


def test_missing_zone_label():
    invalid = """
25%
49%
26%
Défense
Milieu
Zone inconnue
"""
    with pytest.raises(ValueError, match="Zones attendues"):
        parse_veo_possession_zone(invalid)


def test_wrong_number_of_lines():
    too_short = """
25%
49%
Défense
Milieu
"""
    with pytest.raises(ValueError, match="exactement 6 lignes"):
        parse_veo_possession_zone(too_short)


def test_injection_defense():
    malicious = """
25%
49%
26%
<script>alert(1)</script>
Milieu
Attaque
"""
    with pytest.raises(ValueError, match="Zones attendues"):
        parse_veo_possession_zone(malicious)
