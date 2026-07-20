# Build the native single-file exe. Output: backend\dist\<app>.exe (double-click; no Python/uv/Node/browser).
# The native PySide6 app calls the engine directly; the web frontend is not built here.
# ASCII-only on purpose: Windows PowerShell 5.1 mis-parses non-ASCII source, so the spec is named app.spec
# (the Korean product name lives inside app.spec, which PyInstaller reads as UTF-8).
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "Packaging exe (PyInstaller)..." -ForegroundColor Cyan
Push-Location "$root\backend"
uv run pyinstaller --noconfirm --clean app.spec
Pop-Location

Write-Host "Done. Artifact in backend\dist\ (double-click to run)." -ForegroundColor Green
