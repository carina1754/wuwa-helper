import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "이용 가이드 — 띵조 AI",
  description: "띵조 AI 사용법: 도감, 픽업 일정표, 파티 딜 계산(풀 업타임·자동 팀 버프), 실측 딜, AI 빌딩까지 스크린샷과 함께 안내합니다.",
};

/** 스크린샷 + 캡션 공통 프레임 */
function Shot({ src, alt, caption }: { src: string; alt: string; caption?: string }) {
  return (
    <figure className="my-4">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt={alt} loading="lazy" className="w-full rounded-lg border border-[var(--line)] bg-[var(--surface)]" />
      {caption ? <figcaption className="mt-1.5 text-center text-xs text-[var(--muted)]">{caption}</figcaption> : null}
    </figure>
  );
}

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
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

function Tip({ children }: { children: React.ReactNode }) {
  return (
    <div className="my-3 rounded-md border border-[var(--line-2)] bg-[var(--surface-2)] px-3 py-2.5 text-[13px] leading-relaxed text-[var(--fg-soft)]">
      <span className="mr-1 font-semibold text-[var(--accent)]">TIP</span>
      {children}
    </div>
  );
}

const TOC = [
  { id: "start", label: "시작하기" },
  { id: "codex", label: "도감" },
  { id: "pickup", label: "픽업 일정표" },
  { id: "party", label: "파티 딜 계산" },
  { id: "snapshot", label: "실측 딜" },
  { id: "ai", label: "AI 빌딩" },
  { id: "notice", label: "공지사항" },
];

export default function GuidePage() {
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
              <b>띵조 AI</b>
            </Link>
            <Link href="/" className="rounded-md border border-[var(--line-2)] px-3 py-1.5 text-sm text-[var(--fg-soft)] hover:border-[var(--accent)] hover:text-[var(--fg)]">
              ← 앱으로 돌아가기
            </Link>
          </div>
        </div>
      </header>

      <main>
        <div className="wrap" style={{ paddingTop: 28, paddingBottom: 60 }}>
          {/* 헤드라인 */}
          <h1 className="text-2xl font-bold text-[var(--fg)]">이용 가이드</h1>
          <p className="mt-2 text-sm leading-relaxed text-[var(--muted)]">
            띵조 AI는 명조: 워더링 웨이브의 캐릭터 도감 · 픽업 일정 · 파티 딜 계산 · AI 빌드 추천을 제공하는 비공식 팬 도구입니다.
            아래 순서대로 따라 하면 처음 방문해도 모든 기능을 바로 사용할 수 있습니다.
          </p>

          {/* 목차 */}
          <nav className="mt-4 flex flex-wrap gap-1.5">
            {TOC.map((s) => (
              <a key={s.id} href={`#${s.id}`} className="rounded-full border border-[var(--line-2)] bg-[var(--surface)] px-3 py-1 text-xs text-[var(--fg-soft)] hover:border-[var(--accent)] hover:text-[var(--fg)]">
                {s.label}
              </a>
            ))}
          </nav>

          {/* 1. 시작하기 */}
          <section id="start" className="mt-10 scroll-mt-24">
            <h2 className="border-b border-[var(--line)] pb-2 text-xl font-bold text-[var(--fg)]">1. 시작하기</h2>
            <p className="mt-3 text-sm leading-relaxed text-[var(--fg-soft)]">
              첫 화면에는 <b className="text-[var(--fg)]">명조 업데이트</b> 탭이 열려 있고, 상단에서 <b className="text-[var(--fg)]">AI · 도감 · 픽업 일정표 · 명조 업데이트 · 파티 · 실측 딜 · 기록</b> 탭을 오갈 수 있습니다.
              오른쪽 위 아이콘은 순서대로 디스코드 참여, 라이트/다크 테마 전환, 공지사항, 구글 로그인입니다.
            </p>
            <Shot src="/guide/01-home.png" alt="홈 화면 — 명조 업데이트 탭" caption="첫 화면(명조 업데이트) — 상단 탭과 우측 상단 아이콘" />
            <Tip>대부분의 기능은 로그인 없이 사용할 수 있습니다. 구글 로그인은 AI 빌드 추천과 기록 저장에만 필요합니다.</Tip>
          </section>

          {/* 2. 도감 */}
          <section id="codex" className="mt-10 scroll-mt-24">
            <h2 className="border-b border-[var(--line)] pb-2 text-xl font-bold text-[var(--fg)]">2. 도감 — 캐릭터·무기·에코 정보</h2>
            <p className="mt-3 text-sm leading-relaxed text-[var(--fg-soft)]">
              <b className="text-[var(--fg)]">도감</b> 탭에서 캐릭터/무기/에코를 검색·필터링할 수 있습니다. 속성이나 무기 타입으로 좁혀 보고, 이름 검색도 지원합니다.
            </p>
            <Shot src="/guide/02-codex.png" alt="도감 — 캐릭터 그리드" caption="도감 탭 — 캐릭터·무기·에코 서브탭과 검색/필터" />
            <p className="mt-2 text-sm leading-relaxed text-[var(--fg-soft)]">
              카드를 클릭하면 상세 창이 열립니다. 스킬별 설명과 <b className="text-[var(--fg)]">레벨별 실제 배율(%)</b>까지 확인할 수 있어 딜 계산의 근거를 그대로 볼 수 있습니다.
            </p>
            <Shot src="/guide/03-codex-detail.png" alt="도감 상세 — 스킬 배율" caption="캐릭터 상세 — 스킬 설명과 배율(레벨 슬라이더로 조절)" />
          </section>

          {/* 3. 픽업 일정표 */}
          <section id="pickup" className="mt-10 scroll-mt-24">
            <h2 className="border-b border-[var(--line)] pb-2 text-xl font-bold text-[var(--fg)]">3. 픽업 일정표</h2>
            <p className="mt-3 text-sm leading-relaxed text-[var(--fg-soft)]">
              버전별 픽업 배너 일정을 한눈에 볼 수 있습니다. 카드를 클릭하면 해당 캐릭터/무기의 상세 정보가 열립니다.
            </p>
            <Shot src="/guide/04-pickup.png" alt="픽업 일정표" caption="픽업 일정표 — 버전별 배너 일정" />
          </section>

          {/* 4. 파티 딜 계산 */}
          <section id="party" className="mt-10 scroll-mt-24">
            <h2 className="border-b border-[var(--line)] pb-2 text-xl font-bold text-[var(--fg)]">4. 파티 딜 계산 — 핵심 기능</h2>
            <p className="mt-3 text-sm leading-relaxed text-[var(--fg-soft)]">
              <b className="text-[var(--fg)]">파티</b> 탭에서 공명자 3명을 편성하면 서버 엔진이 파티 전체 피해(1사이클)와 각자의 기여도를 계산합니다.
              각 캐릭터가 파티에 주는 공유 버프는 <b className="text-[var(--fg)]">자동으로 반영</b>되므로 편성만 하면 됩니다.
            </p>
            <Shot src="/guide/05-party-empty.png" alt="파티 탭 초기 화면" caption="파티 탭 — 슬롯 3개, 적 조건, 팀 공유 버프, 계산 버튼" />

            <Step n={1} title="공명자 추가">
              빈 슬롯의 <b className="text-[var(--fg)]">공명자 추가</b>를 누르고 검색해서 선택합니다. 3명을 채우면 계산 버튼이 활성화됩니다.
              <Shot src="/guide/06-party-picker.png" alt="공명자 선택 모달" caption="공명자 검색 — 이름 일부만 입력해도 찾아집니다" />
              <Shot src="/guide/07-party-filled.png" alt="3인 편성 완료" caption="3인 편성 완료 — 카드마다 기본 스탯이 표시됩니다" />
            </Step>

            <Step n={2} title="빌드 편집 (선택)">
              각 카드의 <b className="text-[var(--fg)]">빌드 편집</b>에서 캐릭터 레벨, 스킬 레벨(기본 Lv.10), <b className="text-[var(--fg)]">공명 사슬(S0~S6)</b>, 무기(레벨·정제), 에코 5개(메인/부가 옵션)를 설정할 수 있습니다.
              설정하지 않아도 기본값으로 계산됩니다.
              <Shot src="/guide/08-build-editor.png" alt="빌드 편집기" caption="빌드 편집 — 레벨·스킬·공명 사슬·무기·에코·최종 스탯" />
              <Tip>공명 사슬 단계를 올리면 해당 시퀀스의 피해 증가 효과가 딜 계산에 실제로 반영됩니다. 상위 시퀀스에서 딜이 크게 오르는 캐릭터를 비교해 보세요.</Tip>
            </Step>

            <Step n={3} title="적 조건과 풀 업타임">
              적 레벨·저항, 방어 무시/감소, 부스트, 피해증가를 조절할 수 있습니다. 파티에 암흑(인멸) 캐릭터가 있으면 적 방어 감소가 자동 적용됩니다.
              <Shot src="/guide/09-conditions.png" alt="적 조건과 풀 업타임" caption="적 조건 — 풀 업타임 체크박스(기본 켜짐)와 팀 공유 버프 수동 입력" />
              <b className="text-[var(--fg)]">풀 업타임</b>이 켜져 있으면(기본) 공명 사슬·무기·특성의 조건부 버프를 이상적인 로테이션 기준으로 모두 반영해 최대 딜에 가깝게 계산합니다.
              끄면 상시 발동 버프만 반영한 보수적인 수치를 보여줍니다.
              <Tip>다른 딜 계산기와 수치를 비교할 때는 풀 업타임을 켠 상태(기본)가 일반적인 기준입니다.</Tip>
            </Step>

            <Step n={4} title="계산과 결과 해석">
              <b className="text-[var(--fg)]">서버 엔진으로 계산</b>을 누르면 결과가 표시됩니다.
              <Shot src="/guide/10-party-result.png" alt="계산 결과" caption="결과 — 팀 총 피해, 기여도 순위, 스킬별 피해, 자동 적용 팀 버프" />
              <ul className="mt-2 list-disc space-y-1 pl-5">
                <li><b className="text-[var(--fg)]">팀 총 피해 (1사이클)</b> — 파티 전체의 한 로테이션 피해 합계입니다.</li>
                <li><b className="text-[var(--fg)]">기여도 순위</b> — 멤버별 피해량과 점유율(%)을 막대로 보여줍니다.</li>
                <li><b className="text-[var(--fg)]">스킬별 피해</b> — 기본 공격·공명 스킬·해방 등 스킬 단위 피해를 확인할 수 있습니다.</li>
                <li><b className="text-[var(--fg)]">자동 적용 팀 버프</b> — 파티원이 서로 주고받은 버프가 칩으로 표시됩니다. 수동 입력이 필요 없습니다.</li>
                <li><b className="text-[var(--fg)]">상황부 참고값</b> — 이상 피해·조화도 파괴 등은 총합에 넣지 않고 별도로 표기합니다.</li>
              </ul>
            </Step>

            <Tip>공명자 3명을 모두 채우면 하단 <b className="text-[var(--fg)]">AI 파티 분석</b>으로 구성 평가를 받아 기록에 저장할 수도 있습니다(구글 로그인 필요).</Tip>
          </section>

          {/* 5. 실측 딜 */}
          <section id="snapshot" className="mt-10 scroll-mt-24">
            <h2 className="border-b border-[var(--line)] pb-2 text-xl font-bold text-[var(--fg)]">5. 실측 딜 — 내 계정 그대로 계산</h2>
            <p className="mt-3 text-sm leading-relaxed text-[var(--fg-soft)]">
              <b className="text-[var(--fg)]">실측 딜</b> 탭은 게임의 캐릭터 정보 화면 스크린샷(PNG·JPG)을 올리면 실제 장착한 에코 부가옵션을 읽어 <b className="text-[var(--fg)]">내 계정의 절대 피해</b>를 계산합니다.
              파티 탭의 기본값 상대 비교와 달리 실측값 기준입니다. 스크린샷 없이 <b className="text-[var(--fg)]">빈 양식으로 직접 입력</b>할 수도 있습니다.
            </p>
            <Shot src="/guide/11-snapshot.png" alt="실측 딜 탭" caption="실측 딜 — 캐릭터 정보 스크린샷 업로드 또는 수동 입력" />
          </section>

          {/* 6. AI 빌딩 */}
          <section id="ai" className="mt-10 scroll-mt-24">
            <h2 className="border-b border-[var(--line)] pb-2 text-xl font-bold text-[var(--fg)]">6. AI 빌딩 — 대화형 빌드 추천</h2>
            <p className="mt-3 text-sm leading-relaxed text-[var(--fg-soft)]">
              <b className="text-[var(--fg)]">AI</b> 탭에서 보유 캐릭터와 목표(예: 무과금, 심층 클리어)를 입력하면 AI가 빌드와 파티를 추천합니다.
              추천 결과는 <b className="text-[var(--fg)]">기록</b> 탭에 저장되어 언제든 다시 볼 수 있습니다. 이 기능은 구글 로그인 후 이용할 수 있습니다.
            </p>
            <Shot src="/guide/12-ai.png" alt="AI 탭" caption="AI 빌딩 — 구글 로그인 후 이용" />
          </section>

          {/* 7. 공지사항 */}
          <section id="notice" className="mt-10 scroll-mt-24">
            <h2 className="border-b border-[var(--line)] pb-2 text-xl font-bold text-[var(--fg)]">7. 공지사항 — 사이트 업데이트 내역</h2>
            <p className="mt-3 text-sm leading-relaxed text-[var(--fg-soft)]">
              우측 상단의 확성기 아이콘을 누르면 사이트 업데이트 내역(버전별 변경사항)을 볼 수 있습니다. 새 기능이 추가되면 이곳에서 먼저 안내합니다.
            </p>
            <Shot src="/guide/13-site-updates.png" alt="공지사항" caption="공지사항 — 버전별 업데이트 내역" />
          </section>

          <div className="mt-12 rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4 text-center text-sm text-[var(--muted)]">
            더 궁금한 점은{" "}
            <a href="https://discord.gg/hPhsf9GN7E" target="_blank" rel="noreferrer" className="font-medium text-[var(--accent)] hover:underline">디스코드</a>
            에서 물어봐 주세요.
            <div className="mt-2">
              <Link href="/" className="font-medium text-[var(--accent)] hover:underline">← 앱으로 돌아가기</Link>
            </div>
          </div>
        </div>
      </main>

      <footer>
        <p className="disc">Wuthering Waves / Kuro Games와 무관한 비공식 팬 도구입니다.</p>
      </footer>
    </>
  );
}
