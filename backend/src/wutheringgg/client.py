"""Fetch and locate wuthering.gg's static Nuxt data chunks.

The per-entity KO data arrays live in large `/_nuxt/<hash>.js` chunks that are
lazy-loaded, so they are *not* referenced directly by the page HTML or the entry
bundle. `fetch_chunk_names` therefore expands the chunk graph one hop: it takes
every chunk referenced by the page + entry, downloads each, and unions in the
chunk names *they* reference. `find_data_chunk` then downloads candidates and
returns the one matching an entity's content signature.
"""
from __future__ import annotations

import re
import urllib.request

BASE = "https://wuthering.gg"
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120 Safari/537.36"
)
_CHUNK_RE = re.compile(r"[A-Za-z0-9_-]{8}\.js")

# Signature strings that must all appear in an entity's KO data chunk. The
# Korean names pin the chunk to the KO locale (other-locale chunks carry the
# same English keys but not the Korean strings), and the structural key pins it
# to the entity array rather than an unrelated chunk.
_SIGNATURES = {
    # Verified live against the current build's chunks:
    #   characters -> Bl-Led-z.js  (53 objects)
    #   weapons    -> CaGhi8-P.js  (118 objects; objects use WeaponName/WeaponType)
    #   echoes     -> BcbUvbl9.js  (200 objects; objects use MonsterName + PhantomType)
    # Each signature pairs a structural key (pins to the entity array) with a
    # Korean string (pins to the KO locale chunk over its en/ja/zh siblings).
    "characters": ["카멜리아", '"ResonantChainGroup"'],
    "weapons": ['"WeaponType":', "푸른물결의 빛"],
    "echoes": ['"MonsterName"', '"PhantomType"', "칵찰찰"],
}


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=45) as resp:  # noqa: S310 (fixed host)
        return resp.read().decode("utf-8", "replace")


def download_chunk(name: str) -> str:
    return _get(f"{BASE}/_nuxt/{name}")


def fetch_chunk_names() -> list[str]:
    """Return the transitive one-hop set of `/_nuxt/<hash>.js` chunk names.

    Level 0 is the page HTML plus the entry bundle it references; level 1 adds
    every chunk name referenced by each level-0 chunk. The data chunks surface
    at level 1, so this two-level sweep is what makes live discovery work.
    """
    html = _get(f"{BASE}/ko/characters")
    names = set(_CHUNK_RE.findall(html))
    entry = re.search(r"/_nuxt/([A-Za-z0-9_-]{8}\.js)", html)
    if entry:
        names.update(_CHUNK_RE.findall(download_chunk(entry.group(1))))
    expanded = set(names)
    for name in sorted(names):
        try:
            expanded.update(_CHUNK_RE.findall(download_chunk(name)))
        except Exception:  # noqa: BLE001 - a missing chunk must not abort the sweep
            continue
    return sorted(expanded)


def find_data_chunk(kind: str) -> str:
    sig = _SIGNATURES[kind]
    for name in fetch_chunk_names():
        try:
            text = download_chunk(name)
        except Exception:  # noqa: BLE001
            continue
        if all(s in text for s in sig):
            return text
    raise RuntimeError(f"data chunk not found for {kind}; site build may have changed")
