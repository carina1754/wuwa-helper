"""설정 탭 — BYO NVIDIA 키(자동저장) + 키 인증 + 추천 모델 top3 클릭 선택 + 이용안내."""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QLineEdit,
    QPushButton,
    QWidget,
)

from .. import engine, settings
from ..lang import LANG
from ..widgets import FlowLayout, card, chip, clear_layout, hbox, hsep, label, vbox

STR = {
    "ko": {
        "title": "설정", "key_label": "NVIDIA API 키",
        "key_ph": "nvapi-…", "key_hint": "이 키는 이 컴퓨터에만 저장되며 서버로 전송되지 않습니다.",
        "verify": "키 인증하기", "loading": "인증 중…",
        "no_key": "먼저 API 키를 입력하세요.", "verify_fail": "키 인증 실패: {}",
        "verified": "인증 성공 — 아래에서 모델을 클릭해 선택하세요.",
        "rec_models": "추천 모델", "howto": "사용 방법",
        "step1": "1. NVIDIA build.nvidia.com 에서 무료 API 키를 발급받습니다.",
        "step2": "2. 위 칸에 키를 붙여넣으면 자동 저장됩니다.",
        "step3": "3. ‘키 인증하기’를 누르고 추천 모델 중 하나를 클릭합니다.",
        "step4": "4. AI 빌딩 탭에서 대화하며 빌드 추천을 받습니다.",
    },
    "en": {
        "title": "Settings", "key_label": "NVIDIA API Key",
        "key_ph": "nvapi-…", "key_hint": "Stored only on this computer; never sent to any server.",
        "verify": "Verify key", "loading": "Verifying…",
        "no_key": "Enter an API key first.", "verify_fail": "Key verification failed: {}",
        "verified": "Verified — click a model below to select it.",
        "rec_models": "Recommended models", "howto": "How to use",
        "step1": "1. Get a free API key at NVIDIA build.nvidia.com.",
        "step2": "2. Paste it above — it saves automatically.",
        "step3": "3. Click ‘Verify key’, then pick a recommended model.",
        "step4": "4. Chat in the AI Building tab for build advice.",
    },
    "ja": {
        "title": "設定", "key_label": "NVIDIA API キー",
        "key_ph": "nvapi-…", "key_hint": "このキーはこのPCにのみ保存され、サーバーには送信されません。",
        "verify": "キーを認証", "loading": "認証中…",
        "no_key": "先にAPIキーを入力してください。", "verify_fail": "キー認証に失敗しました: {}",
        "verified": "認証成功 — 下のモデルをクリックして選択してください。",
        "rec_models": "おすすめモデル", "howto": "使い方",
        "step1": "1. NVIDIA build.nvidia.com で無料APIキーを取得します。",
        "step2": "2. 上の欄に貼り付けると自動保存されます。",
        "step3": "3. 「キーを認証」を押して、おすすめモデルを選びます。",
        "step4": "4. AIビルディングタブで会話しビルド提案を受けます。",
    },
    "zhHans": {
        "title": "设置", "key_label": "NVIDIA API 密钥",
        "key_ph": "nvapi-…", "key_hint": "仅保存在本机，不会发送到任何服务器。",
        "verify": "验证密钥", "loading": "验证中…",
        "no_key": "请先输入 API 密钥。", "verify_fail": "密钥验证失败：{}",
        "verified": "验证成功 — 点击下方模型进行选择。",
        "rec_models": "推荐模型", "howto": "使用方法",
        "step1": "1. 在 NVIDIA build.nvidia.com 获取免费 API 密钥。",
        "step2": "2. 粘贴到上方，自动保存。",
        "step3": "3. 点击“验证密钥”，然后选择一个推荐模型。",
        "step4": "4. 在 AI 配装标签页对话以获取建议。",
    },
}

# 추천 랭킹 — OpenRouter 리더보드식 등급(프론티어 추론 > OSS 플래그십 > 대형 MoE > 고속 비추론).
# 키로 조회한 실제 모델 목록과 부분일치로 매칭해 상위 3개만 노출.
_RANK = [
    "deepseek-ai/deepseek-r1",
    "openai/gpt-oss-120b",
    "qwen/qwen3-235b",
    "meta/llama-3.1-405b",
    "deepseek-ai/deepseek-v3",
    "meta/llama-3.3-70b",
    "qwen/qwen3-32b",
    "openai/gpt-oss-20b",
    "mistralai/mistral-large",
]


_TOP_N = 5


def _top_models(models: list[str]) -> list[str]:
    picked: list[str] = []
    for want in _RANK:
        hit = next((m for m in models if want in m and m not in picked), None)
        if hit:
            picked.append(hit)
        if len(picked) == _TOP_N:
            return picked
    for m in models:  # 랭킹 매칭이 모자라면 목록 앞에서 채움
        if m not in picked:
            picked.append(m)
        if len(picked) == _TOP_N:
            break
    return picked


class _ModelsWorker(QThread):
    done = Signal(list)
    failed = Signal(str)

    def run(self) -> None:
        try:
            self.done.emit(engine.ai_models())
        except Exception as exc:  # noqa: BLE001 — surface any fetch error to UI
            self.failed.emit(str(exc))


class SettingsTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._worker: _ModelsWorker | None = None
        s = settings.load()

        root = vbox(self, margins=(20, 20, 20, 20), spacing=16)
        self._title = label("", "H1")
        root.addWidget(self._title)

        box = card()
        bl = vbox(box, margins=(18, 18, 18, 18), spacing=10)
        self._key_lb = label("", "H2")
        bl.addWidget(self._key_lb)
        krow = hbox(spacing=8)
        self._key = QLineEdit(s.get("nvidia_key", ""))
        self._key.setEchoMode(QLineEdit.Password)
        self._key.textChanged.connect(self._on_key)
        krow.addWidget(self._key, 1)
        self._verify_btn = QPushButton()
        self._verify_btn.setObjectName("Accent")
        self._verify_btn.clicked.connect(self._verify)
        krow.addWidget(self._verify_btn)
        bl.addLayout(krow)
        self._key_hint = label("", "Muted", wrap=True)
        bl.addWidget(self._key_hint)
        self._status = label("", "Faint", wrap=True)
        bl.addWidget(self._status)
        bl.addWidget(hsep())

        self._model_lb = label("", "H2")
        bl.addWidget(self._model_lb)
        self._chip_group = QButtonGroup(self)
        self._chip_group.setExclusive(True)
        self._chips_host = QWidget()
        self._chips_lay = FlowLayout(self._chips_host, spacing=8)  # 5칩 — 좁으면 줄바꿈
        bl.addWidget(self._chips_host)
        root.addWidget(box)

        how = card()
        hl = vbox(how, margins=(18, 18, 18, 18), spacing=8)
        self._howto = label("", "H2")
        hl.addWidget(self._howto)
        self._steps = [label("", "Muted", wrap=True) for _ in range(4)]
        for st in self._steps:
            hl.addWidget(st)
        root.addWidget(how)
        root.addStretch(1)

        # 인증 전엔 저장된 모델만 칩으로 표시(현재 설정 확인용)
        saved = s.get("model") or ""
        self._set_model_chips([saved] if saved else [], saved)
        self.retranslate()

    # --- persistence (auto-save) --------------------------------------------
    def _on_key(self, text: str) -> None:
        settings.save(nvidia_key=text.strip())

    # --- verify + top3 ------------------------------------------------------
    def _verify(self) -> None:
        if not self._key.text().strip():
            self._status.setText(LANG.m(STR, "no_key"))
            return
        self._verify_btn.setEnabled(False)
        self._status.setText(LANG.m(STR, "loading"))
        self._worker = _ModelsWorker()
        self._worker.done.connect(self._on_models)
        self._worker.failed.connect(self._on_fail)
        self._worker.start()

    def _on_models(self, models: list) -> None:
        self._verify_btn.setEnabled(True)
        self._status.setText(LANG.m(STR, "verified"))
        top = _top_models(models)
        saved = settings.load().get("model") or ""
        if not saved or saved not in top:  # 미설정/목록 밖이면 1위를 기본 선택
            saved = top[0] if top else ""
            settings.save(model=saved)
        self._set_model_chips(top, saved)

    def _on_fail(self, msg: str) -> None:
        self._verify_btn.setEnabled(True)
        self._status.setText(LANG.m(STR, "verify_fail").format(msg))

    def _set_model_chips(self, models: list[str], selected: str) -> None:
        for b in self._chip_group.buttons():
            self._chip_group.removeButton(b)
        clear_layout(self._chips_lay)
        for m in models:
            c = chip(m)
            c.setChecked(m == selected)
            c.clicked.connect(lambda _=False, mid=m: settings.save(model=mid))
            self._chip_group.addButton(c)
            self._chips_lay.addWidget(c)

    def retranslate(self) -> None:
        self._title.setText(LANG.m(STR, "title"))
        self._key_lb.setText(LANG.m(STR, "key_label"))
        self._key.setPlaceholderText(LANG.m(STR, "key_ph"))
        self._key_hint.setText(LANG.m(STR, "key_hint"))
        self._verify_btn.setText(LANG.m(STR, "verify"))
        self._model_lb.setText(LANG.m(STR, "rec_models"))
        self._howto.setText(LANG.m(STR, "howto"))
        for i, st in enumerate(self._steps, 1):
            st.setText(LANG.m(STR, f"step{i}"))


if __name__ == "__main__":  # smoke: build + top5 ranking + chip select headless
    import os
    import sys
    import tempfile

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("LOCAL_DATA_DIR", tempfile.mkdtemp())
    sys.path.insert(0, r"C:\Users\JungSu\Desktop\wawa-ai-coach\backend")

    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    tab = SettingsTab()
    got = _top_models([
        "meta/llama-3.3-70b-instruct", "openai/gpt-oss-20b", "openai/gpt-oss-120b",
        "qwen/qwen3-235b-a22b", "deepseek-ai/deepseek-r1", "x/tiny",
    ])
    assert got == [
        "deepseek-ai/deepseek-r1", "openai/gpt-oss-120b", "qwen/qwen3-235b-a22b",
        "meta/llama-3.3-70b-instruct", "openai/gpt-oss-20b",
    ], got
    tab._on_models(["openai/gpt-oss-120b", "meta/llama-3.3-70b-instruct", "deepseek-ai/deepseek-r1"])
    assert len(tab._chip_group.buttons()) == 3  # 목록이 3개뿐이면 3칩
    for code in ("ko", "en", "ja", "zhHans"):
        LANG.set(code)
        tab.retranslate()
    print("settings ok")
