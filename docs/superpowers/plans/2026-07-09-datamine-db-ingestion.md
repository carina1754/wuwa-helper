# Datamine → DB 인제스천 (서브프로젝트 A) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 게임 원본 datamine(`WutheringWaves_Data-3.5/`)을 전량 재실행 가능하게 Postgres에 적재하고(L1 원본 + L2 텍스트맵), 엔진(서브프로젝트 B)이 읽을 정규 캐릭터 슬라이스(L3 `sim_character` + `sim_role_growth`)를 파생·검증한다.

**Architecture:** 신규 Python 패키지 `backend/src/datamine/`. 순수·단일책임 모듈로 분리 — `paths`(루트 해석), `schema`(DDL), `bindata`/`textmap`(L1 제네릭 인제스트), `normalize`(L1→L3 파생), `ingest`(오케스트레이션 CLI). L1은 구조 무관 제네릭 적재(모든 BinData/Textmap 파일). L3는 `datamine_bindata`를 JSONB로 조회해 빌드. 기존 `src/database.py`(psycopg3, `get_connection`, `CREATE TABLE IF NOT EXISTS`, `INSERT … ON CONFLICT`) 패턴 준수.

**Tech Stack:** Python 3, psycopg3(`psycopg`, `psycopg.types.json.Jsonb`, `dict_row`), Postgres(JSONB), pytest. 데이터 원본 = 리포 루트의 `WutheringWaves_Data-3.5/`.

## Global Constraints

- 엔진·데이터는 **백엔드 Python**에 둔다. 이 서브프로젝트는 데이터 레이어만.
- **datamine 전량을 DB에 적재**(RAG 기반). L1 = 가공 없는 원본. 앱 서빙 블롭은 `data_json TEXT` 관례지만, **`datamine_bindata.data`는 JSONB**(원본 내부 질의/RAG를 위해 의도적 예외).
- L3 `element_ko` 어휘는 **build.ts가 소비하는 값**(`응결/용융/전도/기류/회절/인멸`)에 맞춘다. (프론트 i18n의 "냉응" 표기는 표시용이며 엔진과 무관.)
- 테스트는 `backend/tests/conftest.py`가 자동으로 `wuwa_ai_coach_dev`로 리다이렉트. 실 datamine(1980개)이 아니라 `backend/tests/datamine/fixtures/`의 소형 실값 픽스처로만 구동.
- 스탯 저장 규약: `base_crit`/`base_crit_dmg`는 퍼센트로 저장(원본 `Crit 500`→`5.0`, `CritDamage 15000`→`150.0`). ATK/HP/DEF는 원본 정수 그대로.
- 실 테스트는 유저가 수행. 커밋 단계는 포함하되 **실제 커밋/푸시는 유저 승인 시**.

---

## File Structure

**생성:**
- `backend/src/datamine/__init__.py` — 빈 패키지 마커.
- `backend/src/datamine/paths.py` — `datamine_root()` 루트 경로 해석.
- `backend/src/datamine/schema.py` — `DATAMINE_DDL`, `init_datamine_schema(cur)`.
- `backend/src/datamine/bindata.py` — `ingest_bindata(conn, root)` L1 BinData 제네릭 적재.
- `backend/src/datamine/textmap.py` — `ingest_textmap(conn, root)`, `resolve_text(conn, lang, key)`.
- `backend/src/datamine/normalize.py` — `build_sim_role_growth(conn)`, `build_sim_character(conn)`.
- `backend/src/datamine/ingest.py` — `run_ingest()` 오케스트레이션 + `__main__`.
- `backend/scripts/run_datamine_ingest.py` — CLI 래퍼(`uv run python scripts/run_datamine_ingest.py`).
- `backend/tests/datamine/__init__.py`, `backend/tests/datamine/conftest.py` — 테스트 픽스처.
- `backend/tests/datamine/fixtures/datamine/**` — 소형 실값 픽스처 트리.
- `backend/tests/datamine/test_bindata.py`, `test_textmap.py`, `test_normalize.py`, `test_ingest_cli.py`.

**수정:**
- `backend/src/database.py` — `init_db()`에 `init_datamine_schema(cur)` 배선(+ import).

---

## Task 1: 스키마 + 루트 해석 + init_db 배선

**Files:**
- Create: `backend/src/datamine/__init__.py`, `backend/src/datamine/paths.py`, `backend/src/datamine/schema.py`
- Modify: `backend/src/database.py`
- Test: `backend/tests/datamine/__init__.py`, `backend/tests/datamine/test_schema.py`

**Interfaces:**
- Produces:
  - `datamine_root() -> pathlib.Path` (env `DATAMINE_ROOT` 우선, 없으면 리포 루트 `WutheringWaves_Data-3.5`).
  - `DATAMINE_DDL: list[str]`, `init_datamine_schema(cur) -> None`.
  - 테이블: `datamine_bindata(table_name TEXT, row_id TEXT, data JSONB, PK(table_name,row_id))`; `datamine_textmap(lang, category, text_id, content, PK(lang,category,text_id))`; `sim_role_growth(level, breach, atk_ratio, def_ratio, hp_ratio, PK(level,breach))`; `sim_character(id PK, name_ko, name_en, rarity, element_id, element_ko, weapon_type, weapon_type_ko, max_level, base_atk, base_hp, base_def, base_crit, base_crit_dmg, skill_id, skill_tree_group_id, resonant_chain_group_id, data_json, updated_at)`.

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/datamine/__init__.py` = 빈 파일. `backend/tests/datamine/test_schema.py`:

```python
from __future__ import annotations

from pathlib import Path

from src.database import get_connection
from src.datamine.paths import datamine_root
from src.datamine.schema import init_datamine_schema


def test_datamine_root_default_points_at_repo_data():
    root = datamine_root()
    assert root.name == "WutheringWaves_Data-3.5"


def test_datamine_root_env_override(monkeypatch):
    monkeypatch.setenv("DATAMINE_ROOT", "/tmp/xyz")
    assert datamine_root() == Path("/tmp/xyz")


def test_init_datamine_schema_creates_tables():
    with get_connection() as conn:
        with conn.cursor() as cur:
            init_datamine_schema(cur)
            cur.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('datamine_bindata','datamine_textmap','sim_role_growth','sim_character')
                """
            )
            names = {r["table_name"] for r in cur.fetchall()}
        conn.commit()
    assert names == {"datamine_bindata", "datamine_textmap", "sim_role_growth", "sim_character"}
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/datamine/test_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.datamine'`.

- [ ] **Step 3: 최소 구현**

`backend/src/datamine/__init__.py` = 빈 파일.

`backend/src/datamine/paths.py`:

```python
from __future__ import annotations

import os
from pathlib import Path

# paths.py → datamine → src → backend → <repo root>
DEFAULT_DATAMINE_ROOT = Path(__file__).resolve().parents[3] / "WutheringWaves_Data-3.5"


def datamine_root() -> Path:
    env = os.getenv("DATAMINE_ROOT")
    return Path(env) if env else DEFAULT_DATAMINE_ROOT
```

`backend/src/datamine/schema.py`:

```python
from __future__ import annotations

DATAMINE_DDL: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS datamine_bindata (
        table_name TEXT NOT NULL,
        row_id TEXT NOT NULL,
        data JSONB NOT NULL,
        PRIMARY KEY (table_name, row_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS datamine_textmap (
        lang TEXT NOT NULL,
        category TEXT NOT NULL,
        text_id TEXT NOT NULL,
        content TEXT NOT NULL,
        PRIMARY KEY (lang, category, text_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sim_role_growth (
        level INTEGER NOT NULL,
        breach INTEGER NOT NULL,
        atk_ratio INTEGER NOT NULL,
        def_ratio INTEGER NOT NULL,
        hp_ratio INTEGER NOT NULL,
        PRIMARY KEY (level, breach)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sim_character (
        id INTEGER PRIMARY KEY,
        name_ko TEXT,
        name_en TEXT,
        rarity INTEGER,
        element_id INTEGER,
        element_ko TEXT,
        weapon_type INTEGER,
        weapon_type_ko TEXT,
        max_level INTEGER,
        base_atk DOUBLE PRECISION,
        base_hp DOUBLE PRECISION,
        base_def DOUBLE PRECISION,
        base_crit DOUBLE PRECISION,
        base_crit_dmg DOUBLE PRECISION,
        skill_id INTEGER,
        skill_tree_group_id INTEGER,
        resonant_chain_group_id INTEGER,
        data_json TEXT NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_datamine_textmap_lookup ON datamine_textmap(lang, text_id)",
]


def init_datamine_schema(cur) -> None:
    for ddl in DATAMINE_DDL:
        cur.execute(ddl)
```

`backend/src/database.py` 수정 — 파일 상단 import 블록 끝에 추가:

```python
from .datamine.schema import init_datamine_schema
```

그리고 `init_db()` 내부, 인덱스 생성들(`idx_site_updates_date`) 직후이자 `conn.commit()` 직전에 한 줄 추가:

```python
            cur.execute("CREATE INDEX IF NOT EXISTS idx_site_updates_date ON site_updates(date)")
            init_datamine_schema(cur)
        conn.commit()
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/datamine/test_schema.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: 커밋**

```bash
git add backend/src/datamine/__init__.py backend/src/datamine/paths.py backend/src/datamine/schema.py backend/src/database.py backend/tests/datamine/__init__.py backend/tests/datamine/test_schema.py
git commit -m "feat(datamine): L1/L3 schema + datamine_root resolver, wired into init_db"
```

---

## Task 2: L1 BinData 제네릭 적재 + 테스트 픽스처

**Files:**
- Create: `backend/src/datamine/bindata.py`
- Create: `backend/tests/datamine/conftest.py`
- Create: `backend/tests/datamine/fixtures/datamine/BinData/role/roleinfo.json`
- Create: `backend/tests/datamine/fixtures/datamine/BinData/property/baseproperty.json`
- Create: `backend/tests/datamine/fixtures/datamine/BinData/property/rolepropertygrowth.json`
- Create: `backend/tests/datamine/fixtures/datamine/Textmaps/ko/multi_text/MultiText.json`
- Create: `backend/tests/datamine/fixtures/datamine/Textmaps/en/multi_text/MultiText.json`
- Test: `backend/tests/datamine/test_bindata.py`

**Interfaces:**
- Consumes: `datamine_root()`(Task 1), `datamine_bindata` 테이블(Task 1).
- Produces:
  - `ingest_bindata(conn, root=None) -> int` — `root/BinData/**/*.json`를 순회, 파일당 `DELETE WHERE table_name=?` 후 전 행 INSERT. `table_name` = BinData 이하 posix 상대경로에서 `.json` 제거(예: `role/roleinfo`). 리스트 파일은 인덱스를 `row_id`로, 비리스트는 `row_id="0"`. 반환 = 적재 행 수.
  - 공용 테스트 픽스처: `backend/tests/datamine/conftest.py`의 `conn` 픽스처(DB 초기화 + datamine 테이블 TRUNCATE + `DATAMINE_ROOT`를 픽스처 트리로 지정), `FIXTURE_ROOT`.

- [ ] **Step 1: 실패 테스트 작성**

먼저 픽스처 파일들(정확한 실값):

`backend/tests/datamine/fixtures/datamine/BinData/role/roleinfo.json`:

```json
[
  {"Id": 1108, "QualityId": 5, "RoleType": 1, "IsTrial": false, "Name": "RoleInfo_1108_Name", "NickName": "RoleInfo_1108_Name", "Introduction": "FavorRoleInfo_1108_Info", "ElementId": 1, "PropertyId": 1108, "WeaponType": 2, "MaxLevel": 90, "SkillId": 1108, "SkillTreeGroupId": 1108, "ResonantChainGroupId": 1108},
  {"Id": 9999, "QualityId": 2, "RoleType": 1, "IsTrial": true, "Name": "RoleInfo_9999_Name", "ElementId": 3, "PropertyId": 9999, "WeaponType": 1, "MaxLevel": 90}
]
```

`backend/tests/datamine/fixtures/datamine/BinData/property/baseproperty.json`:

```json
[
  {"Id": 1108, "Lv": 1, "LifeMax": 824, "Life": 824, "Atk": 37, "Crit": 500, "CritDamage": 15000, "Def": 91},
  {"Id": 1108, "Lv": 2, "LifeMax": 900, "Life": 900, "Atk": 40, "Crit": 500, "CritDamage": 15000, "Def": 95}
]
```

`backend/tests/datamine/fixtures/datamine/BinData/property/rolepropertygrowth.json`:

```json
[
  {"Id": 1, "Level": 1, "BreachLevel": 0, "LifeMaxRatio": 10000, "AtkRatio": 10000, "DefRatio": 10000},
  {"Id": 96, "Level": 90, "BreachLevel": 6, "LifeMaxRatio": 125000, "AtkRatio": 125000, "DefRatio": 122222}
]
```

`backend/tests/datamine/fixtures/datamine/Textmaps/ko/multi_text/MultiText.json`:

```json
[
  {"Id": "RoleInfo_1108_Name", "Content": "히유키"}
]
```

`backend/tests/datamine/fixtures/datamine/Textmaps/en/multi_text/MultiText.json`:

```json
[
  {"Id": "RoleInfo_1108_Name", "Content": "Hiyuki"}
]
```

`backend/tests/datamine/conftest.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest

from src.database import get_connection, init_db

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "datamine"

_DATAMINE_TABLES = "datamine_bindata, datamine_textmap, sim_character, sim_role_growth"


@pytest.fixture(autouse=True)
def _datamine_env(monkeypatch):
    monkeypatch.setenv("DATAMINE_ROOT", str(FIXTURE_ROOT))


@pytest.fixture
def conn():
    init_db()  # base tables + datamine tables (wired into init_db in Task 1)
    with get_connection() as c:
        with c.cursor() as cur:
            cur.execute(f"TRUNCATE {_DATAMINE_TABLES}")
        c.commit()
        yield c
```

`backend/tests/datamine/test_bindata.py`:

```python
from __future__ import annotations

from src.datamine.bindata import ingest_bindata


def test_ingest_bindata_loads_all_files(conn):
    total = ingest_bindata(conn)
    # roleinfo(2) + baseproperty(2) + rolepropertygrowth(2)
    assert total == 6


def test_ingest_bindata_table_names_use_posix(conn):
    ingest_bindata(conn)
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT table_name FROM datamine_bindata ORDER BY table_name")
        tables = [r["table_name"] for r in cur.fetchall()]
    assert tables == ["property/baseproperty", "property/rolepropertygrowth", "role/roleinfo"]


def test_ingest_bindata_addressable_by_json_id(conn):
    ingest_bindata(conn)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT data FROM datamine_bindata WHERE table_name = %s AND data->>'Id' = %s",
            ("role/roleinfo", "1108"),
        )
        row = cur.fetchone()
    assert row is not None
    assert row["data"]["ElementId"] == 1
    assert row["data"]["WeaponType"] == 2


def test_ingest_bindata_is_idempotent(conn):
    ingest_bindata(conn)
    total = ingest_bindata(conn)
    assert total == 6
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) AS n FROM datamine_bindata")
        assert cur.fetchone()["n"] == 6
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/datamine/test_bindata.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.datamine.bindata'`.

- [ ] **Step 3: 최소 구현**

`backend/src/datamine/bindata.py`:

```python
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
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/datamine/test_bindata.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: 커밋**

```bash
git add backend/src/datamine/bindata.py backend/tests/datamine/conftest.py backend/tests/datamine/fixtures backend/tests/datamine/test_bindata.py
git commit -m "feat(datamine): generic L1 BinData ingestion + test fixtures"
```

---

## Task 3: L1 Textmap 적재 + `resolve_text`

**Files:**
- Create: `backend/src/datamine/textmap.py`
- Test: `backend/tests/datamine/test_textmap.py`

**Interfaces:**
- Consumes: `datamine_root()`, `datamine_textmap` 테이블, 픽스처 트리(Task 2).
- Produces:
  - `ingest_textmap(conn, root=None) -> int` — `root/Textmaps/**/*.json`를 순회. `lang` = Textmaps 이하 첫 세그먼트, `category` = 나머지 경로(`.json` 제거, posix). 각 엔트리 `{Id, Content}` → `(lang, category, str(Id), Content)`. 파일당 `DELETE WHERE lang=? AND category=?` 후 INSERT. 반환 = 행 수.
  - `resolve_text(conn, lang, key) -> str | None` — `(lang, text_id=key)` 첫 매치의 content. string 키는 전역 유니크라 category 무시.

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/datamine/test_textmap.py`:

```python
from __future__ import annotations

from src.datamine.textmap import ingest_textmap, resolve_text


def test_ingest_textmap_loads_langs(conn):
    total = ingest_textmap(conn)
    assert total == 2  # ko(1) + en(1)
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT lang FROM datamine_textmap ORDER BY lang")
        langs = [r["lang"] for r in cur.fetchall()]
    assert langs == ["en", "ko"]


def test_ingest_textmap_category_from_path(conn):
    ingest_textmap(conn)
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT category FROM datamine_textmap")
        cats = {r["category"] for r in cur.fetchall()}
    assert cats == {"multi_text/MultiText"}


def test_resolve_text_string_key(conn):
    ingest_textmap(conn)
    assert resolve_text(conn, "ko", "RoleInfo_1108_Name") == "히유키"
    assert resolve_text(conn, "en", "RoleInfo_1108_Name") == "Hiyuki"


def test_resolve_text_missing_returns_none(conn):
    ingest_textmap(conn)
    assert resolve_text(conn, "ko", "Nope_Nonexistent") is None
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/datamine/test_textmap.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.datamine.textmap'`.

- [ ] **Step 3: 최소 구현**

`backend/src/datamine/textmap.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from psycopg import Connection

from .paths import datamine_root


def _iter_textmap_files(root: Path) -> Iterable[Path]:
    yield from sorted((root / "Textmaps").rglob("*.json"))


def _lang_and_category(root: Path, path: Path) -> tuple[str, str]:
    parts = path.relative_to(root / "Textmaps").with_suffix("").parts
    lang = parts[0]
    category = "/".join(parts[1:]) if len(parts) > 1 else "_"
    return lang, category


def ingest_textmap(conn: Connection, root: Path | None = None) -> int:
    root = root or datamine_root()
    total = 0
    for path in _iter_textmap_files(root):
        lang, category = _lang_and_category(root, path)
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            continue
        rows = [
            (lang, category, str(e["Id"]), e.get("Content") or "")
            for e in data
            if isinstance(e, dict) and "Id" in e
        ]
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM datamine_textmap WHERE lang = %s AND category = %s",
                (lang, category),
            )
            cur.executemany(
                "INSERT INTO datamine_textmap (lang, category, text_id, content) VALUES (%s, %s, %s, %s)",
                rows,
            )
        total += len(rows)
    conn.commit()
    return total


def resolve_text(conn: Connection, lang: str, key: str) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT content FROM datamine_textmap WHERE lang = %s AND text_id = %s LIMIT 1",
            (lang, key),
        )
        row = cur.fetchone()
    return row["content"] if row else None
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/datamine/test_textmap.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: 커밋**

```bash
git add backend/src/datamine/textmap.py backend/tests/datamine/test_textmap.py
git commit -m "feat(datamine): L1 textmap ingestion + resolve_text"
```

---

## Task 4: L3 `sim_role_growth` 파생

**Files:**
- Create: `backend/src/datamine/normalize.py`
- Test: `backend/tests/datamine/test_normalize.py` (성장 커브 파트)

**Interfaces:**
- Consumes: `datamine_bindata`(Task 2 적재), `sim_role_growth` 테이블(Task 1).
- Produces: `build_sim_role_growth(conn) -> int` — `datamine_bindata`의 `property/rolepropertygrowth` 전 행을 `sim_role_growth(level, breach, atk_ratio, def_ratio, hp_ratio)`로 upsert. 반환 = 행 수.

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/datamine/test_normalize.py`:

```python
from __future__ import annotations

from src.datamine.bindata import ingest_bindata
from src.datamine.normalize import build_sim_role_growth


def test_build_sim_role_growth(conn):
    ingest_bindata(conn)
    n = build_sim_role_growth(conn)
    assert n == 2
    with conn.cursor() as cur:
        cur.execute(
            "SELECT atk_ratio, def_ratio, hp_ratio FROM sim_role_growth WHERE level = 90 AND breach = 6"
        )
        row = cur.fetchone()
    assert row["atk_ratio"] == 125000
    assert row["def_ratio"] == 122222
    assert row["hp_ratio"] == 125000
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/datamine/test_normalize.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.datamine.normalize'`.

- [ ] **Step 3: 최소 구현**

`backend/src/datamine/normalize.py`:

```python
from __future__ import annotations

from psycopg import Connection


def _bindata_rows(conn: Connection, table_name: str) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute("SELECT data FROM datamine_bindata WHERE table_name = %s", (table_name,))
        return [r["data"] for r in cur.fetchall()]


def build_sim_role_growth(conn: Connection) -> int:
    rows = _bindata_rows(conn, "property/rolepropertygrowth")
    n = 0
    with conn.cursor() as cur:
        for d in rows:
            cur.execute(
                """
                INSERT INTO sim_role_growth (level, breach, atk_ratio, def_ratio, hp_ratio)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (level, breach) DO UPDATE SET
                    atk_ratio = EXCLUDED.atk_ratio,
                    def_ratio = EXCLUDED.def_ratio,
                    hp_ratio = EXCLUDED.hp_ratio
                """,
                (d["Level"], d["BreachLevel"], d["AtkRatio"], d["DefRatio"], d["LifeMaxRatio"]),
            )
            n += 1
    conn.commit()
    return n
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/datamine/test_normalize.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: 커밋**

```bash
git add backend/src/datamine/normalize.py backend/tests/datamine/test_normalize.py
git commit -m "feat(datamine): L3 sim_role_growth from rolepropertygrowth"
```

---

## Task 5: L3 `sim_character` 파생 + 히유키 검증

**Files:**
- Modify: `backend/src/datamine/normalize.py`
- Test: `backend/tests/datamine/test_normalize.py` (캐릭터 파트 추가)

**Interfaces:**
- Consumes: `datamine_bindata`(role/roleinfo, property/baseproperty), `datamine_textmap`(Task 3), `resolve_text`(Task 3), `sim_character`/`sim_role_growth` 테이블.
- Produces: `build_sim_character(conn) -> int` — 플레이어블 캐릭(`RoleType==1 & not IsTrial & QualityId>=4`)만 파싱. 각 캐릭 base = `baseproperty`의 `Id==PropertyId & Lv==1`. `element_ko`/`weapon_type_ko`는 정적 맵. `base_crit=Crit/100`, `base_crit_dmg=CritDamage/100`. `name_ko/name_en`은 `resolve_text`로 `Name` 키 해석. `sim_character` upsert. 반환 = 캐릭 수.

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/datamine/test_normalize.py`에 추가:

```python
from src.datamine.normalize import build_sim_character
from src.datamine.textmap import ingest_textmap


def test_build_sim_character_hiyuki(conn):
    ingest_bindata(conn)
    ingest_textmap(conn)
    n = build_sim_character(conn)
    assert n == 1  # 트라이얼/저레어 9999는 제외

    with conn.cursor() as cur:
        cur.execute("SELECT * FROM sim_character WHERE id = 1108")
        c = cur.fetchone()
    assert c["name_ko"] == "히유키"
    assert c["name_en"] == "Hiyuki"
    assert c["rarity"] == 5
    assert c["element_id"] == 1
    assert c["element_ko"] == "응결"
    assert c["weapon_type"] == 2
    assert c["weapon_type_ko"] == "직검"
    assert c["base_atk"] == 37
    assert c["base_def"] == 91
    assert c["base_crit"] == 5.0
    assert c["base_crit_dmg"] == 150.0
    assert c["skill_id"] == 1108
    assert c["resonant_chain_group_id"] == 1108


def test_sim_character_lv90_atk_matches_phro(conn):
    ingest_bindata(conn)
    ingest_textmap(conn)
    build_sim_role_growth(conn)
    build_sim_character(conn)
    with conn.cursor() as cur:
        cur.execute("SELECT base_atk FROM sim_character WHERE id = 1108")
        base_atk = cur.fetchone()["base_atk"]
        cur.execute("SELECT atk_ratio FROM sim_role_growth WHERE level = 90 AND breach = 6")
        ratio = cur.fetchone()["atk_ratio"]
    lv90_atk = base_atk * ratio / 10000.0
    assert lv90_atk == 462.5  # phro 히유키 캐릭 base ATK와 일치
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/datamine/test_normalize.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_sim_character'`.

- [ ] **Step 3: 최소 구현**

`backend/src/datamine/normalize.py` 상단에 import·상수 추가, 함수 추가:

```python
from __future__ import annotations

import json

from psycopg import Connection

from .textmap import resolve_text

_ELEMENT_KO = {1: "응결", 2: "용융", 3: "전도", 4: "기류", 5: "회절", 6: "인멸"}
_WEAPON_TYPE_KO = {1: "브로드소드", 2: "직검", 3: "권총", 4: "권갑", 5: "증폭기"}
```

(기존 `_bindata_rows`/`build_sim_role_growth`는 유지.)

```python
def _is_playable(d: dict) -> bool:
    return d.get("RoleType") == 1 and not d.get("IsTrial") and (d.get("QualityId") or 0) >= 4


def build_sim_character(conn: Connection) -> int:
    roles = [d for d in _bindata_rows(conn, "role/roleinfo") if _is_playable(d)]
    base_by_id = {
        d["Id"]: d
        for d in _bindata_rows(conn, "property/baseproperty")
        if d.get("Lv") == 1
    }
    n = 0
    with conn.cursor() as cur:
        for r in roles:
            base = base_by_id.get(r.get("PropertyId") or r["Id"])
            if base is None:
                continue
            rec = {
                "id": r["Id"],
                "name_ko": resolve_text(conn, "ko", r.get("Name") or ""),
                "name_en": resolve_text(conn, "en", r.get("Name") or ""),
                "rarity": r.get("QualityId"),
                "element_id": r.get("ElementId"),
                "element_ko": _ELEMENT_KO.get(r.get("ElementId")),
                "weapon_type": r.get("WeaponType"),
                "weapon_type_ko": _WEAPON_TYPE_KO.get(r.get("WeaponType")),
                "max_level": r.get("MaxLevel"),
                "base_atk": base["Atk"],
                "base_hp": base["LifeMax"],
                "base_def": base["Def"],
                "base_crit": base["Crit"] / 100.0,
                "base_crit_dmg": base["CritDamage"] / 100.0,
                "skill_id": r.get("SkillId"),
                "skill_tree_group_id": r.get("SkillTreeGroupId"),
                "resonant_chain_group_id": r.get("ResonantChainGroupId"),
            }
            cur.execute(
                """
                INSERT INTO sim_character (
                    id, name_ko, name_en, rarity, element_id, element_ko,
                    weapon_type, weapon_type_ko, max_level,
                    base_atk, base_hp, base_def, base_crit, base_crit_dmg,
                    skill_id, skill_tree_group_id, resonant_chain_group_id,
                    data_json, updated_at
                ) VALUES (
                    %(id)s, %(name_ko)s, %(name_en)s, %(rarity)s, %(element_id)s, %(element_ko)s,
                    %(weapon_type)s, %(weapon_type_ko)s, %(max_level)s,
                    %(base_atk)s, %(base_hp)s, %(base_def)s, %(base_crit)s, %(base_crit_dmg)s,
                    %(skill_id)s, %(skill_tree_group_id)s, %(resonant_chain_group_id)s,
                    %(data_json)s, now()
                )
                ON CONFLICT (id) DO UPDATE SET
                    name_ko = EXCLUDED.name_ko, name_en = EXCLUDED.name_en, rarity = EXCLUDED.rarity,
                    element_id = EXCLUDED.element_id, element_ko = EXCLUDED.element_ko,
                    weapon_type = EXCLUDED.weapon_type, weapon_type_ko = EXCLUDED.weapon_type_ko,
                    max_level = EXCLUDED.max_level, base_atk = EXCLUDED.base_atk, base_hp = EXCLUDED.base_hp,
                    base_def = EXCLUDED.base_def, base_crit = EXCLUDED.base_crit,
                    base_crit_dmg = EXCLUDED.base_crit_dmg, skill_id = EXCLUDED.skill_id,
                    skill_tree_group_id = EXCLUDED.skill_tree_group_id,
                    resonant_chain_group_id = EXCLUDED.resonant_chain_group_id,
                    data_json = EXCLUDED.data_json, updated_at = now()
                """,
                {**rec, "data_json": json.dumps(rec, ensure_ascii=False)},
            )
            n += 1
    conn.commit()
    return n
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/datamine/test_normalize.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: 커밋**

```bash
git add backend/src/datamine/normalize.py backend/tests/datamine/test_normalize.py
git commit -m "feat(datamine): L3 sim_character w/ Hiyuki base-stat validation"
```

---

## Task 6: 오케스트레이션 CLI + `refresh_state`

**Files:**
- Create: `backend/src/datamine/ingest.py`
- Create: `backend/scripts/run_datamine_ingest.py`
- Test: `backend/tests/datamine/test_ingest_cli.py`

**Interfaces:**
- Consumes: `init_datamine_schema`(Task 1), `ingest_bindata`(Task 2), `ingest_textmap`(Task 3), `build_sim_role_growth`(Task 4), `build_sim_character`(Task 5), `get_connection`, `refresh_state` 테이블(기존 init_db).
- Produces: `run_ingest() -> dict` — 스키마 보장 → L1(bindata, textmap) → L3(role_growth, characters) 순차 실행, `refresh_state`에 `source='datamine'` upsert. 반환 = 카운트 dict(`bindata_rows`, `textmap_rows`, `role_growth`, `characters`).

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/datamine/test_ingest_cli.py`:

```python
from __future__ import annotations

from src.datamine.ingest import run_ingest


def test_run_ingest_counts(conn):
    counts = run_ingest()
    assert counts == {
        "bindata_rows": 6,
        "textmap_rows": 2,
        "role_growth": 2,
        "characters": 1,
    }


def test_run_ingest_records_refresh_state(conn):
    run_ingest()
    with conn.cursor() as cur:
        cur.execute("SELECT status FROM refresh_state WHERE source = 'datamine'")
        row = cur.fetchone()
    assert row is not None
    assert row["status"] == "ok"
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/datamine/test_ingest_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.datamine.ingest'`.

- [ ] **Step 3: 최소 구현**

`backend/src/datamine/ingest.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone

from ..database import get_connection
from .bindata import ingest_bindata
from .normalize import build_sim_character, build_sim_role_growth
from .schema import init_datamine_schema
from .textmap import ingest_textmap


def run_ingest() -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            init_datamine_schema(cur)
        conn.commit()
        counts = {
            "bindata_rows": ingest_bindata(conn),
            "textmap_rows": ingest_textmap(conn),
            "role_growth": build_sim_role_growth(conn),
            "characters": build_sim_character(conn),
        }
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO refresh_state (source, refreshed_at, status, message)
                VALUES ('datamine', %s, 'ok', %s)
                ON CONFLICT (source) DO UPDATE SET
                    refreshed_at = EXCLUDED.refreshed_at,
                    status = EXCLUDED.status,
                    message = EXCLUDED.message
                """,
                (datetime.now(timezone.utc).isoformat(), str(counts)),
            )
        conn.commit()
    return counts


if __name__ == "__main__":
    print(run_ingest())
```

`backend/scripts/run_datamine_ingest.py`:

```python
"""Ingest the local datamine (WutheringWaves_Data-3.5) into Postgres.

Usage:
    uv run python scripts/run_datamine_ingest.py

Runs against whatever DATABASE_URL points at (use the _dev DB locally). Reads
the datamine root from DATAMINE_ROOT env or the repo's WutheringWaves_Data-3.5/.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.datamine.ingest import run_ingest  # noqa: E402


def main() -> None:
    print(run_ingest())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/datamine/test_ingest_cli.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: 전체 스위트 회귀 확인**

Run: `cd backend && uv run pytest tests/datamine -v` 후 `cd backend && uv run pytest -q`
Expected: datamine 전 테스트 PASS, 기존 스위트 회귀 없음.

- [ ] **Step 6: 커밋**

```bash
git add backend/src/datamine/ingest.py backend/scripts/run_datamine_ingest.py backend/tests/datamine/test_ingest_cli.py
git commit -m "feat(datamine): ingest orchestrator CLI + refresh_state"
```

---

## 실 데이터 적재 (유저 수행)

전 테스트 통과 후, 유저가 실 datamine을 dev DB에 적재해 검증:

```bash
cd backend
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/wuwa_ai_coach_dev uv run python scripts/run_datamine_ingest.py
```

기대: `characters`가 실제 플레이어블 수(≈56)와 근접, `bindata_rows`가 수십만 규모, `textmap_rows`가 13개 언어 합계. 이상치(캐릭 수 과다/과소)면 `_is_playable` 필터를 로그로 점검.

---

## Self-Review

**Spec coverage (스펙 §4·§6 대비):**
- L1 원본 전량 → Task 2(BinData) + Task 3(Textmap). ✓ ("datamine 전량 DB 적재" 충족: 모든 BinData/Textmap 파일 제네릭 적재.)
- L2 텍스트 해석 → Task 3 `resolve_text`. ✓
- L3 정규화 슬라이스 → Task 4(`sim_role_growth`) + Task 5(`sim_character`). ✓ (엔진 B의 캐릭 스탯 재구성 입력.)
- 멱등·재실행(패치 갱신) → 파일당 DELETE+INSERT, upsert. Task 2 `test_ingest_bindata_is_idempotent`. ✓
- 히유키 검증(462.5, base 스탯) → Task 5 두 테스트. ✓
- `refresh_state` 버전 태깅/CLI → Task 6. ✓
- **범위 밖(스펙 §6 명시)**: `sim_skill`/`sim_weapon`/`sim_echo`/`sim_buff`(L3 전투 상세)와 `sim_enemy_def`는 이 계획에 없음 — build.ts 오라클이 적방을 레벨식(792+8·L)으로 처리하므로 B 착수에 불필요. **후속 계획(A2: L3 전투 상세)**로 분리. 엔진 B의 공식 패리티(고정 벡터)는 이 계획 산출물과 무관하게 병행 가능.

**Placeholder scan:** TBD/TODO/"적절히 처리" 없음. 모든 스텝에 실제 코드·정확 경로·기대 출력 포함. ✓

**Type consistency:** `ingest_bindata(conn, root=None)→int`, `ingest_textmap(conn, root=None)→int`, `resolve_text(conn, lang, key)→str|None`, `build_sim_role_growth(conn)→int`, `build_sim_character(conn)→int`, `run_ingest()→dict` — Task 6에서 호출하는 시그니처와 정의부 일치. 테이블/컬럼명(`sim_role_growth.atk_ratio`, `sim_character.base_crit` 등) Task 1 DDL과 후속 INSERT/SELECT 일치. ✓

**주의(구현자용):**
- psycopg3는 JSONB를 파이썬 dict로 자동 역직렬화 → `_bindata_rows`의 `r["data"]`는 dict. `get_connection`이 `dict_row`라 `row["col"]` 접근.
- `element_ko`는 build.ts 어휘(`응결`…)로 저장(Global Constraints). i18n의 "냉응"과 다름은 의도됨.
- 실 datamine 1980개 파일은 단일 트랜잭션 대량 적재 — dev DB 기준 수 초~수십 초. 테스트는 픽스처(6행)라 즉시.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-09-datamine-db-ingestion.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — 태스크당 신선한 서브에이전트 디스패치, 태스크 간 2단계 리뷰, 빠른 반복.

**2. Inline Execution** — 이 세션에서 executing-plans로 배치 실행 + 체크포인트 리뷰.

**Which approach?**
