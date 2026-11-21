# JomiGuard demo health check. Read-only except: starts containers that are not running.
# Never touches cloudflared. Run from anywhere:  powershell -ExecutionPolicy Bypass -File C:\JomIGuard\scripts\health.ps1
param(
    [string]$PublicUrl = "https://framing-enables-thru-blocks.trycloudflare.com/"
)

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$problems = 0

function Report([bool]$ok, [string]$what, [string]$detail) {
    if ($ok) { Write-Host ("OK       {0}  {1}" -f $what, $detail) -ForegroundColor Green }
    else { Write-Host ("PROBLEM  {0}  {1}" -f $what, $detail) -ForegroundColor Red; $script:problems++ }
}

function Get-Status([string]$url) {
    try { return (Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 20).StatusCode }
    catch {
        if ($_.Exception.Response) { return [int]$_.Exception.Response.StatusCode }
        return 0
    }
}

# 1. containers: every service in docker-compose.yml must be running
$all = @(docker compose config --services)
$running = @(docker compose ps --services --filter "status=running")
$down = @($all | Where-Object { $running -notcontains $_ })
if ($down.Count -eq 0) {
    Report $true "containers" ("all {0} running" -f $all.Count)
} else {
    Report $false "containers" ("not running: {0} -> starting them" -f ($down -join ", "))
    docker compose up -d @down
    Start-Sleep -Seconds 15
    $running = @(docker compose ps --services --filter "status=running")
    $still = @($down | Where-Object { $running -notcontains $_ })
    Report ($still.Count -eq 0) "containers (after start)" ($(if ($still.Count) { "still down: " + ($still -join ", ") } else { "all running now" }))
}

# 2. local site, 3. public tunnel URL, 4. sentinel (satellite service)
$code = Get-Status "http://localhost:3000/"
Report ($code -eq 200) "local site  http://localhost:3000" ("HTTP {0}" -f $code)

$code = Get-Status $PublicUrl
Report ($code -eq 200) ("public URL  {0}" -f $PublicUrl) ("HTTP {0}" -f $code)
if ($code -ne 200 -and -not (Get-Process cloudflared -ErrorAction SilentlyContinue)) {
    Write-Host "         cloudflared is not running: see 'If the PC restarts' in the notes." -ForegroundColor Yellow
}

$code = Get-Status "http://localhost:5060/healthz"
Report ($code -eq 200) "sentinel    http://localhost:5060/healthz" ("HTTP {0}" -f $code)

if ($problems -eq 0) { Write-Host "ALL OK" -ForegroundColor Green; exit 0 }
Write-Host ("{0} PROBLEM(S)" -f $problems) -ForegroundColor Red
exit 1
