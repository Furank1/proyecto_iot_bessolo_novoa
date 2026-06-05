# =====================================================================
#  Levanta el entorno del proyecto (Docker, Mosquitto, contenedores).
#  Los datos vienen de los ESP32 fisicos.
#
#  Uso:  powershell -ExecutionPolicy Bypass -File start_real.ps1
# =====================================================================
$base = "c:\Users\javie\OneDrive\Escritorio\Universidad\IoT"

# --- 1) Docker Desktop ---
Write-Host "1) Docker Desktop..." -ForegroundColor Cyan
docker ps 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "   Iniciando Docker Desktop (puede tardar ~1 min)..."
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    $i = 0
    while ($i -lt 60) { Start-Sleep -Seconds 3; docker ps 2>$null | Out-Null; if ($LASTEXITCODE -eq 0) { break }; $i++ }
}
docker ps 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host "   ERROR: Docker no respondio." -ForegroundColor Red; return }
Write-Host "   Docker OK" -ForegroundColor Green

# --- 2) Mosquitto ---
Write-Host "2) Mosquitto..." -ForegroundColor Cyan
if (-not (Get-Process mosquitto -ErrorAction SilentlyContinue)) {
    try { Start-Service mosquitto -ErrorAction Stop } catch {
        Start-Process "C:\Program Files\mosquitto\mosquitto.exe" -ArgumentList '-c', '"C:\Program Files\mosquitto\mosquitto.conf"'
    }
    Start-Sleep -Seconds 2
}
Write-Host "   Mosquitto OK" -ForegroundColor Green

# --- 3) Contenedores ---
Write-Host "3) Contenedores Node-RED + face-service..." -ForegroundColor Cyan
docker stop mynodered 2>$null | Out-Null
docker compose -f "$base\nodered-debian\docker-compose.yml" up -d 2>$null | Out-Null
Write-Host "   nodered-debian + face-service OK" -ForegroundColor Green

# --- 4) Recordatorio de IP para los sketches ---
Write-Host "4) IP de la laptop para los sketches (mqtt_server):" -ForegroundColor Cyan
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like '*Wi-Fi*' -and $_.IPAddress -notlike '169.*' } | ForEach-Object { Write-Host "   $($_.IPAddress)" -ForegroundColor Yellow }

# --- 5) Abrir el panel ---
Start-Sleep -Seconds 3
Start-Process "http://localhost:1880/ui"

Write-Host "`nListo. Prende los ESP32 con la IP de arriba en el sketch." -ForegroundColor Green
Write-Host "  Editor:    http://localhost:1880"
Write-Host "  Dashboard: http://localhost:1880/ui"