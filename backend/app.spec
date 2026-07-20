# PyInstaller spec — 띵조 AI 네이티브 Qt 단일 exe. `uv run pyinstaller 띵조AI.spec` (backend 폴더).
# 웹 스택(webview/uvicorn/static) 없음 — 엔진 직접 호출하는 PySide6 앱만 패키징.
# PySide6 Qt 플러그인/DLL 은 PyInstaller 내장 훅이 처리(collect_all 불필요).

# 번들 리소스: 카탈로그/콘텐츠 데이터(JSON 정본) + 이미지(아이콘).
datas = [("data", "data"), ("media", "media")]

a = Analysis(
    ["run_native.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    # psycopg 는 제외 금지: database.py 가 로드 시 import(휴면). 서버 스택만 제외.
    excludes=["webview", "clr_loader", "clr", "uvicorn", "fastapi"],
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
