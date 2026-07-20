"""메인 윈도우 셸 — 탭바 한 줄(우측 테마 토글) + 7탭. 웹 App 셸 대체."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QWidget,
)

from .lang import LANG
from .theme import THEME
from .tabs.ai import AiTab
from .tabs.codex import CodexTab
from .tabs.history import HistoryTab
from .tabs.pickup import PickupTab
from .tabs.settings import SettingsTab
from .tabs.teams import TeamsTab
from .tabs.updates import UpdatesTab
from .widgets import vbox

# (title_key, factory). 순서 = 탭 순서. 기본 선택 = 업데이트.
_TABS = [
    ("tab_ai", AiTab),
    ("tab_codex", CodexTab),
    ("tab_pickup", PickupTab),
    ("tab_updates", UpdatesTab),
    ("tab_teams", TeamsTab),
    ("tab_history", HistoryTab),
    ("tab_settings", SettingsTab),
]
_DEFAULT_TAB = 3  # updates


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.resize(1180, 820)
        central = QWidget()
        self.setCentralWidget(central)
        root = vbox(central, margins=(0, 6, 0, 0), spacing=0)

        # 제목줄 없음(창 타이틀바가 앱명) — 탭바 오른쪽 코너에 테마 토글만 얹어 한 줄 구성
        self._tabs = QTabWidget()
        self._theme_btn = QPushButton()
        self._theme_btn.setObjectName("IconBtn")
        self._theme_btn.setCursor(Qt.PointingHandCursor)
        self._theme_btn.clicked.connect(THEME.toggle)
        self._tabs.setCornerWidget(self._theme_btn, Qt.TopRightCorner)

        self._tab_widgets: list[QWidget] = []
        self._tab_keys = [k for k, _ in _TABS]
        for _key, factory in _TABS:
            w = factory()
            self._tab_widgets.append(w)
            self._tabs.addTab(w, "")
        self._tabs.setCurrentIndex(_DEFAULT_TAB)
        # 탭 진입 시 최신화(예: 파티 계산이 저장한 기록을 기록 탭이 다시 읽음)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        root.addWidget(self._tabs, 1)

        THEME.changed.connect(self._apply_theme)
        LANG.changed.connect(self._retranslate)
        self._apply_theme()
        self._retranslate()

    # --- reactive wiring ----------------------------------------------------
    def _on_tab_changed(self, index: int) -> None:
        fn = getattr(self._tabs.widget(index), "refresh", None)
        if callable(fn):
            fn()

    def _apply_theme(self) -> None:
        # 앱 전역에 적용 → 별도 top-level 다이얼로그(도감 상세)도 테마 상속
        QApplication.instance().setStyleSheet(THEME.qss())
        self._theme_btn.setText("☀" if THEME.dark else "🌙")

    def _retranslate(self) -> None:
        for i, key in enumerate(self._tab_keys):
            self._tabs.setTabText(i, LANG.t(key))
        for w in self._tab_widgets:
            fn = getattr(w, "retranslate", None)
            if callable(fn):
                fn()
