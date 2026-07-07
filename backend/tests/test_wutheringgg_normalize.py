from src.wutheringgg.normalize import WEAPON_TYPE, image_url, normalize_character

# Element in the live KO chunk is a nested object {Id, Name, Icon7}, not a string.
RAW = {
    "Id": 1603,
    "Name": "카멜리아",
    "NameEn": "Camellya",
    "QualityId": 5,
    "ElementId": 6,
    "Element": {"Id": 6, "Name": "인멸", "Icon7": "T_IconElementDark3.png"},
    "WeaponType": 2,
    "RoleType": 1,
    "RoleHeadIconBig": "T_IconRoleHead150_29_UI.png",
    "Skills": [{"Name": "s"}],
    "ResonantChainGroup": [{"NodeName": "n"}],
    "Ascension": [],
    "Stats": {"atk": 1},
    "Introduction": "hi",
}


def test_normalize_character():
    c = normalize_character(RAW)
    assert c["id"] == 1603
    assert c["name"] == "카멜리아"
    assert c["name_en"] == "Camellya"
    assert c["rarity"] == 5
    assert c["element"] == "인멸"
    assert c["weapon_type"] == "Sword"
    assert c["weapon_type_ko"] == "직검"
    assert c["head_icon_asset"] == "T_IconRoleHead150_29_UI.png"
    assert len(c["skills"]) == 1 and len(c["resonance_chain"]) == 1


def test_normalize_character_element_as_plain_string():
    # Robust to a plain-string Element (older/other builds).
    c = normalize_character({**RAW, "Element": "인멸"})
    assert c["element"] == "인멸"


def test_image_url():
    assert (
        image_url("iconrolehead150", "T_x.png")
        == "https://wuthering.gg/images/iconrolehead150/T_x.png"
    )


def test_weapon_type_complete():
    assert set(WEAPON_TYPE) == {1, 2, 3, 4, 5}
