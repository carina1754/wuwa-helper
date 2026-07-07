"""Downscale cached game-update banner images (media/updates/*).

The official banners are 4K-ish and huge (10-13 MB each); they only ever render
as a ~900px-wide hero background. This resizes each to a max width and re-encodes
as JPEG, keeping the same id stem so the served path /updates/image/{id} is
unchanged (cached_image_path globs {id}.* regardless of extension).

Usage: uv run python scripts/downscale_update_banners.py [max_width]
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.media import updates_image_dir  # noqa: E402

MAX_WIDTH = int(sys.argv[1]) if len(sys.argv) > 1 else 1280
JPEG_QUALITY = 85


def main() -> None:
    directory = updates_image_dir()
    files = sorted(p for p in directory.glob("*") if p.is_file())
    total_before = total_after = 0
    for src in files:
        before = src.stat().st_size
        total_before += before
        try:
            with Image.open(src) as im:
                im = im.convert("RGB")
                if im.width > MAX_WIDTH:
                    h = round(im.height * MAX_WIDTH / im.width)
                    im = im.resize((MAX_WIDTH, h), Image.LANCZOS)
                dest = src.with_suffix(".jpg")
                im.save(dest, "JPEG", quality=JPEG_QUALITY, optimize=True)
        except Exception as e:  # noqa: BLE001
            print(f"  {src.name}: SKIP ({e})")
            continue
        if dest != src:
            src.unlink()  # drop the original (e.g. .png) so the glob resolves to .jpg
        after = dest.stat().st_size
        total_after += after
        print(f"  {src.stem}: {before // 1024}KB -> {after // 1024}KB")
    print(f"total: {total_before // (1024 * 1024)}MB -> {total_after // (1024 * 1024)}MB  (max_width={MAX_WIDTH})")


if __name__ == "__main__":
    main()
