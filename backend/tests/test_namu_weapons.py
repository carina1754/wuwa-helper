from __future__ import annotations

from src.namu.weapons import parse_weapons

# Minimal synthetic version of the Namuwiki master weapon table: a rarity
# header row, then a row of 5 icon cells, then a row of 5 name cells, with the
# 5 columns being [대검, 직검, 권총, 권갑, 증폭기].
_MASTER_HTML = """
<table>
  <tr><td>무기 유형 및 목록</td></tr>
  <tr><td>대검 직검 권총 권갑 증폭기</td></tr>
  <tr><td>5성 레귤러 튜닝</td></tr>
  <tr>
    <td><img src="//i.namu.wiki/i/aa.webp"/></td>
    <td><img src="//i.namu.wiki/i/bb.webp"/></td>
    <td><img src="//i.namu.wiki/i/cc.webp"/></td>
    <td><img src="//i.namu.wiki/i/dd.webp"/></td>
    <td><img src="//i.namu.wiki/i/ee.webp"/></td>
  </tr>
  <tr>
    <td>대검A</td><td>직검B</td><td>권총C</td><td>권갑D</td><td>증폭E</td>
  </tr>
  <tr><td>4성 튜닝</td></tr>
  <tr>
    <td><img src="//i.namu.wiki/i/ff.webp"/></td>
    <td></td><td></td><td></td><td></td>
  </tr>
  <tr>
    <td>대검F</td><td></td><td></td><td></td><td></td>
  </tr>
</table>
"""


def test_parse_weapons_extracts_grid():
    weapons = parse_weapons(_MASTER_HTML)
    by_name = {w["name_ko"]: w for w in weapons}
    # 5 five-star (aligned columns) + 1 four-star (only column 0 filled)
    assert len(weapons) == 6
    assert by_name["권총C"] == {
        "name_ko": "권총C",
        "weapon_type": "권총",
        "rarity": 5,
        "icon_source": "https://i.namu.wiki/i/cc.webp",
    }
    assert by_name["대검A"]["weapon_type"] == "대검"
    assert by_name["증폭E"]["weapon_type"] == "증폭기"
    assert by_name["대검F"]["rarity"] == 4


def test_parse_weapons_empty_without_master_table():
    assert parse_weapons("<table><tr><td>무관한 표</td></tr></table>") == []
