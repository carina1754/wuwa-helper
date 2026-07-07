from __future__ import annotations

from src.namu import banners, characters, echoes


def test_namu_parser_modules_expose_functions():
    assert callable(characters.parse_character)
    assert callable(banners.parse_banner_history)
    assert callable(echoes.parse_sonata_sets)
    assert callable(echoes.parse_echoes)


def test_parsers_are_defensive_on_empty_html():
    # A page with no recognizable structure must not raise.
    assert isinstance(characters.parse_character("<html></html>"), dict)
    assert banners.parse_banner_history("<html></html>", "character") == []
    assert echoes.parse_sonata_sets("<html></html>") == []
    assert echoes.parse_echoes("<html></html>") == []
