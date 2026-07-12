"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useLanguage, type Language } from "@/lib/i18n";

/** **bold** 마커를 <b>로 렌더. 나머지는 그대로. */
function RT({ s }: { s: string }) {
  const parts = s.split(/\*\*(.+?)\*\*/g);
  return (
    <>
      {parts.map((p, i) =>
        i % 2 === 1 ? (
          <b key={i} className="text-[var(--fg)]">
            {p}
          </b>
        ) : (
          <span key={i}>{p}</span>
        ),
      )}
    </>
  );
}

type Shot = { src: string; alt: string; caption: string };

function ShotFig({ shot }: { shot: Shot }) {
  return (
    <figure className="my-4">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={shot.src} alt={shot.alt} loading="lazy" className="w-full rounded-lg border border-[var(--line)] bg-[var(--surface)]" />
      {shot.caption ? <figcaption className="mt-1.5 text-center text-xs text-[var(--muted)]">{shot.caption}</figcaption> : null}
    </figure>
  );
}

function Step({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <div className="mt-6">
      <h3 className="flex items-center gap-2 text-base font-semibold text-[var(--fg)]">
        <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[var(--accent)] text-xs font-bold text-[var(--accent-ink)]">{n}</span>
        {title}
      </h3>
      <div className="mt-2 text-sm leading-relaxed text-[var(--fg-soft)]">{children}</div>
    </div>
  );
}

function Tip({ children }: { children: ReactNode }) {
  return (
    <div className="my-3 rounded-md border border-[var(--line-2)] bg-[var(--surface-2)] px-3 py-2.5 text-[13px] leading-relaxed text-[var(--fg-soft)]">
      <span className="mr-1 font-semibold text-[var(--accent)]">TIP</span>
      {children}
    </div>
  );
}

type Copy = {
  backToApp: string;
  headline: string;
  intro: string;
  toc: { id: string; label: string }[];
  start: { h2: string; p: string; shot: Shot; tip: string };
  codex: { h2: string; p1: string; shot1: Shot; p2: string; shot2: Shot };
  pickup: { h2: string; p: string; shot: Shot };
  party: {
    h2: string;
    p: string;
    shot: Shot;
    step1: { title: string; body: string; shots: Shot[] };
    step2: { title: string; body: string; shot: Shot; tip: string };
    step3: { title: string; body1: string; shot: Shot; body2: string; tip: string };
    step4: { title: string; body: string; shot: Shot; list: string[] };
    tip: string;
  };
  ai: { h2: string; p: string; shot: Shot };
  notice: { h2: string; p: string; shot: Shot };
  footerAskPre: string;
  discordLabel: string;
  footerAskPost: string;
  disclaimer: string;
};

const ko: Copy = {
  backToApp: "앱으로 돌아가기",
  headline: "이용 가이드",
  intro:
    "명조: 워더링 웨이브의 캐릭터 도감 · 픽업 일정 · 파티 딜 계산 · AI 빌드 추천을 제공하는 비공식 팬 도구입니다. 아래 순서대로 따라 하면 처음 방문해도 모든 기능을 바로 사용할 수 있습니다.",
  toc: [
    { id: "start", label: "시작하기" },
    { id: "codex", label: "도감" },
    { id: "pickup", label: "픽업 일정표" },
    { id: "party", label: "파티 딜 계산" },
    { id: "ai", label: "AI 빌딩" },
    { id: "notice", label: "공지사항" },
  ],
  start: {
    h2: "1. 시작하기",
    p: "첫 화면에는 **명조 업데이트** 탭이 열려 있고, 상단에서 **AI · 도감 · 픽업 일정표 · 명조 업데이트 · 파티 · 기록** 탭을 오갈 수 있습니다. 오른쪽 위 아이콘은 순서대로 디스코드 참여, 라이트/다크 테마 전환, 공지사항, 구글 로그인입니다.",
    shot: { src: "/guide/01-home.png", alt: "홈 화면 — 명조 업데이트 탭", caption: "첫 화면(명조 업데이트) — 상단 탭과 우측 상단 아이콘" },
    tip: "대부분의 기능은 로그인 없이 사용할 수 있습니다. 구글 로그인은 AI 빌드 추천과 기록 저장에만 필요합니다.",
  },
  codex: {
    h2: "2. 도감 — 캐릭터·무기·에코 정보",
    p1: "**도감** 탭에서 캐릭터/무기/에코를 검색·필터링할 수 있습니다. 속성이나 무기 타입으로 좁혀 보고, 이름 검색도 지원합니다.",
    shot1: { src: "/guide/02-codex.png", alt: "도감 — 캐릭터 그리드", caption: "도감 탭 — 캐릭터·무기·에코 서브탭과 검색/필터" },
    p2: "카드를 클릭하면 상세 창이 열립니다. 스킬별 설명과 **레벨별 실제 배율(%)**까지 확인할 수 있어 딜 계산의 근거를 그대로 볼 수 있습니다.",
    shot2: { src: "/guide/03-codex-detail.png", alt: "도감 상세 — 스킬 배율", caption: "캐릭터 상세 — 스킬 설명과 배율(레벨 슬라이더로 조절)" },
  },
  pickup: {
    h2: "3. 픽업 일정표",
    p: "버전별 픽업 배너 일정을 한눈에 볼 수 있습니다. 카드를 클릭하면 해당 캐릭터/무기의 상세 정보가 열립니다.",
    shot: { src: "/guide/04-pickup.png", alt: "픽업 일정표", caption: "픽업 일정표 — 버전별 배너 일정" },
  },
  party: {
    h2: "4. 파티 딜 계산 — 핵심 기능",
    p: "**파티** 탭에서 공명자 3명을 편성하면 서버 엔진이 파티 전체 피해(1사이클)와 각자의 기여도를 계산합니다. 각 캐릭터가 파티에 주는 공유 버프는 **자동으로 반영**되므로 편성만 하면 됩니다.",
    shot: { src: "/guide/05-party-empty.png", alt: "파티 탭 초기 화면", caption: "파티 탭 — 슬롯 3개, 적 조건, 팀 공유 버프, 계산 버튼" },
    step1: {
      title: "공명자 추가",
      body: "빈 슬롯의 **공명자 추가**를 누르고 검색해서 선택합니다. 3명을 채우면 계산 버튼이 활성화됩니다.",
      shots: [
        { src: "/guide/06-party-picker.png", alt: "공명자 선택 모달", caption: "공명자 검색 — 이름 일부만 입력해도 찾아집니다" },
        { src: "/guide/07-party-filled.png", alt: "3인 편성 완료", caption: "3인 편성 완료 — 카드마다 기본 스탯이 표시됩니다" },
      ],
    },
    step2: {
      title: "빌드 편집 (선택)",
      body: "각 카드의 **빌드 편집**에서 캐릭터 레벨, 스킬 레벨(기본 Lv.10), **공명 사슬(S0~S6)**, 무기(레벨·정제), 에코 5개(메인/부가 옵션)를 설정할 수 있습니다. 설정하지 않아도 기본값으로 계산됩니다.",
      shot: { src: "/guide/08-build-editor.png", alt: "빌드 편집기", caption: "빌드 편집 — 레벨·스킬·공명 사슬·무기·에코·최종 스탯" },
      tip: "공명 사슬 단계를 올리면 해당 시퀀스의 피해 증가 효과가 딜 계산에 실제로 반영됩니다. 상위 시퀀스에서 딜이 크게 오르는 캐릭터를 비교해 보세요.",
    },
    step3: {
      title: "적 조건과 풀 업타임",
      body1: "적 레벨·저항, 방어 무시/감소, 부스트, 피해증가를 조절할 수 있습니다. 파티에 암흑(인멸) 캐릭터가 있으면 적 방어 감소가 자동 적용됩니다.",
      shot: { src: "/guide/09-conditions.png", alt: "적 조건과 풀 업타임", caption: "적 조건 — 풀 업타임 체크박스(기본 켜짐)와 팀 공유 버프 수동 입력" },
      body2: "**풀 업타임**이 켜져 있으면(기본) 공명 사슬·무기·특성의 조건부 버프를 이상적인 로테이션 기준으로 모두 반영해 최대 딜에 가깝게 계산합니다. 끄면 상시 발동 버프만 반영한 보수적인 수치를 보여줍니다.",
      tip: "다른 딜 계산기와 수치를 비교할 때는 풀 업타임을 켠 상태(기본)가 일반적인 기준입니다.",
    },
    step4: {
      title: "계산과 결과 해석",
      body: "**서버 엔진으로 계산**을 누르면 결과가 표시됩니다.",
      shot: { src: "/guide/10-party-result.png", alt: "계산 결과", caption: "결과 — 팀 총 피해, 기여도 순위, 스킬별 피해, 자동 적용 팀 버프" },
      list: [
        "**팀 총 피해 (1사이클)** — 파티 전체의 한 로테이션 피해 합계입니다.",
        "**기여도 순위** — 멤버별 피해량과 점유율(%)을 막대로 보여줍니다.",
        "**스킬별 피해** — 기본 공격·공명 스킬·해방 등 스킬 단위 피해를 확인할 수 있습니다.",
        "**자동 적용 팀 버프** — 파티원이 서로 주고받은 버프가 칩으로 표시됩니다. 수동 입력이 필요 없습니다.",
        "**상황부 참고값** — 이상 피해·조화도 파괴 등은 총합에 넣지 않고 별도로 표기합니다.",
      ],
    },
    tip: "공명자 3명을 모두 채우면 하단 **AI 파티 분석**으로 구성 평가를 받아 기록에 저장할 수도 있습니다(구글 로그인 필요).",
  },
  ai: {
    h2: "5. AI 빌딩 — 대화형 빌드 추천",
    p: "**AI** 탭에서 보유 캐릭터와 목표(예: 무과금, 심층 클리어)를 입력하면 AI가 빌드와 파티를 추천합니다. 추천 결과는 **기록** 탭에 저장되어 언제든 다시 볼 수 있습니다. 이 기능은 구글 로그인 후 이용할 수 있습니다.",
    shot: { src: "/guide/12-ai.png", alt: "AI 탭", caption: "AI 빌딩 — 구글 로그인 후 이용" },
  },
  notice: {
    h2: "6. 공지사항 — 사이트 업데이트 내역",
    p: "우측 상단의 확성기 아이콘을 누르면 사이트 업데이트 내역(버전별 변경사항)을 볼 수 있습니다. 새 기능이 추가되면 이곳에서 먼저 안내합니다.",
    shot: { src: "/guide/13-site-updates.png", alt: "공지사항", caption: "공지사항 — 버전별 업데이트 내역" },
  },
  footerAskPre: "더 궁금한 점은 ",
  discordLabel: "디스코드",
  footerAskPost: "에서 물어봐 주세요.",
  disclaimer: "Wuthering Waves / Kuro Games와 무관한 비공식 팬 도구입니다.",
};

const en: Copy = {
  backToApp: "Back to app",
  headline: "User Guide",
  intro:
    "An unofficial fan tool for Wuthering Waves offering a character Codex, banner schedule, party damage calculation, and AI build recommendations. Follow the steps below and you can use every feature right away, even on your first visit.",
  toc: [
    { id: "start", label: "Getting started" },
    { id: "codex", label: "Codex" },
    { id: "pickup", label: "Banner schedule" },
    { id: "party", label: "Party damage" },
    { id: "ai", label: "AI building" },
    { id: "notice", label: "Announcements" },
  ],
  start: {
    h2: "1. Getting started",
    p: "The home screen opens on the **WuWa updates** tab, and the top bar lets you switch between **AI · Codex · Banner schedule · WuWa updates · Party · History**. The icons at the top right are, in order: join Discord, light/dark theme toggle, announcements, and Google sign-in.",
    shot: { src: "/guide/01-home.png", alt: "Home screen — WuWa updates tab", caption: "Home screen (WuWa updates) — top tabs and top-right icons" },
    tip: "Most features work without signing in. Google sign-in is only required for AI build recommendations and saving history.",
  },
  codex: {
    h2: "2. Codex — character, weapon & echo info",
    p1: "The **Codex** tab lets you search and filter characters/weapons/echoes. Narrow down by element or weapon type, and search by name too.",
    shot1: { src: "/guide/02-codex.png", alt: "Codex — character grid", caption: "Codex tab — character/weapon/echo sub-tabs with search & filters" },
    p2: "Click a card to open its detail panel. You can see per-skill descriptions and even the **actual multipliers (%) by level**, so you see exactly what the damage calculation is based on.",
    shot2: { src: "/guide/03-codex-detail.png", alt: "Codex detail — skill multipliers", caption: "Character detail — skill descriptions and multipliers (adjust with the level slider)" },
  },
  pickup: {
    h2: "3. Banner schedule",
    p: "See the pickup banner schedule for each version at a glance. Click a card to open the detail for that character/weapon.",
    shot: { src: "/guide/04-pickup.png", alt: "Banner schedule", caption: "Banner schedule — pickup banners by version" },
  },
  party: {
    h2: "4. Party damage — the core feature",
    p: "In the **Party** tab, build a team of 3 Resonators and the server engine calculates the whole party's damage (1 cycle) plus each member's contribution. The shared buffs each character grants the party are **applied automatically**, so you only need to build the team.",
    shot: { src: "/guide/05-party-empty.png", alt: "Party tab initial screen", caption: "Party tab — 3 slots, enemy conditions, team shared buffs, calculate button" },
    step1: {
      title: "Add Resonators",
      body: "Press **Add Resonator** on an empty slot, then search and select. Once all 3 are filled, the calculate button becomes active.",
      shots: [
        { src: "/guide/06-party-picker.png", alt: "Resonator picker modal", caption: "Resonator search — even a partial name finds them" },
        { src: "/guide/07-party-filled.png", alt: "Team of 3 completed", caption: "Team of 3 completed — base stats show on each card" },
      ],
    },
    step2: {
      title: "Edit build (optional)",
      body: "In each card's **Edit build**, you can set character level, skill levels (default Lv.10), **Resonance chain (S0–S6)**, weapon (level & refinement), and 5 echoes (main/sub stats). It still calculates with defaults if you leave them alone.",
      shot: { src: "/guide/08-build-editor.png", alt: "Build editor", caption: "Edit build — level, skills, Resonance chain, weapon, echoes, final stats" },
      tip: "Raising the Resonance chain level actually applies that sequence's damage-boost effect to the calculation. Compare characters whose damage jumps sharply at higher sequences.",
    },
    step3: {
      title: "Enemy conditions and Full uptime",
      body1: "Adjust enemy level/resistance, DEF ignore/reduction, boosts, and DMG bonus. If the party includes a Havoc character, enemy DEF reduction is applied automatically.",
      shot: { src: "/guide/09-conditions.png", alt: "Enemy conditions and Full uptime", caption: "Enemy conditions — Full uptime checkbox (on by default) and manual team shared buffs" },
      body2: "When **Full uptime** is on (default), it applies the conditional buffs from Resonance chains, weapons, and traits based on an ideal rotation, giving a result close to maximum damage. Turn it off to see a conservative number that reflects only always-on buffs.",
      tip: "When comparing numbers against other damage calculators, Full uptime on (default) is the usual baseline.",
    },
    step4: {
      title: "Calculate and read the results",
      body: "Press **Calculate with server engine** to show the results.",
      shot: { src: "/guide/10-party-result.png", alt: "Calculation results", caption: "Results — team total damage, contribution ranking, per-skill damage, auto-applied team buffs" },
      list: [
        "**Team total damage (1 cycle)** — the sum of the whole party's damage over one rotation.",
        "**Contribution ranking** — each member's damage and share (%) shown as bars.",
        "**Per-skill damage** — check damage per skill: Basic Attack, Resonance Skill, Liberation, and more.",
        "**Auto-applied team buffs** — buffs members grant each other are shown as chips. No manual input needed.",
        "**Situational reference values** — aberration damage, harmony break, and the like are listed separately rather than added to the total.",
      ],
    },
    tip: "Once all 3 Resonators are filled, you can also get a composition review via **AI party analysis** at the bottom and save it to History (Google sign-in required).",
  },
  ai: {
    h2: "5. AI building — conversational build recommendations",
    p: "In the **AI** tab, enter the characters you own and your goal (e.g. F2P, endgame tower clears) and the AI recommends builds and parties. Recommendations are saved to the **History** tab so you can revisit them anytime. This feature requires Google sign-in.",
    shot: { src: "/guide/12-ai.png", alt: "AI tab", caption: "AI building — available after Google sign-in" },
  },
  notice: {
    h2: "6. Announcements — site update log",
    p: "Press the megaphone icon at the top right to see the site update log (changes by version). New features are announced here first.",
    shot: { src: "/guide/13-site-updates.png", alt: "Announcements", caption: "Announcements — update log by version" },
  },
  footerAskPre: "Have more questions? Ask us on ",
  discordLabel: "Discord",
  footerAskPost: ".",
  disclaimer: "An unofficial fan tool, not affiliated with Wuthering Waves / Kuro Games.",
};

const ja: Copy = {
  backToApp: "アプリに戻る",
  headline: "利用ガイド",
  intro:
    "鳴潮（Wuthering Waves）のキャラクター図鑑・ピックアップ日程・パーティダメージ計算・AIビルド提案を提供する非公式ファンツールです。以下の順に進めれば、初めての方でもすべての機能をすぐに使えます。",
  toc: [
    { id: "start", label: "はじめに" },
    { id: "codex", label: "図鑑" },
    { id: "pickup", label: "ピックアップ日程" },
    { id: "party", label: "パーティダメージ" },
    { id: "ai", label: "AIビルド" },
    { id: "notice", label: "お知らせ" },
  ],
  start: {
    h2: "1. はじめに",
    p: "最初の画面では **鳴潮アップデート** タブが開いており、上部から **AI・図鑑・ピックアップ日程・鳴潮アップデート・パーティ・履歴** を切り替えられます。右上のアイコンは順に、Discord参加、ライト/ダークテーマ切替、お知らせ、Googleログインです。",
    shot: { src: "/guide/01-home.png", alt: "ホーム画面 — 鳴潮アップデートタブ", caption: "最初の画面（鳴潮アップデート）— 上部タブと右上アイコン" },
    tip: "ほとんどの機能はログインなしで使えます。GoogleログインはAIビルド提案と履歴保存にのみ必要です。",
  },
  codex: {
    h2: "2. 図鑑 — キャラ・武器・エコー情報",
    p1: "**図鑑** タブでキャラ／武器／エコーを検索・絞り込みできます。属性や武器タイプで絞り込め、名前検索にも対応しています。",
    shot1: { src: "/guide/02-codex.png", alt: "図鑑 — キャラクター一覧", caption: "図鑑タブ — キャラ・武器・エコーのサブタブと検索/フィルター" },
    p2: "カードをクリックすると詳細が開きます。スキルごとの説明に加え、**レベル別の実際の倍率（%）** まで確認でき、ダメージ計算の根拠をそのまま見られます。",
    shot2: { src: "/guide/03-codex-detail.png", alt: "図鑑詳細 — スキル倍率", caption: "キャラ詳細 — スキル説明と倍率（レベルスライダーで調整）" },
  },
  pickup: {
    h2: "3. ピックアップ日程",
    p: "バージョンごとのピックアップバナー日程を一目で確認できます。カードをクリックすると、そのキャラ／武器の詳細が開きます。",
    shot: { src: "/guide/04-pickup.png", alt: "ピックアップ日程", caption: "ピックアップ日程 — バージョン別バナースケジュール" },
  },
  party: {
    h2: "4. パーティダメージ計算 — 中核機能",
    p: "**パーティ** タブで共鳴者3人を編成すると、サーバーエンジンがパーティ全体のダメージ（1サイクル）と各自の貢献度を計算します。各キャラがパーティに与える共有バフは **自動で反映** されるので、編成するだけでOKです。",
    shot: { src: "/guide/05-party-empty.png", alt: "パーティタブ初期画面", caption: "パーティタブ — スロット3つ、敵条件、チーム共有バフ、計算ボタン" },
    step1: {
      title: "共鳴者を追加",
      body: "空きスロットの **共鳴者を追加** を押し、検索して選択します。3人埋めると計算ボタンが有効になります。",
      shots: [
        { src: "/guide/06-party-picker.png", alt: "共鳴者選択モーダル", caption: "共鳴者検索 — 名前の一部だけでも見つかります" },
        { src: "/guide/07-party-filled.png", alt: "3人編成完了", caption: "3人編成完了 — カードごとに基礎ステータスを表示" },
      ],
    },
    step2: {
      title: "ビルド編集（任意）",
      body: "各カードの **ビルド編集** で、キャラレベル、スキルレベル（初期Lv.10）、**共鳴チェーン（S0〜S6）**、武器（レベル・精錬）、エコー5個（メイン/サブ効果）を設定できます。設定しなくても初期値で計算されます。",
      shot: { src: "/guide/08-build-editor.png", alt: "ビルドエディター", caption: "ビルド編集 — レベル・スキル・共鳴チェーン・武器・エコー・最終ステータス" },
      tip: "共鳴チェーンの段階を上げると、そのシーケンスのダメージ上昇効果が計算に実際に反映されます。上位シーケンスでダメージが大きく伸びるキャラを比較してみてください。",
    },
    step3: {
      title: "敵条件とフルアップタイム",
      body1: "敵レベル・耐性、防御無視/減少、ブースト、ダメージ増加を調整できます。パーティに消滅（湮滅）キャラがいると、敵の防御減少が自動で適用されます。",
      shot: { src: "/guide/09-conditions.png", alt: "敵条件とフルアップタイム", caption: "敵条件 — フルアップタイムのチェック（初期ON）とチーム共有バフの手動入力" },
      body2: "**フルアップタイム** がON（初期値）だと、共鳴チェーン・武器・特性の条件付きバフを理想的なローテーション基準ですべて反映し、最大ダメージに近い値で計算します。OFFにすると常時発動バフのみを反映した保守的な数値になります。",
      tip: "他のダメージ計算機と数値を比較する際は、フルアップタイムON（初期値）が一般的な基準です。",
    },
    step4: {
      title: "計算と結果の見方",
      body: "**サーバーエンジンで計算** を押すと結果が表示されます。",
      shot: { src: "/guide/10-party-result.png", alt: "計算結果", caption: "結果 — チーム総ダメージ、貢献度ランキング、スキル別ダメージ、自動適用のチームバフ" },
      list: [
        "**チーム総ダメージ（1サイクル）** — パーティ全体の1ローテーション分のダメージ合計です。",
        "**貢献度ランキング** — メンバーごとのダメージ量と占有率（%）をバーで表示します。",
        "**スキル別ダメージ** — 通常攻撃・共鳴スキル・解放など、スキル単位のダメージを確認できます。",
        "**自動適用のチームバフ** — メンバー同士が与え合ったバフをチップで表示します。手動入力は不要です。",
        "**状況依存の参考値** — 異常ダメージや調和度破壊などは合計に含めず、別枠で表記します。",
      ],
    },
    tip: "共鳴者3人を埋めると、下部の **AIパーティ分析** で編成評価を受け、履歴に保存することもできます（Googleログインが必要）。",
  },
  ai: {
    h2: "5. AIビルド — 対話型ビルド提案",
    p: "**AI** タブで所持キャラと目標（例：無課金、深層クリア）を入力すると、AIがビルドとパーティを提案します。提案結果は **履歴** タブに保存され、いつでも見返せます。この機能はGoogleログイン後に利用できます。",
    shot: { src: "/guide/12-ai.png", alt: "AIタブ", caption: "AIビルド — Googleログイン後に利用" },
  },
  notice: {
    h2: "6. お知らせ — サイト更新履歴",
    p: "右上のメガホンアイコンを押すと、サイトの更新履歴（バージョン別の変更点）を確認できます。新機能はまずここでご案内します。",
    shot: { src: "/guide/13-site-updates.png", alt: "お知らせ", caption: "お知らせ — バージョン別の更新履歴" },
  },
  footerAskPre: "さらにご質問があれば ",
  discordLabel: "Discord",
  footerAskPost: " でお気軽にどうぞ。",
  disclaimer: "Wuthering Waves / Kuro Games とは無関係の非公式ファンツールです。",
};

const zhHans: Copy = {
  backToApp: "返回应用",
  headline: "使用指南",
  intro:
    "这是一款为《鸣潮》（Wuthering Waves）提供角色图鉴、抽卡日程、队伍伤害计算和 AI 配装推荐的非官方粉丝工具。按下面的步骤操作，即使是初次访问也能立刻用上所有功能。",
  toc: [
    { id: "start", label: "开始" },
    { id: "codex", label: "图鉴" },
    { id: "pickup", label: "抽卡日程" },
    { id: "party", label: "队伍伤害" },
    { id: "ai", label: "AI 配装" },
    { id: "notice", label: "公告" },
  ],
  start: {
    h2: "1. 开始",
    p: "首页默认打开 **鸣潮更新** 标签，顶部可在 **AI · 图鉴 · 抽卡日程 · 鸣潮更新 · 队伍 · 记录** 之间切换。右上角的图标依次是：加入 Discord、浅色/深色主题切换、公告、谷歌登录。",
    shot: { src: "/guide/01-home.png", alt: "首页 — 鸣潮更新标签", caption: "首页（鸣潮更新）— 顶部标签与右上角图标" },
    tip: "大部分功能无需登录即可使用。谷歌登录仅用于 AI 配装推荐和保存记录。",
  },
  codex: {
    h2: "2. 图鉴 — 角色·武器·声骸信息",
    p1: "在 **图鉴** 标签中可搜索并筛选角色/武器/声骸。可按属性或武器类型缩小范围，也支持按名称搜索。",
    shot1: { src: "/guide/02-codex.png", alt: "图鉴 — 角色一览", caption: "图鉴标签 — 角色·武器·声骸子标签与搜索/筛选" },
    p2: "点击卡片会打开详情面板。可查看每个技能的说明，甚至 **各等级的实际倍率（%）**，让伤害计算的依据一目了然。",
    shot2: { src: "/guide/03-codex-detail.png", alt: "图鉴详情 — 技能倍率", caption: "角色详情 — 技能说明与倍率（用等级滑块调整）" },
  },
  pickup: {
    h2: "3. 抽卡日程",
    p: "一目了然地查看各版本的抽卡卡池日程。点击卡片可打开该角色/武器的详情。",
    shot: { src: "/guide/04-pickup.png", alt: "抽卡日程", caption: "抽卡日程 — 各版本卡池安排" },
  },
  party: {
    h2: "4. 队伍伤害计算 — 核心功能",
    p: "在 **队伍** 标签中编成 3 名共鸣者后，服务器引擎会计算全队伤害（1 循环）以及每人的贡献度。每名角色为队伍提供的共享增益会 **自动生效**，所以只需完成编成即可。",
    shot: { src: "/guide/05-party-empty.png", alt: "队伍标签初始界面", caption: "队伍标签 — 3 个槽位、敌人条件、队伍共享增益、计算按钮" },
    step1: {
      title: "添加共鸣者",
      body: "点击空槽位的 **添加共鸣者**，搜索并选择。填满 3 名后，计算按钮即可使用。",
      shots: [
        { src: "/guide/06-party-picker.png", alt: "共鸣者选择弹窗", caption: "共鸣者搜索 — 只输入部分名称也能找到" },
        { src: "/guide/07-party-filled.png", alt: "3 人编成完成", caption: "3 人编成完成 — 每张卡片显示基础属性" },
      ],
    },
    step2: {
      title: "编辑配装（可选）",
      body: "在每张卡片的 **编辑配装** 中，可设置角色等级、技能等级（默认 Lv.10）、**共鸣链（S0~S6）**、武器（等级·精炼）以及 5 个声骸（主/副词条）。不设置也会按默认值计算。",
      shot: { src: "/guide/08-build-editor.png", alt: "配装编辑器", caption: "编辑配装 — 等级·技能·共鸣链·武器·声骸·最终属性" },
      tip: "提升共鸣链层数后，对应序列的伤害提升效果会实际计入计算。可对比那些在高序列伤害大幅提升的角色。",
    },
    step3: {
      title: "敌人条件与完整循环",
      body1: "可调整敌人等级/抗性、无视/降低防御、增伤、伤害加成。若队伍中有湮灭角色，会自动应用降低敌人防御。",
      shot: { src: "/guide/09-conditions.png", alt: "敌人条件与完整循环", caption: "敌人条件 — 完整循环复选框（默认开启）与手动输入队伍共享增益" },
      body2: "开启 **完整循环**（默认）时，会以理想循环为基准，把共鸣链·武器·特性的条件增益全部计入，得出接近最大伤害的结果。关闭后则只计入常驻增益，给出较保守的数值。",
      tip: "与其他伤害计算器对比数值时，开启完整循环（默认）是通常的基准。",
    },
    step4: {
      title: "计算与结果解读",
      body: "点击 **用服务器引擎计算** 即可显示结果。",
      shot: { src: "/guide/10-party-result.png", alt: "计算结果", caption: "结果 — 全队总伤害、贡献度排名、各技能伤害、自动生效的队伍增益" },
      list: [
        "**全队总伤害（1 循环）** — 全队一次循环的伤害总和。",
        "**贡献度排名** — 用条形显示每名成员的伤害量与占比（%）。",
        "**各技能伤害** — 可查看普攻·共鸣技能·解放等按技能划分的伤害。",
        "**自动生效的队伍增益** — 成员之间互相提供的增益以标签显示，无需手动输入。",
        "**情境参考值** — 异常伤害、和谐度破坏等不计入总和，单独列出。",
      ],
    },
    tip: "填满 3 名共鸣者后，还可通过底部的 **AI 队伍分析** 获得编成评价并保存到记录（需谷歌登录）。",
  },
  ai: {
    h2: "5. AI 配装 — 对话式配装推荐",
    p: "在 **AI** 标签中输入你拥有的角色和目标（例如零氪、深层通关），AI 会推荐配装和队伍。推荐结果会保存到 **记录** 标签，可随时回看。此功能需谷歌登录后使用。",
    shot: { src: "/guide/12-ai.png", alt: "AI 标签", caption: "AI 配装 — 谷歌登录后使用" },
  },
  notice: {
    h2: "6. 公告 — 网站更新记录",
    p: "点击右上角的喇叭图标，可查看网站更新记录（各版本的变更）。有新功能时会先在这里公布。",
    shot: { src: "/guide/13-site-updates.png", alt: "公告", caption: "公告 — 各版本更新记录" },
  },
  footerAskPre: "还有疑问？欢迎到 ",
  discordLabel: "Discord",
  footerAskPost: " 咨询我们。",
  disclaimer: "与《鸣潮》/ 库洛游戏无关的非官方粉丝工具。",
};

const GUIDE: Record<Language, Copy> = { ko, en, ja, zhHans };

export default function GuideContent() {
  const { t, language } = useLanguage();
  const g = GUIDE[language];

  return (
    <>
      <header>
        <div className="wrap">
          <div className="htop" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 0" }}>
            <Link className="brand" href="/">
              <span className="seal">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/logo.png" alt="" aria-hidden="true" />
              </span>
              <b>{t.app.name}</b>
            </Link>
            <Link href="/" className="rounded-md border border-[var(--line-2)] px-3 py-1.5 text-sm text-[var(--fg-soft)] hover:border-[var(--accent)] hover:text-[var(--fg)]">
              ← {g.backToApp}
            </Link>
          </div>
        </div>
      </header>

      <main>
        <div className="wrap" style={{ paddingTop: 28, paddingBottom: 60 }}>
          <h1 className="text-2xl font-bold text-[var(--fg)]">{g.headline}</h1>
          <p className="mt-2 text-sm leading-relaxed text-[var(--muted)]">{g.intro}</p>

          <nav className="mt-4 flex flex-wrap gap-1.5">
            {g.toc.map((s) => (
              <a key={s.id} href={`#${s.id}`} className="rounded-full border border-[var(--line-2)] bg-[var(--surface)] px-3 py-1 text-xs text-[var(--fg-soft)] hover:border-[var(--accent)] hover:text-[var(--fg)]">
                {s.label}
              </a>
            ))}
          </nav>

          <section id="start" className="mt-10 scroll-mt-24">
            <h2 className="border-b border-[var(--line)] pb-2 text-xl font-bold text-[var(--fg)]">{g.start.h2}</h2>
            <p className="mt-3 text-sm leading-relaxed text-[var(--fg-soft)]"><RT s={g.start.p} /></p>
            <ShotFig shot={g.start.shot} />
            <Tip>{g.start.tip}</Tip>
          </section>

          <section id="codex" className="mt-10 scroll-mt-24">
            <h2 className="border-b border-[var(--line)] pb-2 text-xl font-bold text-[var(--fg)]">{g.codex.h2}</h2>
            <p className="mt-3 text-sm leading-relaxed text-[var(--fg-soft)]"><RT s={g.codex.p1} /></p>
            <ShotFig shot={g.codex.shot1} />
            <p className="mt-2 text-sm leading-relaxed text-[var(--fg-soft)]"><RT s={g.codex.p2} /></p>
            <ShotFig shot={g.codex.shot2} />
          </section>

          <section id="pickup" className="mt-10 scroll-mt-24">
            <h2 className="border-b border-[var(--line)] pb-2 text-xl font-bold text-[var(--fg)]">{g.pickup.h2}</h2>
            <p className="mt-3 text-sm leading-relaxed text-[var(--fg-soft)]"><RT s={g.pickup.p} /></p>
            <ShotFig shot={g.pickup.shot} />
          </section>

          <section id="party" className="mt-10 scroll-mt-24">
            <h2 className="border-b border-[var(--line)] pb-2 text-xl font-bold text-[var(--fg)]">{g.party.h2}</h2>
            <p className="mt-3 text-sm leading-relaxed text-[var(--fg-soft)]"><RT s={g.party.p} /></p>
            <ShotFig shot={g.party.shot} />

            <Step n={1} title={g.party.step1.title}>
              <RT s={g.party.step1.body} />
              {g.party.step1.shots.map((sh) => (
                <ShotFig key={sh.src} shot={sh} />
              ))}
            </Step>

            <Step n={2} title={g.party.step2.title}>
              <RT s={g.party.step2.body} />
              <ShotFig shot={g.party.step2.shot} />
              <Tip>{g.party.step2.tip}</Tip>
            </Step>

            <Step n={3} title={g.party.step3.title}>
              <RT s={g.party.step3.body1} />
              <ShotFig shot={g.party.step3.shot} />
              <RT s={g.party.step3.body2} />
              <Tip>{g.party.step3.tip}</Tip>
            </Step>

            <Step n={4} title={g.party.step4.title}>
              <RT s={g.party.step4.body} />
              <ShotFig shot={g.party.step4.shot} />
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {g.party.step4.list.map((li, i) => (
                  <li key={i}><RT s={li} /></li>
                ))}
              </ul>
            </Step>

            <Tip>
              <RT s={g.party.tip} />
            </Tip>
          </section>

          <section id="ai" className="mt-10 scroll-mt-24">
            <h2 className="border-b border-[var(--line)] pb-2 text-xl font-bold text-[var(--fg)]">{g.ai.h2}</h2>
            <p className="mt-3 text-sm leading-relaxed text-[var(--fg-soft)]"><RT s={g.ai.p} /></p>
            <ShotFig shot={g.ai.shot} />
          </section>

          <section id="notice" className="mt-10 scroll-mt-24">
            <h2 className="border-b border-[var(--line)] pb-2 text-xl font-bold text-[var(--fg)]">{g.notice.h2}</h2>
            <p className="mt-3 text-sm leading-relaxed text-[var(--fg-soft)]"><RT s={g.notice.p} /></p>
            <ShotFig shot={g.notice.shot} />
          </section>

          <div className="mt-12 rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4 text-center text-sm text-[var(--muted)]">
            {g.footerAskPre}
            <a href="https://discord.gg/hPhsf9GN7E" target="_blank" rel="noreferrer" className="font-medium text-[var(--accent)] hover:underline">
              {g.discordLabel}
            </a>
            {g.footerAskPost}
            <div className="mt-2">
              <Link href="/" className="font-medium text-[var(--accent)] hover:underline">← {g.backToApp}</Link>
            </div>
          </div>
        </div>
      </main>

      <footer>
        <p className="disc">{g.disclaimer}</p>
      </footer>
    </>
  );
}
