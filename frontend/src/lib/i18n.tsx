"use client";

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

export type Language = "ko" | "en";

export const copy = {
  ko: {
    app: {
      tagline: "스크린샷 추출, 에코 점수, 빌드 우선순위",
      status: "비공식 가이드",
      languageLabel: "언어 전환",
      themeLabel: "테마 전환",
      signIn: "구글 로그인",
      signOut: "로그아웃",
      admin: "관리자",
      loading: "로딩 중",
    },
    tabs: {
      Dashboard: "대시보드",
      Analyzer: "분석",
      Planner: "플래너",
      PickupSchedule: "픽업 일정표",
      Updates: "업데이트 정리",
      Teams: "팀",
      History: "기록",
    },
    roles: {
      main_dps: "메인 딜러",
      sub_dps: "서브 딜러",
      support: "서포터",
      healer: "힐러",
    },
    dashboard: {
      cards: [
        ["최근 분석", "진단을 저장하면 기록에서 확인할 수 있습니다."],
        ["현재 우선순위", "분석을 실행해 가장 약한 에코부터 확인하세요."],
        ["다음 행동", "부옵션 최적화 전에 주옵션부터 맞추세요."],
      ],
    },
    analyzer: {
      manualEditor: "수동 편집",
      character: "캐릭터",
      level: "레벨",
      weapon: "무기",
      atk: "공격력",
      critRate: "치명타 확률",
      critDmg: "치명타 피해",
      energyRegen: "공명 효율",
      analyzeImage: "이미지 분석",
      runDiagnosis: "진단 실행",
      saveHistory: "기록 저장",
      selectImageFirst: "먼저 이미지를 선택하세요.",
      extracting: "스크린샷을 추출하는 중...",
      extractionReady: "추출이 완료되었습니다.",
      extractionFailed: "추출에 실패했습니다.",
      diagnosisRunning: "진단을 실행하는 중...",
      diagnosisComplete: "진단이 완료되었습니다.",
      diagnosisFailed: "진단에 실패했습니다.",
      saveRequirement: "기록 저장 전에 추출과 진단을 실행하세요.",
      saved: "기록에 저장했습니다.",
      saveFailed: "기록 저장에 실패했습니다.",
    },
    uploader: {
      screenshot: "스크린샷",
      previewAlt: "업로드한 스크린샷 미리보기",
      previewEmpty: "이미지 미리보기가 여기에 표시됩니다",
    },
    echoes: {
      title: "에코",
      echo: "에코",
      slot: "슬롯",
      echoName: "에코 이름",
      set: "세트",
      mainStat: "주옵션",
      level: "레벨",
      subStat: "부옵션",
      value: "값",
    },
    extraction: {
      empty: "아직 추출 결과가 없습니다.",
      title: "추출 결과",
      screen: "화면",
      rawText: "원문 텍스트",
      json: "JSON",
    },
    diagnosis: {
      empty: "진단을 실행하면 결과가 표시됩니다.",
      title: "진단 결과",
    },
    planner: {
      title: "캐릭터 플래너",
      body: "캐릭터별 추천 세트, 무기, 우선 스탯을 확인하세요.",
      search: "캐릭터 검색",
      allRoles: "전체 역할",
      allElements: "전체 원소",
      recommendedSet: "추천 세트",
      fallbackSets: "대체 세트",
      weapon: "추천 무기",
      bonusStats: "보너스 스탯",
      noResults: "조건에 맞는 캐릭터가 없습니다.",
      source: "출처",
    },
    teams: {
      title: "팀 빌더",
      body: "MVP 팀 조언은 역할 기준입니다: 메인 딜러, 서브 딜러, 서포터/힐러. 보유 캐릭터 추천은 다음 단계에서 추가됩니다.",
    },
    pickup: {
      title: "역대 픽업 일정표",
      body: "한국 기준으로 정리한 캐릭터 픽업 월별 일정입니다.",
      year: "년도",
      yearly: "연간 보기",
      monthly: "월별 달력",
      legend: "범례",
      first: "첫 픽업",
      rerun: "복각",
      empty: "등록된 픽업 정보가 없습니다.",
    },
    updates: {
      title: "명조 업데이트 정리",
      body: "한국 기준 날짜와 주요 내용을 간단히 정리했습니다.",
      releaseDate: "한국 기준",
      source: "출처",
      empty: "등록된 업데이트 정보가 없습니다.",
    },
    history: {
      title: "기록",
      empty: "저장한 분석이 여기에 표시됩니다.",
      unknown: "알 수 없음",
      select: "저장된 세션을 선택하세요.",
    },
    rules: {
      title: "규칙 관리",
      save: "규칙 저장",
      saved: "규칙을 저장했습니다.",
      saveFailed: "규칙 저장에 실패했습니다.",
    },
    settings: {
      title: "설정",
      apiBaseUrl: "API 기본 URL",
      openAiKey: "OpenAI API 키",
      openAiKeyBody: "실제 비전 추출을 사용하려면 백엔드 환경에 OPENAI_API_KEY를 설정하세요. 없으면 mock 모드가 사용됩니다.",
      legalNotice: "법적 안내",
      legalNoticeBody: "WuWa AI Coach는 비공식 팬 도구이며 Wuthering Waves 또는 Kuro Games와 관련이 없습니다.",
      exportJson: "JSON 내보내기",
      importJson: "JSON 가져오기",
      imported: (rules: number, history: number, characters = 0) => `규칙 ${rules}개, 캐릭터 ${characters}개, 기록 ${history}개를 가져왔습니다.`,
    },
    login: {
      title: "로그인",
      body: "Google 계정으로 로그인하면 관리자 권한과 사용자 세션을 확인할 수 있습니다.",
      google: "Google로 로그인",
      adminEmail: "관리자 이메일: wawa.ai.coach@gmail.com",
    },
    admin: {
      title: "관리자 페이지",
      body: "규칙과 서비스 설정은 관리자만 수정할 수 있습니다.",
      restricted: "관리자 계정으로 로그인해야 접근할 수 있습니다.",
    },
  },
  en: {
    app: {
      tagline: "Screenshot extraction, echo scoring, and build priorities",
      status: "Unofficial guide",
      languageLabel: "Switch language",
      themeLabel: "Switch theme",
      signIn: "Google Login",
      signOut: "Log out",
      admin: "Admin",
      loading: "Loading",
    },
    tabs: {
      Dashboard: "Dashboard",
      Analyzer: "Analyzer",
      Planner: "Planner",
      PickupSchedule: "Pickup Schedule",
      Updates: "Updates",
      Teams: "Teams",
      History: "History",
    },
    roles: {
      main_dps: "Main DPS",
      sub_dps: "Sub DPS",
      support: "Support",
      healer: "Healer",
    },
    dashboard: {
      cards: [
        ["Recent analysis", "Use History after saving a diagnosis."],
        ["Current priority", "Run Analyzer to identify the weakest echo first."],
        ["Next action", "Fix main stats before optimizing sub-stats."],
      ],
    },
    analyzer: {
      manualEditor: "Manual Editor",
      character: "Character",
      level: "Level",
      weapon: "Weapon",
      atk: "ATK",
      critRate: "Crit Rate",
      critDmg: "Crit DMG",
      energyRegen: "Energy Regen",
      analyzeImage: "Analyze Image",
      runDiagnosis: "Run Diagnosis",
      saveHistory: "Save History",
      selectImageFirst: "Select an image first.",
      extracting: "Extracting screenshot...",
      extractionReady: "Extraction ready.",
      extractionFailed: "Extraction failed.",
      diagnosisRunning: "Running diagnosis...",
      diagnosisComplete: "Diagnosis complete.",
      diagnosisFailed: "Diagnosis failed.",
      saveRequirement: "Run extraction and diagnosis before saving history.",
      saved: "Saved to history.",
      saveFailed: "History save failed.",
    },
    uploader: {
      screenshot: "Screenshot",
      previewAlt: "Uploaded screenshot preview",
      previewEmpty: "Image preview appears here",
    },
    echoes: {
      title: "Echoes",
      echo: "Echo",
      slot: "slot",
      echoName: "Echo name",
      set: "Set",
      mainStat: "Main stat",
      level: "Level",
      subStat: "Sub stat",
      value: "Value",
    },
    extraction: {
      empty: "No extraction yet.",
      title: "Extraction",
      screen: "Screen",
      rawText: "Raw text",
      json: "JSON",
    },
    diagnosis: {
      empty: "Run diagnosis to see results.",
      title: "Diagnosis Result",
    },
    planner: {
      title: "Character Planner",
      body: "Review each character's recommended sets, weapon, and priority stats.",
      search: "Search characters",
      allRoles: "All roles",
      allElements: "All elements",
      recommendedSet: "Recommended set",
      fallbackSets: "Fallback sets",
      weapon: "Recommended weapon",
      bonusStats: "Bonus stats",
      noResults: "No characters match these filters.",
      source: "Source",
    },
    teams: {
      title: "Team Builder",
      body: "MVP team advice is role-based: main DPS, sub DPS, and support/healer. Owned-character recommendations come in a later phase.",
    },
    pickup: {
      title: "Pickup Schedule",
      body: "Character pickup schedule organized for Korea.",
      year: "Year",
      yearly: "Year view",
      monthly: "Monthly calendar",
      legend: "Legend",
      first: "First pickup",
      rerun: "Rerun",
      empty: "No pickup schedule has been added.",
    },
    updates: {
      title: "Wuthering Waves Updates",
      body: "Major updates summarized with Korea-based dates.",
      releaseDate: "Korea date",
      source: "Source",
      empty: "No update summaries have been added.",
    },
    history: {
      title: "History",
      empty: "Saved analyses appear here.",
      unknown: "Unknown",
      select: "Select a saved session.",
    },
    rules: {
      title: "Rules Manager",
      save: "Save Rules",
      saved: "Rules saved.",
      saveFailed: "Rules save failed.",
    },
    settings: {
      title: "Settings",
      apiBaseUrl: "API base URL",
      openAiKey: "OpenAI API key",
      openAiKeyBody: "Set OPENAI_API_KEY in the backend environment to enable real vision extraction. Without it, mock mode is used.",
      legalNotice: "Legal notice",
      legalNoticeBody: "WuWa AI Coach is an unofficial fan tool and is not affiliated with Wuthering Waves or Kuro Games.",
      exportJson: "Export JSON",
      importJson: "Import JSON",
      imported: (rules: number, history: number, characters = 0) => `Imported ${rules} rules, ${characters} characters, and ${history} history sessions.`,
    },
    login: {
      title: "Login",
      body: "Sign in with Google to verify your user session and admin access.",
      google: "Sign in with Google",
      adminEmail: "Admin email: wawa.ai.coach@gmail.com",
    },
    admin: {
      title: "Admin",
      body: "Rules and service settings are only editable by admins.",
      restricted: "Sign in with an admin account to access this page.",
    },
  },
} as const;

interface LanguageContextValue {
  language: Language;
  setLanguage: (language: Language) => void;
  toggleLanguage: () => void;
  t: (typeof copy)[Language];
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>("ko");
  const value = useMemo(
    () => ({
      language,
      setLanguage,
      toggleLanguage: () => setLanguage((current) => (current === "ko" ? "en" : "ko")),
      t: copy[language],
    }),
    [language],
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  const value = useContext(LanguageContext);
  if (!value) {
    throw new Error("useLanguage must be used within LanguageProvider");
  }
  return value;
}
