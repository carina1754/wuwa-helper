from pathlib import Path

import pytest

from src.wutheringgg.extract import extract_array, parse_characters

FIX = Path(__file__).parent / "fixtures" / "wuwagg_characters_ko.js"


def test_extract_array_pulls_enclosing_array():
    text = 'var x=[{"Id":1,"Name":"a"},{"Id":2,"Name":"b[racket]"}];foo'
    arr = extract_array(text, '"Id":2')
    assert arr == [{"Id": 1, "Name": "a"}, {"Id": 2, "Name": "b[racket]"}]


def test_extract_array_ignores_brackets_inside_strings():
    text = '[{"k":"]["},{"k":"x"}]'
    arr = extract_array(text, '"k":"x"')
    assert len(arr) == 2 and arr[0]["k"] == "]["


def test_extract_array_raises_when_anchor_missing():
    with pytest.raises(ValueError):
        extract_array("[]", "nope")


def test_parse_characters_from_fixture():
    text = FIX.read_text(encoding="utf-8")
    chars = parse_characters(text)
    by_id = {c["Id"]: c for c in chars}
    assert 1603 in by_id
    assert by_id[1603]["Name"] == "카멜리아"
    assert by_id[1603]["NameEn"] == "Camellya"
    assert by_id[1603]["QualityId"] == 5
    assert by_id[1603]["WeaponType"] == 2
