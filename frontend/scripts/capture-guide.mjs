/**
 * 가이드 페이지용 스크린샷 캡처 — 실제 서비스(127.0.0.1:3000, prod 서버)를 시스템 Chrome으로 순회하며
 * public/guide/*.png 생성. 실행: node scripts/capture-guide.mjs
 */
import fs from "node:fs";
import path from "node:path";
import puppeteer from "puppeteer-core";

const BASE = process.env.GUIDE_BASE_URL ?? "http://127.0.0.1:3000";
const OUT = path.resolve(import.meta.dirname, "..", "public", "guide");
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";

fs.mkdirSync(OUT, { recursive: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** 텍스트가 정확히 일치(공백 정리 후)하는 <button> 클릭 */
async function clickButton(page, text) {
  const ok = await page.evaluate((t) => {
    const btns = [...document.querySelectorAll("button")];
    const b = btns.find((x) => x.textContent.replace(/\s+/g, " ").trim() === t);
    if (b) { b.click(); return true; }
    return false;
  }, text);
  if (!ok) throw new Error(`button not found: ${text}`);
}

/** 텍스트를 포함하는 첫 <button> 클릭 */
async function clickButtonContaining(page, text) {
  const ok = await page.evaluate((t) => {
    const btns = [...document.querySelectorAll("button")];
    const b = btns.find((x) => x.textContent.replace(/\s+/g, " ").trim().includes(t));
    if (b) { b.click(); return true; }
    return false;
  }, text);
  if (!ok) throw new Error(`button(contains) not found: ${text}`);
}

async function settle(page, ms = 900) {
  try { await page.waitForNetworkIdle({ idleTime: ms, timeout: 15000 }); } catch { /* 광고 등 지속 요청은 무시 */ }
  await sleep(350);
}

async function shot(page, name) {
  await page.screenshot({ path: path.join(OUT, name), type: "png" });
  console.log("saved", name);
}

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: true,
  args: ["--hide-scrollbars", "--force-device-scale-factor=1.5", "--lang=ko-KR"],
});
const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1.5 });

try {
  // 1) 홈(명조 업데이트 탭이 기본)
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("nav.tabs button");
  await settle(page, 1200);
  await shot(page, "01-home.png");

  // 2) 도감
  await clickButton(page, "도감");
  await settle(page, 1200);
  await shot(page, "02-codex.png");

  // 3) 도감 상세(첫 캐릭터 카드 클릭)
  const openedDetail = await page.evaluate(() => {
    const grid = document.querySelector("main");
    const card = grid?.querySelector("button img")?.closest("button");
    if (card) { card.click(); return true; }
    return false;
  });
  if (openedDetail) {
    await sleep(500);
    await settle(page, 800);
    const hasDialog = await page.$('[role="dialog"]');
    if (hasDialog) {
      await shot(page, "03-codex-detail.png");
      await page.keyboard.press("Escape");
      await page.mouse.click(20, 450); // 오버레이 클릭 닫기 폴백
      await sleep(400);
    }
  }

  // 4) 픽업 일정표
  await clickButton(page, "픽업 일정표");
  await settle(page, 1200);
  await shot(page, "04-pickup.png");

  // 5) 파티 — 초기 화면
  await clickButton(page, "파티");
  await settle(page, 1000);
  await shot(page, "05-party-empty.png");

  // 6) 공명자 선택 모달
  await clickButtonContaining(page, "공명자 추가");
  await page.waitForSelector('input[placeholder="공명자 검색"]');
  await page.type('input[placeholder="공명자 검색"]', "데니아");
  await sleep(600);
  await settle(page, 600);
  await shot(page, "06-party-picker.png");
  await page.click('button[title="데니아"]');
  await sleep(500);

  // 나머지 2명 편성(장리·모니에)
  for (const name of ["장리", "모니에"]) {
    await clickButtonContaining(page, "공명자 추가");
    await page.waitForSelector('input[placeholder="공명자 검색"]');
    await page.type('input[placeholder="공명자 검색"]', name);
    await sleep(500);
    await page.click(`button[title="${name}"]`);
    await sleep(500);
  }
  await settle(page, 800);
  await shot(page, "07-party-filled.png");

  // 7) 빌드 편집기
  await clickButtonContaining(page, "빌드 편집");
  await sleep(700);
  await settle(page, 700);
  await shot(page, "08-build-editor.png");
  await page.mouse.click(20, 450); // 오버레이 클릭으로 닫기
  await sleep(500);

  // 8) 적 조건 + 풀 업타임 블록(요소 캡처)
  const condHandle = await page.evaluateHandle(() => {
    const el = [...document.querySelectorAll("div")].find((d) => d.firstElementChild?.textContent === "적 조건");
    return el?.closest("div.grid") ?? el;
  });
  const condEl = condHandle.asElement();
  if (condEl) {
    await condEl.scrollIntoViewIfNeeded?.();
    await sleep(300);
    await condEl.screenshot({ path: path.join(OUT, "09-conditions.png") });
    console.log("saved 09-conditions.png");
  }

  // 9) 계산 → 결과
  await clickButton(page, "서버 엔진으로 계산");
  await page.waitForFunction(() => document.body.textContent.includes("팀 총 피해"), { timeout: 60000 });
  await settle(page, 1200);
  await page.evaluate(() => {
    // 스티키 헤더(~170px)에 배너가 가리지 않게 오프셋 스크롤
    const el = [...document.querySelectorAll("span")].find((s) => s.textContent === "팀 총 피해 (1사이클)");
    const y = el.getBoundingClientRect().top + window.scrollY;
    window.scrollTo(0, Math.max(0, y - 200));
  });
  await sleep(500);
  await shot(page, "10-party-result.png");

  // 10) 실측 딜
  await page.evaluate(() => window.scrollTo(0, 0));
  await clickButton(page, "실측 딜");
  await settle(page, 1000);
  await shot(page, "11-snapshot.png");

  // 11) AI 탭
  await clickButton(page, "AI");
  await settle(page, 1000);
  await shot(page, "12-ai.png");

  // 12) 공지사항(헤더 스피커 아이콘)
  await page.click('button[aria-label="공지사항"]');
  await settle(page, 1000);
  await shot(page, "13-site-updates.png");

  console.log("ALL DONE");
} finally {
  await browser.close();
}
