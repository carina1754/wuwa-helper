"""PyInstaller 진입 스크립트 — 네이티브 Qt 앱 부트. 패키지 컨텍스트 확보용 얇은 래퍼."""
from native.main import run

raise SystemExit(run())
