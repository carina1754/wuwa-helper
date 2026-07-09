# DPS/팀 시뮬레이터 엔진 — 설계 (재정의판)

- 작성일: 2026-07-09 (재작성)
- 상태: 설계 승인 대기
- 성격: **엄브렐라 설계** — 하위 4개 서브프로젝트로 분해. 각 서브프로젝트는 이 문서를 공유 설계로 삼고 개별 구현계획(plan)을 가진다.

---

## 1. 개요 & 차별점

WuWa용 자체 DPS/팀 시뮬레이터를 만든다(phro.love 대항).

**차별점**: phro는 "디폴트 에코옵션 가정"으로 조합 간 **상대 비교**만 한다. 우리는 **유저 실계정 에코 실측(OCR `CharacterSnapshot`)**을 입력으로 "내 실제 빌드 기준 **절대 딜**"을 계산한다. 이게 제품의 헤드라인.

---

## 2. 핵심 발견 — 엔진은 이미 절반 존재한다

`frontend/src/lib/build.ts`(408행)는 **이미 완성된 클라이언트 사이드 데미지 엔진**이다(자체 주석: "phro.love 공식"). 포함:

- `defMultiplier` = `(800 + 8·myLv) / (800 + 8·myLv + (792 + 8·enemyLv)·(1−ignore)·(1−reduce))` — 이전 세션에서 phro 역산으로 "락"했던 방어감쇄식(C=1520@Lv90, 적DEF=1512)이 **이미 여기 하드코딩**돼 있음.
- `skillDamage(...)` = 배율 × ATK × 크릿 × 피해보너스 × (1+부스트) × RES × DEF × (1+받는피해) × (1+총피해) + 고정딜 — 락된 8항 곱과 동일 구조.
- `computeStats(reso, weapon, build, config, extra)` — base(스탯커브)+무기+에코서브+세트+트리 → 최종 ATK/HP/DEF/치확/치피/증뎀%. **에코 실측 서브스탯(`e.subs`)을 그대로 받음 → 실계정 절대딜이 이미 원리상 가능**.
- `resMultiplier`(과관통 반감), `weaponBuffs`(무기 패시브 always/conditional/boost 파싱), `activeSetBonuses`(소나타 2/5pc), `anomalyDamage`(이상), `tuneBreakDamage`(공진해제).

**결론**: 이전 스펙의 "제로에서 솔로 딜 엔진 구축(v0/v1)"은 **사실상 이미 구현돼 있음**. 다시 만들지 않는다. build.ts를 **① 이식 검증 기준(oracle)** 이자 **② 재정의된 스코프의 출발점**으로 삼는다.

**진짜 남은 가치(build.ts에 없는 것)**:
1. **로테이션** — 캐스팅 시퀀스 → 시간당 DPS(build.ts는 1타 딜만).
2. **팀 버프 시너지** — 버퍼→딜러 버프 전파(build.ts/partyDamage는 각 캐릭 독립).
3. **실계정 절대딜 배선** — OCR `CharacterSnapshot` → 엔진 → "내 빌드 딜" 리포트.
4. **datamine → DB + RAG 기반** — 데이터 소스를 encore에서 게임 원본으로 교체, 전량 DB 적재.

---

## 3. 아키텍처 결정 — 엔진은 백엔드 정규(canonical)

**결정: 정규 엔진은 백엔드(Python `backend/src/sim/`)에 둔다.** build.ts는 검증 기준 + 당분간 프론트 프리뷰로 유지하다 API 패리티 확인 후 은퇴.

**근거**:
- datamine DB·RAG·AI 코치(로컬 llama-server)가 전부 백엔드 → 엔진이 거기 있어야 딜 계산을 직접 호출·한 몸으로 운용.
- 공식이 **한 곳에만** 존재해야 드리프트가 없다(지금은 TS에만 있어 백엔드가 딜을 못 냄).
- 무거운 계산(로테이션, 팀 시뮬, 전 빌드 스윕)은 서버가 적합.
- pytest 골든 스위트가 이미 백엔드에 있음(`backend/tests/`).

**프론트 상호작용(슬라이더 즉석 계산) 처리**: 빌더는 백엔드 `/sim/*` API를 **디바운스 호출**. 초기엔 build.ts를 클라이언트 프리뷰로 병행하되 백엔드를 authoritative로 취급, API 패리티가 증명되면 build.ts 제거. (서브프로젝트 D에서 이관.)

---

## 4. 데이터 전략 — datamine → DB (3-레이어), 전량 적재

데이터 소스를 encore에서 **게임 원본 datamine**(`WutheringWaves_Data-3.5/`, game 3.5.0)으로 교체. 유저가 매 패치 datamine·이미지를 직접 갱신(encore 내구성/이미지 파이프라인 우려 해소됨).

**"datamine에 있는 데이터를 모두 DB에 올린다"** — 원본을 파일로 직접 읽으면 RAG 구성이 어려우므로 전량 DB 적재. 3-레이어:

- **L1 원본 전량(RAG 소스)**: `BinData/**/*.json`(≈486 테이블) → `datamine_bindata(table_name, row_id, data jsonb)`; `Textmaps/*`(13개 언어) → `datamine_textmap(lang, text_id, text)`. 가공 없이 그대로. RAG·향후 확장의 원천.
- **L2 텍스트 해석**: L1 BinData의 숫자 text_id를 L2 textmap으로 조인 → 한글 이름/설명 해석. (L2는 L1의 일부지만 조인 경로로서 명시.)
- **L3 정규화 전투 슬라이스(엔진 입력)**: L1에서 파생한 목적형 테이블 — `sim_character`(base 스탯+성장커브+엘리먼트+무기타입), `sim_skill`(RateLv 배열·스케일스탯·엘리먼트·FormulaType), `sim_weapon`(base+부옵 커브·패시브), `sim_echo`/`sim_sonata`, `sim_enemy_def`(레벨별 방어 커브), `sim_buff`(버프 값+의미). 엔진은 **L3만** 읽는다.

**인제스천**: `backend/src/datamine/ingest.py`가 파일 순회→L1/L2 upsert, `datamine/normalize.py`가 L1→L3 빌드. 멱등·재실행 가능(패치 갱신 대응).

**검증된 원본 기반**(2026-07-09 실사):
- `property/baseproperty.json`: Lv1 base(히유키 1108 = Atk37/Crit500/CritDamage15000/Def91) — 캐릭+몹.
- `property/rolepropertygrowth.json`: Level×BreachLevel 비율(Lv90/돌파6 AtkRatio=125000). 실증: 히유키 Atk37×12.5=462.5 ≒ phro 463.
- `property/monsterpropertygrowth.json`: 적 레벨별 방어 커브(추측 적방 대체).
- `property/propertyindex.json`: 스탯 Id(Atk=7, Crit=8, CritDamage=9, Def=10, LifeMax=2).
- `damage/damage.json`(9706행): RateLv(20레벨)·RelatedProperty(스케일)·Element·FormulaType. **FormulaType0=93.5%·ATK스케일=95.8%** → 코어 공식 하나로 사실상 전부 커버, 특수 FT는 소수 꼬리로 별도 처리.
- 산술 상수(감쇄식/저항 piecewise/크릿결합)는 **JSON에 없음**(게임 블루프린트 코드). → 공식은 build.ts/phro 락값에서 가져오고, datamine은 **입력 수치**(배율·스탯·커브)를 공급.

---

## 5. 서브프로젝트 분해

| # | 이름 | 산출물 | 의존 |
|---|------|--------|------|
| **A** | datamine → DB 인제스천 | L1/L2/L3 테이블 + ingest/normalize 스크립트 | — |
| **B** | 백엔드 엔진 `sim/` | build.ts 이식·검증된 Python 데미지 엔진 | A(실데이터), 단 검증은 A 무관 |
| **C** | 로테이션 + 팀 버프 | 시간당 DPS, 버퍼→딜러 전파 | B, A의 `sim_buff` |
| **D** | 실계정 절대딜 + API/프론트 | `CharacterSnapshot`→딜 리포트, `/sim/*`, 프론트 이관 | B(+C) |

**순서**: A + B 병행 → C → D. (B의 **공식 정확성 검증**은 고정 테스트 벡터로 build.ts와 대조하므로 A와 무관하게 진행 가능. B의 **실데이터 구동**만 A를 기다림.)

---

## 6. 서브프로젝트 A — datamine → DB 인제스천

**목표**: 게임 원본 전량을 DB에 재실행 가능하게 적재하고, 엔진용 정규 슬라이스(L3)를 파생.

**구성** (`backend/src/datamine/`):
- `ingest.py`: `WutheringWaves_Data-3.5/BinData/**/*.json` → `datamine_bindata` upsert; `Textmaps/*` → `datamine_textmap` upsert. 파일→테이블명 매핑, 멱등(PK 충돌 시 갱신).
- `normalize.py`: L1을 조인·해석해 L3(`sim_*`) 빌드. build.ts `computeStats`/`skillDamage`가 기대하는 필드 형태에 맞춤(§7과 계약).
- `schema.sql`(또는 마이그레이션): L1/L2/L3 테이블 정의. `patch` 컬럼으로 버전 태깅.
- CLI 엔트리: `python -m src.datamine.ingest`(전량), `--layer3-only`(재파생).

**L3 계약(엔진이 읽는 최소 필드)** — plan에서 컬럼 확정, 여기선 형태만:
- `sim_character`: id, name_ko, rarity, element, weapon_type, base(atk/hp/def/crit/crit_dmg), growth_curve.
- `sim_skill`: char_id, name_ko, type(평/공/E/Q/인트로/아웃트로), element, rate_lv(배열), related_property(스케일 스탯), energy, formula_type.
- `sim_weapon`: id, type, base_atk_curve, sub_stat/sub_curve, passive_desc, passive_params.
- `sim_echo`/`sim_sonata`: cost/grade/main·sub 후보, 2/5pc 효과.
- `sim_enemy_def`: level→def(커브), 기본 적 파라미터.
- `sim_buff`: buff_id, 값(정형), 의미(대상/스탯/조건/지속) — **의미 바인딩은 C에서 LLM 파싱**(A는 값+원문까지만).

**검증**: 히유키(1108) L3 재구성값이 §2 실증(base 462.5, 최종ATK 2630 경로)과 일치하는 스모크 테스트. 전 캐릭 L3 적재 시 크래시/NaN/누락 없음.

**비범위**: 버프 의미 바인딩(C), 프론트 codex/builder의 encore→datamine 이관(후속, §11).

---

## 7. 서브프로젝트 B — 백엔드 엔진 `backend/src/sim/`

**목표**: build.ts의 검증된 데미지 로직을 Python으로 이식, **수치 패리티로 검증**, L3 데이터로 구동.

**모듈** (단일 책임 순수함수 위주):
- `formula.py`: 락된 8항 곱. `def_multiplier`, `res_multiplier`(과관통 반감), `crit_multiplier`(§10 규약 확정 대상), `hit_damage(...)`. 순수함수.
- `stats.py`: `reconstruct(...)` — base(성장커브)+무기+에코서브+세트+트리 → 최종 스탯. build.ts `computeStats`의 이식.
- `data.py`: L3(`sim_*`)에서 캐릭/스킬/무기/에코/적방 로드. **encore 아님.**
- `enemy.py`: 적 스펙(레벨/방어/저항/취약), 기본값 phro/커뮤 표준(적DEF=1512@Lv90, RES 0.8, 취약 0).
- `weapon.py`/`sets.py`: `weapon_buffs`, `active_set_bonuses` 이식.
- `anomaly.py`: 이상 딜, 공진해제(`tune_break`) 이식.
- `engine.py`: `BuildSpec` → `reconstruct` → 스킬 로드 → `hit_damage` 반복 → `DpsResult`.
- `models.py`: `BuildSpec`(캐릭/레벨/무기/에코5), `WeaponSpec`, `EchoSpec`(실측 subs), `EnemySpec`, `HitResult`, `DpsResult`(스킬별 딜/총딜/최종스탯).

**데이터 소스 매핑**: build.ts는 encore 형태(`reso.stat_curves`, `skills[].damage[].rates`)를 읽음. `data.py`는 L3를 **동일 의미 필드**로 노출해 `stats/formula`가 소스 불문 동작하게 함(§6 L3 계약).

**검증**: §10.

**비범위**: 로테이션 시간축(C), 팀 버프 전파(C), API/프론트(D).

---

## 8. 서브프로젝트 C — 로테이션 + 팀 버프

**로테이션**(`sim/rotation.py`): 캐릭별 캐스팅 시퀀스(우선순위 메타) + 스킬 시전시간/쿨/에너지 → 시간당 총딜·DPS. 초기엔 대표 캐릭 하드코딩 시퀀스, 이후 일반화.

**팀 버프 시너지**: 3슬롯 파티에서 버퍼 스킬 버프(공%/증뎀/치피/저항감소 등)를 딜러 `reconstruct`의 버프 버킷에 **전파**. 지금 partyDamage/computeStats는 캐릭 독립(=phro 방식) → 여기서 상호 전파 도입. **버프 의미 바인딩**(대상/스탯/조건/지속)은 A의 `sim_buff` 원문을 로컬 llama-server로 1회 파싱·캐싱(값은 이미 정형, LLM은 분류/바인딩만).

**검증**: 대표 3~5 조합의 총딜을 phro 조합 결과와 상대 순위 대조(절대값은 가정 차이로 ±, 순위·배수 경향 일치).

---

## 9. 서브프로젝트 D — 실계정 절대딜 + API/프론트

- **어댑터**: OCR `CharacterSnapshot`(실측 에코 subs/무기/레벨) → `BuildSpec`.
- **API**: `/sim/character`(단일 캐릭 절대딜 리포트), `/sim/team`(파티 DPS), `/sim/skill-sheet`(스킬별 1타 딜). AI 코치가 직접 호출.
- **프론트 이관**: `TeamBuilder`/빌더가 `/sim/*` 디바운스 호출로 전환. build.ts는 프리뷰로 병행하다 패리티 확인 후 제거.
- **차별점 실현**: "내 실제 빌드 기준 절대 딜" + AI 코치가 그 수치로 개선 조언.

---

## 10. 오라클 & 검증 전략

- **1차 오라클 = build.ts 수치 패리티**: 동일 입력(고정 테스트 벡터: base 스탯/무기 커브/에코 subs/배율)을 build.ts와 Python `sim`에 넣어 **최종 스탯·1타 딜이 일치**(±0.5%)하는지 대조. 공식 구조 검증은 데이터 소스와 무관.
- **2차 교차검증 = phro 히유키**: `TOTAL_DAMAGE 515,112 / DPS 42,926 / 히트01 11,455` 재현(±0.5%).
- **⚠ 크릿 규약 재조정(유일한 알려진 불일치)**: build.ts = `1 + 치확×(치피−1)`(표준 기댓값, WuWa 치피 150%=×1.5 해석). phro REPORT = `1 + 치확×치피`(히트01 1+0.709×2.012=2.427). **동일 치피 표기에서 결과가 다름** → 두 오라클이 크릿에서만 어긋남. **인게임 훈련장 1방**(실측 딜 vs 표기 치확/치피)으로 확정. 확정 전까지 규약을 파라미터화하고 build.ts 기본값(표준 EV) 채택.
- **회귀 게이트**: A로 데이터 소스를 datamine으로 바꾼 뒤에도 위 골든이 유지되는지 확인(데이터 교체가 공식을 깨지 않음).
- pytest 편입: `backend/tests/sim/`(formula 유닛, golden_hiyuki, parity_buildts, all_chars_smoke).

---

## 11. 미해결 / 리스크

- **크릿 규약**(§10) — 인게임 1방으로 확정.
- **버프 의미 바인딩 정확도** — LLM 파싱 품질 spot 검증 필요(C).
- **FormulaType 디코드** — FT0/ATK스케일이 95%+ 커버, 특수 FT(HP/DEF 스케일·이상 특수)는 소수 꼬리로 개별 처리.
- **build.ts↔L3 필드 매핑** — encore 형태 가정을 L3가 정확히 재현해야 함(§6 계약이 실패점).
- **프론트 이관 지연/레이턴시** — 디바운스+프리뷰로 완화(D).
- **프론트 codex/builder의 encore 의존** — 당장 유지, datamine 이관은 엔진이 datamine 검증을 통과한 뒤 별도 후속.

---

## 12. 진행 순서 & 다음 단계

1. 이 엄브렐라 스펙 유저 리뷰·승인.
2. **writing-plans → 서브프로젝트 A**(datamine → DB) 구현계획 작성 → 구현.
3. B(엔진 이식·검증)의 **공식 패리티 작업은 A와 무관하게 병행 가능**(고정 벡터로 build.ts 대조). B의 실데이터 구동만 A 완료를 기다림.
4. 이어서 C(로테/팀버프) → D(실계정·API·프론트). 각 단계 진입 시 필요하면 미니 설계 보강.

> 실 테스트는 유저가 수행(빌드+보고는 이쪽). 커밋/푸시는 유저 명시 요청 시에만.
