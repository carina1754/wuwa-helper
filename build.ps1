# 스탠드얼론 빌드: 프론트 정적 export → backend/static 복사. 코드 바뀌면 재실행.
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

Write-Host "[3/3] 완료. start.bat 로 실행하세요." -ForegroundColor Green
