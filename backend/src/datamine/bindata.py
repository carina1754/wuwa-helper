from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from psycopg import Connection
from psycopg.types.json import Jsonb

from .paths import datamine_root


def _iter_bindata_files(root: Path) -> Iterable[Path]:
    yield from sorted((root / "BinData").rglob("*.json"))


def _table_name(root: Path, path: Path) -> str:
    return path.relative_to(root / "BinData").with_suffix("").as_posix()


def _rows(data: object) -> list[tuple[str, object]]:
    if isinstance(data, list):
        return [(str(i), entry) for i, entry in enumerate(data)]
    return [("0", data)]


def ingest_bindata(conn: Connection, root: Path | None = None) -> int:
    root = root or datamine_root()
    total = 0
    for path in _iter_bindata_files(root):
        table = _table_name(root, path)
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = _rows(data)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM datamine_bindata WHERE table_name = %s", (table,))
            cur.executemany(
                "INSERT INTO datamine_bindata (table_name, row_id, data) VALUES (%s, %s, %s)",
                [(table, rid, Jsonb(entry)) for rid, entry in rows],
            )
        total += len(rows)
    conn.commit()
    return total
