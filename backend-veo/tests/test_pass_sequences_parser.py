import pytest
from app.services.pass_sequences_parser import parse_veo_pass_sequence

VALID_INPUT = """
3 à 5 passes
26
6 passes ou plus
3
Enchaînement de passes le plus long
8
"""


def test_valid_pass_chain():
    result = parse_veo_pass_sequence(VALID_INPUT)
    data = result["data"]

    assert result["type"] == "enchaînements_de_passes"
    assert isinstance(data, dict)
    assert data["3 à 5 passes"] == 26
    assert data["6 passes ou plus"] == 3
    assert data["Enchaînement de passes le plus long"] == 8


def test_invalid_label_raises():
    invalid = """
3 à 5 passes
26
Autre libellé
3
Enchaînement de passes le plus long
8
"""
    with pytest.raises(ValueError, match="Label inconnu"):
        parse_veo_pass_sequence(invalid)


def test_non_numeric_value_raises():
    invalid = """
3 à 5 passes
abc
6 passes ou plus
3
Enchaînement de passes le plus long
8
"""
    with pytest.raises(ValueError, match="Valeur numérique attendue"):
        parse_veo_pass_sequence(invalid)


def test_wrong_line_count_raises():
    invalid = """
3 à 5 passes
26
6 passes ou plus
3
"""  # Manque la 3e paire
    with pytest.raises(ValueError, match="exactement 6 lignes"):
        parse_veo_pass_sequence(invalid)
