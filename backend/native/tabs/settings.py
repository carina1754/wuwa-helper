"""설정 탭 — BYO NVIDIA 키(자동저장) + 모델 선택 + 이용안내."""
from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from .. import engine, settings
from ..lang import LANG
from ..widgets import card, hsep, label, vbox

STR = {
    "ko": {
        "title": "설정", "key_label": "NVIDIA API 키",
        "key_ph": "nvapi-…", "key_hint": "이 키는 이 컴퓨터에만 저장되며 서버로 전송되지 않습니다.",
        "model": "모델", "load_models": "모델 불러오기", "loading": "불러오는 중…",
        "no_key": "먼저 API 키를 입력하세요.", "load_fail": "모델 목록을 가져오지 못했습니다: {}",
        "saved": "저장됨", "howto": "사용 방법",
        "step1": "1. NVIDIA build.nvidia.com 에서 무료 API 키를 발급받습니다.",
        "step2": "2. 위 칸에 키를 붙여넣으면 자동 저장됩니다.",
        "step3": "3. ‘모델 불러오기’로 사용할 모델을 고릅니다.",
        "step4": "4. AI 코치 탭에서 대화하며 빌드 추천을 받습니다.",
    },
    "en": {
        "title": "Settings", "key_label": "NVIDIA API Key",
        "key_ph": "nvapi-…", "key_hint": "Stored only on this computer; never sent to any server.",
        "model": "Model", "load_models": "Load models", "loading": "Loading…",
        "no_key": "Enter an API key first.", "load_fail": "Failed to fetch models: {}",
        "saved": "Saved", "howto": "How to use",
        "step1": "1. Get a free API key at NVIDIA build.nvidia.com.",
        "step2": "2. Paste it above — it saves automatically.",
        "step3": "3. Click ‘Load models’ and pick one.",
        "step4": "4. Chat in the AI Coach tab for build advice.",
    },
    "ja": {
        "title": "設定", "key_label": "NVIDIA API キー",
        "key_ph": "nvapi-…", "key_hint": "このキーはこのPCにのみ保存され、サーバーには送信されません。",
        "model": "モデル", "load_models": "モデルを読み込む", "loading": "読み込み中…",
        "no_key": "先にAPIキーを入力してください。", "load_fail": "モデル一覧の取得に失敗しました: {}",
        "saved": "保存しました", "howto": "使い方",
        "step1": "1. NVIDIA build.nvidia.com で無料APIキーを取得します。",
        "step2": "2. 上の欄に貼り付けると自動保存されます。",
        "step3": "3. 「モデルを読み込む」で使うモデルを選びます。",
        "step4": "4. AIコーチタブで会話しビルド提案を受けます。",
    },
    "zhHans": {
        "title": "设置", "key_label": "NVIDIA API 密钥",
        "key_ph": "nvapi-…", "key_hint": "仅保存在本机，不会发送到任何服务器。",
        "model": "模型", "load_models": "加载模型", "loading": "加载中…",
        "no_key": "请先输入 API 密钥。", "load_fail": "获取模型列表失败：{}",
        "saved": "已保存", "howto": "使用方法",
        "step1": "1. 在 NVIDIA build.nvidia.com 获取免费 API 密钥。",
        "step2": "2. 粘贴到上方，自动保存。",
        "step3": "3. 点击“加载模型”并选择一个。",
        "step4": "4. 在 AI 教练标签页对话以获取配装建议。",
    },
}


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
        self._key = QLineEdit(s.get("nvidia_key", ""))
        self._key.setEchoMode(QLineEdit.Password)
        self._key.textChanged.connect(self._on_key)
        bl.addWidget(self._key)
        self._key_hint = label("", "Muted", wrap=True)
        bl.addWidget(self._key_hint)
        bl.addWidget(hsep())

        self._model_lb = label("", "H2")
        bl.addWidget(self._model_lb)
        self._model = QComboBox()
        self._model.setEditable(True)
        if s.get("model"):
            self._model.addItem(s["model"])
            self._model.setCurrentText(s["model"])
        self._model.currentTextChanged.connect(self._on_model)
        bl.addWidget(self._model)
        self._load_btn = QPushButton()
        self._load_btn.clicked.connect(self._load_models)
        bl.addWidget(self._load_btn, 0, Qt.AlignLeft)
        self._status = label("", "Faint")
        bl.addWidget(self._status)
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

        self.retranslate()

    # --- persistence (auto-save) --------------------------------------------
    def _on_key(self, text: str) -> None:
        settings.save(nvidia_key=text.strip())

    def _on_model(self, text: str) -> None:
        settings.save(model=text.strip())

    def _load_models(self) -> None:
        if not self._key.text().strip():
            self._status.setText(LANG.m(STR, "no_key"))
            return
        self._load_btn.setEnabled(False)
        self._status.setText(LANG.m(STR, "loading"))
        self._worker = _ModelsWorker()
        self._worker.done.connect(self._on_models)
        self._worker.failed.connect(self._on_models_fail)
        self._worker.start()

    def _on_models(self, models: list) -> None:
        self._load_btn.setEnabled(True)
        current = self._model.currentText()
        self._model.clear()
        self._model.addItems(models)
        if current:
            self._model.setCurrentText(current)
        self._status.setText("")

    def _on_models_fail(self, msg: str) -> None:
        self._load_btn.setEnabled(True)
        self._status.setText(LANG.m(STR, "load_fail").format(msg))

    def retranslate(self) -> None:
        self._title.setText(LANG.m(STR, "title"))
        self._key_lb.setText(LANG.m(STR, "key_label"))
        self._key.setPlaceholderText(LANG.m(STR, "key_ph"))
        self._key_hint.setText(LANG.m(STR, "key_hint"))
        self._model_lb.setText(LANG.m(STR, "model"))
        self._load_btn.setText(LANG.m(STR, "load_models"))
        self._howto.setText(LANG.m(STR, "howto"))
        for i, st in enumerate(self._steps, 1):
            st.setText(LANG.m(STR, f"step{i}"))
