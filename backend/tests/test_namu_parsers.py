from __future__ import annotations

from src.namu import banners, echoes


def test_namu_parser_modules_expose_functions():
    assert callable(banners.parse_banner_history)
    assert callable(echoes.parse_sonata_sets)
    assert callable(echoes.parse_echoes)


def test_parsers_are_defensive_on_empty_html():
    # A page with no recognizable structure must not raise.
    assert banners.parse_banner_history("<html></html>", "character") == []
    assert echoes.parse_sonata_sets("<html></html>") == []
    assert echoes.parse_echoes("<html></html>") == []


def test_parse_banner_history_master_page_depth():
    """Master 튜닝 page nests versions at h4 / banners at h5. The '1.X/2.X/3.X
    버전' roll-up h3 headings carry no absolute version and must not open a group."""
    html = """
    <h3>3.1. 1.X 버전 [편집]</h3>
    <h3>3.2. 2.X 버전 [편집]</h3>
    <h3>3.3. 3.X 버전 [편집]</h3>
    <h4>3.3.1. 3.0 버전 [편집]</h4>
    <h5>3.3.1.1. 언디파인드 스펙트럼 [편집]</h5>
    <p>이벤트 기간 동안 5성 캐릭터 <a>「린네」</a> 의 튜닝 확률 한정 UP!</p>
    <h5>3.3.1.2. 별빛 (☆) [편집]</h5>
    <p>이벤트 기간 동안 5성 캐릭터 <a>「금희」</a> 의 튜닝 확률 한정 UP!</p>
    """
    res = banners.parse_banner_history(html, "character")
    assert [(b["version"], b["phase"], b["banner_name"]) for b in res] == [
        ("3.0", 1, "언디파인드 스펙트럼"),
        ("3.0", 2, "별빛"),
    ]
    assert res[0]["items"] == ["린네"]
    assert res[1]["is_rerun"] is True


def test_parse_banner_history_sub_article_depth():
    """Per-era sub-articles nest versions at h2 / banners at h3. Structural h2s
    (개요, 관련 틀) must close the group so trailing h3 aren't read as banners."""
    html = """
    <h2>1. 개요 [편집]</h2>
    <h2>3. 1.0 버전 [편집]</h2>
    <h3>3.1. 야밤의 청룡 [편집]</h3>
    <p>이벤트 기간 동안 5성 캐릭터 <a>「기염」</a> 의 튜닝 확률 한정 UP!</p>
    <h2>4. 1.1버전 [편집]</h2>
    <h3>4.1. 눈 속에 트는 새싹 [편집]</h3>
    <p>이벤트 기간 동안 5성 캐릭터 <a>「금희」</a> 의 튜닝 확률 한정 UP!</p>
    <h2>8. 관련 틀 [편집]</h2>
    <h3>8.1. 배너 아님 [편집]</h3>
    """
    res = banners.parse_banner_history(html, "character")
    assert [(b["version"], b["phase"], b["banner_name"]) for b in res] == [
        ("1.0", 1, "야밤의 청룡"),
        ("1.1", 1, "눈 속에 트는 새싹"),
    ]
    assert res[0]["items"] == ["기염"]
