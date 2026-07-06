$ErrorActionPreference = "Stop"

$hostsPath = "C:\Windows\System32\drivers\etc\hosts"
$entries = @(
  "127.0.0.1 wawahelper.com",
  "::1 wawahelper.com"
)

$content = Get-Content -LiteralPath $hostsPath -ErrorAction Stop
foreach ($entry in $entries) {
  if ($content -notcontains $entry) {
    Add-Content -LiteralPath $hostsPath -Value $entry
  }
}

ipconfig /flushdns | Out-Null
Write-Host "wawahelper.com now points to this computer."
