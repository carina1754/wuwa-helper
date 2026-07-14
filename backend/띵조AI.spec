# PyInstaller spec — 띵조 AI 단일 exe. `uv run pyinstaller 띵조AI.spec` (backend 폴더에서).
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
# GUI(웹뷰)·서버 스택은 지연 import 가 많아 통째로 수집해야 누락 없음.
for pkg in ("webview", "clr_loader", "uvicorn"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# 번들 리소스: 정적 프론트 + 카탈로그/콘텐츠 데이터 + 이미지.
datas += [("static", "static"), ("data", "data"), ("media", "media")]

a = Analysis(
    ["desktop.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + ["clr"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],  # database.py 가 모듈 로드시 import psycopg(휴면 코드) → 제외 불가
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="띵조AI",
    console=False,          # 콘솔창 없음(진짜 프로그램)
    disable_windowed_traceback=False,
    upx=False,
)
