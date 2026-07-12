# Bring up all wuwahelper.com services if they aren't already listening.
# Idempotent (skips any port already UP) and console-independent: every service is
# launched detached (Start-Process, hidden), so closing a terminal never kills them.
# Run manually any time, or via the "WuWaHelper Services" scheduled task at logon.

$root   = "C:\Users\JungSu\Desktop\wawa-ai-coach"
$be     = Join-Path $root "backend"
$fe     = Join-Path $root "frontend"
$cad    = Join-Path $root "caddy"
$llmExe = "C:\Users\JungSu\llm\llama.cpp\llama-server.exe"
$model  = "C:\Users\JungSu\llm\models\gemma-4-12b-qat\gemma-4-12B-it-qat-UD-Q4_K_XL.gguf"
$mmproj = "C:\Users\JungSu\llm\models\gemma-4-12b-qat\mmproj-F16.gguf"

$logs = "C:\Users\JungSu\wuwahelper-logs"
New-Item -ItemType Directory -Force $logs | Out-Null
$launchLog = Join-Path $logs "launch.log"

function Log([string]$Msg) {
    $line = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Msg
    Add-Content -Path $launchLog -Value $line
    Write-Output $Msg
}

function Test-PortUp([int]$Port) {
    [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

# NOTE: the parameter is $ArgList, NOT $Args — $Args is a PowerShell automatic
# variable and using it as a param name silently corrupts -ArgumentList, so the
# process never launches (only a "started" line is printed). Do not rename it back.
function Start-Svc([string]$Name, [string]$Exe, [string[]]$ArgList, [string]$Cwd) {
    try {
        $p = Start-Process -FilePath $Exe -ArgumentList $ArgList -WorkingDirectory $Cwd `
            -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $logs "$Name.out.log") `
            -RedirectStandardError  (Join-Path $logs "$Name.err.log") `
            -PassThru -ErrorAction Stop
        Log "started $Name (pid $($p.Id))"
    } catch {
        Log "FAILED to start $Name : $($_.Exception.Message)"
    }
}

Log "=== start-services run ==="

# 1) llama.cpp vision/LLM server (8080)
if (Test-PortUp 8080) { Log "llama-server: already up" } else {
    Start-Svc "llama" $llmExe @("--model",$model,"--mmproj",$mmproj,"--jinja","--reasoning-budget","0","-ngl","99","--ctx-size","16384","--parallel","1","--no-mmap","--host","127.0.0.1","--port","8080","--alias","wuwa-vlm") $be
}

# 2) FastAPI backend (8000) — loads backend/.env (DATABASE_URL, LLM_BASE_URL)
if (Test-PortUp 8000) { Log "backend: already up" } else {
    Start-Svc "backend" (Join-Path $be ".venv\Scripts\uvicorn.exe") @("main:app","--host","127.0.0.1","--port","8000") $be
}

# 3) Next.js frontend prod (3000)
if (Test-PortUp 3000) { Log "frontend: already up" } else {
    Start-Svc "frontend" "cmd.exe" @("/c","npx next start -H 127.0.0.1 -p 3000") $fe
}

# 4) Caddy TLS reverse proxy (443 -> 3000) — needs elevation to bind 443
if (Test-PortUp 443) { Log "caddy: already up" } else {
    Start-Svc "caddy" (Join-Path $cad "caddy.exe") @("run","--config","Caddyfile") $cad
}
