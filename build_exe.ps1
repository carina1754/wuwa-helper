# 띵조 AI 단일 exe 빌드. 산출물: backend\dist\띵조AI.exe (더블클릭 실행, 파이썬/uv/브라우저 불필요).
# 최초 1회 Node.js 필요(프론트 빌드). 이후 코드 안 바뀌면 재빌드 불필요.
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "[1/3] 프론트 정적 빌드..." -ForegroundColor Cyan
Push-Location "$root\frontend"
$env:NEXT_PUBLIC_API_BASE_URL = ""   # 같은 오리진 상대경로 fetch
npx next build
Pop-Location

Write-Host "[2/3] backend/static 갱신..." -ForegroundColor Cyan
$static = "$root\backend\static"
if (Test-Path $static) { Remove-Item -Recurse -Force $static }
Copy-Item -Recurse "$root\frontend\out" $static

Write-Host "[3/3] exe 패키징(PyInstaller)..." -ForegroundColor Cyan
Push-Location "$root\backend"
uv run pyinstaller --noconfirm --clean "띵조AI.spec"
Pop-Location

Write-Host "완료: backend\dist\띵조AI.exe 더블클릭." -ForegroundColor Green
