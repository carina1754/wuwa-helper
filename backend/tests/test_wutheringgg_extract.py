import pytest
from src.wutheringgg.extract import extract_array


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
