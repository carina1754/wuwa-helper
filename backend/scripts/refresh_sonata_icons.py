"""Refresh sonata-set crest icons from Namuwiki into the committed catalog.

Sonata set icons live at ``data/catalog/icons/echoes/s-<hash>.webp`` (76x76 RGBA
webp) and are sourced from the Namuwiki 데이터 스테이션 page (section "4. 화음 도감")
via :func:`src.namu.echoes.parse_sonata_sets`. The committed file wins over the
gitignored media cache (see ``media.cached_catalog_image_path``), so a broken/
placeholder icon MUST be overwritten in the committed dir — re-running the normal
refresh (which writes to the media cache) is not enough.

By default this only re-fetches icons that are the known 1326-byte placeholder;
pass ``--all`` to refresh every set, or ``--names "A,B"`` to target specific sets.

Usage:
  uv run python scripts/refresh_sonata_icons.py            # fix placeholders only
  uv run python scripts/refresh_sonata_icons.py --all      # refetch all 34
  uv run python scripts/refresh_sonata_icons.py --names "내려앉은 깃털의 노래"
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.namu.client import fetch_page, sub_page  # noqa: E402
from src.namu.echoes import parse_sonata_sets  # noqa: E402

ICON_DIR = Path(__file__).resolve().parents[1] / "data" / "catalog" / "icons" / "echoes"
PLACEHOLDER_BYTES = 1326  # the identical blank icon that shipped for unfetched sets
SIZE = (76, 76)  # existing sonata icons are 76x76 RGBA webp


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="refetch every set")
    ap.add_argument("--names", default="", help="comma-separated set names to refetch")
    args = ap.parse_args()

    from PIL import Image  # local import so the script fails loudly if Pillow is missing

    catalog = json.loads((ICON_DIR.parents[2] / "catalog" / "sonata_sets.json").read_text("utf-8"))
    id_by_name = {s["name_ko"]: (s.get("icon") or "").split("/")[-1] for s in catalog}

    # decide which set names to refresh
    if args.names:
        wanted = {n.strip() for n in args.names.split(",") if n.strip()}
    elif args.all:
        wanted = set(id_by_name)
    else:  # placeholders only
        placeholder_ids = {
            os.path.basename(p)[:-5]
            for p in glob.glob(str(ICON_DIR / "s-*.webp"))
            if os.path.getsize(p) == PLACEHOLDER_BYTES
        }
        wanted = {name for name, sid in id_by_name.items() if sid in placeholder_ids}

    if not wanted:
        print("nothing to refresh (no placeholder icons found).")
        return

    namu = {s["name_ko"]: s.get("icon") for s in parse_sonata_sets(fetch_page(sub_page("데이터 스테이션")))}
    for name in sorted(wanted):
        sid = id_by_name.get(name)
        url = namu.get(name)
        if not sid or not url:
            print(f"  SKIP {name}: sid={sid} url={'ok' if url else 'MISSING'}")
            continue
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=30).read()
        im = Image.open(io.BytesIO(data)).convert("RGBA")
        if im.size != SIZE:
            im = im.resize(SIZE, Image.LANCZOS)
        dest = ICON_DIR / f"{sid}.webp"
        im.save(dest, "WEBP")
        print(f"  {name} [{sid}]: saved {dest.stat().st_size}B")


if __name__ == "__main__":
    main()
