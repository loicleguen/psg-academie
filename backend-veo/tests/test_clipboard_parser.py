"""
tests/test_clipboard_parser.py

Tests unitaires pour la fonction `parse_veo_clipboard` qui transforme du texte brut collé depuis
l'interface VEO en données structurées.

Chaque test vérifie une facette différente du parsing : ordre des équipes, formatage, injection,
nombres flottants, gestion des erreurs, etc.
"""

import pytest
from app.services.clipboard_parser import parse_veo_clipboard

VALID_INPUT = """
FCS
N3
TEG
TEGGFC
But
4
0
Tir
3
6
Total des tentatives
7
6
Corner
3
5
Coup franc
19
14
Throw-in
21
13
Penalty
0
0
Passes effectuées
382
240
Possession en %
62%
38%
Minutes de possession
26
16
Possession remportée
185
186
"""


def test_parse_valid_input_left_team():
    """Vérifie que les statistiques sont correctement extraites quand l'équipe est à gauche."""
    result = parse_veo_clipboard(VALID_INPUT, club_prefix="TEG")

    assert result["equipe"] == "TEG"
    assert result["adversaire"] == "FCS"
    assert result["stats"]["But"]["TEG"] == "0"
    assert result["stats"]["But"]["FCS"] == "4"
    assert result["stats"]["Possession en %"]["TEG"] == "38%"
    assert result["stats"]["Possession en %"]["FCS"] == "62%"


def test_parse_valid_input_right_team():
    """Vérifie que le parser gère correctement quand l'équipe est à droite."""
    reversed_input = """
TEG
TEGGFC
FCS
N3
But
0
4
Tir
6
3
"""
    result = parse_veo_clipboard(reversed_input, club_prefix="TEG")
    assert result["equipe"] == "TEG"
    assert result["adversaire"] == "FCS"
    assert result["stats"]["But"]["TEG"] == "0"
    assert result["stats"]["But"]["FCS"] == "4"


def test_parse_short_input():
    """Vérifie qu'une exception est levée si le texte est trop court ou incomplet."""
    with pytest.raises(ValueError, match="Contenu trop court"):
        parse_veo_clipboard("TEG\nFCS\nBut\n1")


def test_parse_missing_team_prefix():
    """Vérifie qu'une exception est levée si aucun nom d'équipe ne correspond au préfixe."""
    input_text = """
ABC
N3
XYZ
N3
But
1
2
"""
    with pytest.raises(ValueError, match="Aucune équipe ne commence par"):
        parse_veo_clipboard(input_text, club_prefix="TEG")


def test_parse_with_injection_attempt():
    """Vérifie que le parser neutralise les tentatives d'injection HTML/JS."""
    malicious_input = """
TEG
N3
FCS
N3
But
0
4
<script>alert('XSS')</script>
3
"""
    result = parse_veo_clipboard(malicious_input, club_prefix="TEG")
    assert "<script>" not in result["stats"]
    assert all("<" not in k and ">" not in k for k in result["stats"].keys())


def test_parse_float_handling():
    """Vérifie la gestion correcte des pourcentages contenant des virgules."""
    float_input = """
TEG
U19
FCS
U19
Possession en %
38,5%
61,5%
"""
    result = parse_veo_clipboard(float_input, club_prefix="TEG")
    assert result["stats"]["Possession en %"]["TEG"] == "38.5%"
    assert result["stats"]["Possession en %"]["FCS"] == "61.5%"


def test_parse_handles_spacing_and_formatting():
    """Vérifie la robustesse face aux espaces et indentations irrégulières."""
    messy_input = """
TEG  
U19  
FCS  
N3  
   But  
 1  
   3  
        Tir 
4  
2
"""
    result = parse_veo_clipboard(messy_input, club_prefix="TEG")
    assert result["stats"]["But"]["TEG"] == "1"
    assert result["stats"]["But"]["FCS"] == "3"
    assert result["stats"]["Tir"]["TEG"] == "4"
    assert result["stats"]["Tir"]["FCS"] == "2"
