"""Extract embedded JSON arrays from wuthering.gg's minified Nuxt data chunks."""
from __future__ import annotations

import json


def extract_array(text: str, anchor: str) -> list[dict]:
    """Locate `anchor` in `text`, expand to the enclosing JSON array, and parse it.

    Scans the text once, string-aware, tracking bracket depth. The array that
    encloses the anchor position is the top-level ``[`` whose matching ``]`` lies
    past the anchor. Brackets inside JSON string literals are ignored so that a
    ``"]["`` value never confuses the scan. Raises ``ValueError`` if the anchor is
    absent or no enclosing array can be found.
    """
    a = text.find(anchor)
    if a < 0:
        raise ValueError(f"anchor not found: {anchor!r}")

    n = len(text)
    in_str = False
    esc = False
    # Stack of positions of currently-open '[' brackets.
    open_stack: list[int] = []
    j = 0
    while j < n:
        c = text[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "[":
                open_stack.append(j)
            elif c == "]":
                if open_stack:
                    start = open_stack.pop()
                    # If this array spans the anchor, it is the enclosing array.
                    if start <= a <= j:
                        return json.loads(text[start : j + 1])
        j += 1
    raise ValueError("no enclosing array found for anchor")
