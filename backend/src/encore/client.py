"""Fetch character/weapon/echo data from the encore.moe API (api-v2.encore.moe).

The site is a Nuxt SPA backed by a clean REST API:
    list   : GET /api/{lang}/{route}            -> {<container>: [...summaries]}
    detail : GET /api/{lang}/{route}/{id}        -> {...full record}
Images are absolute URLs under https://api.encore.moe/resource/...

Responses are cached to disk so a refresh is reproducible offline and does not
hammer the API (56 chars + 118 weapons + 266 echoes = ~440 detail calls).
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

BASE = "https://api-v2.encore.moe"
_HEADERS = {"Referer": "https://encore.moe/", "User-Agent": "Mozilla/5.0 (wawa-ai-coach)"}
_CACHE_DIR = Path(__file__).resolve().parents[2] / ".encore_cache"

# route -> the key wrapping the list array in the list response
LIST_CONTAINER = {"character": "roleList", "weapon": "weapons", "echo": "Echo"}


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=45) as resp:  # noqa: S310 (fixed host)
        return resp.read().decode("utf-8", "replace")


def _cached(name: str, url: str, *, use_cache: bool) -> str:
    path = _CACHE_DIR / name
    if use_cache and path.exists():
        return path.read_text(encoding="utf-8")
    text = _get(url)
    _CACHE_DIR.mkdir(exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return text


def fetch_list(route: str, lang: str = "ko", *, use_cache: bool = True) -> list[dict]:
    text = _cached(f"{lang}_{route}_list.json", f"{BASE}/api/{lang}/{route}", use_cache=use_cache)
    data = json.loads(text)
    container = LIST_CONTAINER[route]
    return data.get(container, []) if isinstance(data, dict) else data


def fetch_detail(route: str, item_id: int | str, lang: str = "ko", *, use_cache: bool = True) -> dict:
    text = _cached(
        f"{lang}_{route}_{item_id}.json", f"{BASE}/api/{lang}/{route}/{item_id}", use_cache=use_cache
    )
    return json.loads(text)


def fetch_all_details(
    route: str, ids: list, lang: str = "ko", *, use_cache: bool = True, pause: float = 0.03
) -> list[dict]:
    """Fetch every detail record for a route, politely (small pause between live calls)."""
    out = []
    for item_id in ids:
        cache_hit = (_CACHE_DIR / f"{lang}_{route}_{item_id}.json").exists()
        out.append(fetch_detail(route, item_id, lang, use_cache=use_cache))
        if not (use_cache and cache_hit):
            time.sleep(pause)
    return out
