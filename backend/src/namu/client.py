"""Fetch Namuwiki article HTML (server-rendered) with a browser User-Agent."""
from __future__ import annotations

import urllib.parse
from urllib.request import Request, urlopen

NAMU_BASE = "https://namu.wiki/w/"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
GAME = "명조: 워더링 웨이브"


def page_url(title: str) -> str:
    """Full namu.wiki URL for an article title (spaces/hangul percent-encoded)."""
    return NAMU_BASE + urllib.parse.quote(title)


def sub_page(*parts: str) -> str:
    """Title of a WuWa sub-page, e.g. sub_page('무기', '권총')."""
    return "/".join((GAME, *parts))


def fetch_page(title: str, timeout: int = 30) -> str:
    """Fetch an article's HTML. Raises on transport errors (caller decides)."""
    request = Request(page_url(title), headers={"User-Agent": _USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="ignore")
