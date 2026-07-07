from src.wutheringgg import images


def test_cache_asset_uses_image_url_and_returns_local(monkeypatch):
    seen = {}

    def fake_ensure(kind, item_id, src):
        seen.update(kind=kind, item_id=item_id, src=src)
        return f"/catalog/image/{kind}/{item_id}"

    monkeypatch.setattr(images, "ensure_catalog_image", fake_ensure)
    out = images.cache_asset("characters", "iconrolehead150", "T_IconRoleHead150_29_UI.png")
    assert out == "/catalog/image/characters/T_IconRoleHead150_29_UI"
    assert seen["src"] == "https://wuthering.gg/images/iconrolehead150/T_IconRoleHead150_29_UI.png"


def test_cache_asset_returns_none_for_empty_asset(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("must not call ensure_catalog_image for empty asset")

    monkeypatch.setattr(images, "ensure_catalog_image", boom)
    assert images.cache_asset("characters", "iconrolehead150", "") is None
    assert images.cache_asset("characters", "iconrolehead150", None) is None
