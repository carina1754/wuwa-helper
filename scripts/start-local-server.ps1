$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

Start-Process -FilePath "powershell.exe" -ArgumentList @(
  "-NoProfile",
  "-ExecutionPolicy",
  "Bypass",
  "-Command",
  "cd '$backend'; uv run uvicorn main:app --host 127.0.0.1 --port 8000"
) -WorkingDirectory $backend

Start-Process -FilePath "powershell.exe" -ArgumentList @(
  "-NoProfile",
  "-ExecutionPolicy",
  "Bypass",
  "-Command",
  "cd '$frontend'; npm exec next -- dev --experimental-https --hostname 0.0.0.0 --port 443"
) -WorkingDirectory $frontend

Write-Host "Started backend on http://127.0.0.1:8000"
Write-Host "Started frontend on https://wawahelper.com"
