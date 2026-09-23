# Levanta Langflow + Postgres del copiloto MineTwin con Podman.
# Detecta las IPs de Windows para que los contenedores puedan llamar a MineTwin (npm run dev, puerto 3000).
# En Podman sobre WSL, host.containers.internal apunta a la VM y no a Windows; por eso se pasan las IPs.
#
# Uso (PowerShell, desde minetwin-ai):  .\langflow\start.ps1
# Primera vez, después de levantar:     python .\langflow\scripts\setup_flow.py

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$running = podman machine list --format '{{.Running}}' 2>$null
if ($running -notcontains 'true') {
    # Mensajes sin tildes: PowerShell 5.1 lee los .ps1 sin BOM como ANSI.
    Write-Host 'Iniciando Podman...'
    podman machine start
}

$wslIps = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.InterfaceAlias -like 'vEthernet (WSL*' } |
    Select-Object -ExpandProperty IPAddress
$otherIps = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' -and $_.InterfaceAlias -notlike 'vEthernet (WSL*' } |
    Select-Object -ExpandProperty IPAddress

$urls = @($wslIps) + @($otherIps) | Where-Object { $_ } | ForEach-Object { "http://${_}:3000" }
$env:MINETWIN_API_URL = ($urls + 'http://host.docker.internal:3000') -join ','
Write-Host "MINETWIN_API_URL=$env:MINETWIN_API_URL"

# --force-recreate aplica la variable aunque el contenedor ya exista.
podman compose up -d --force-recreate langflow postgres

Write-Host ''
Write-Host 'Langflow tarda ~1 minuto en arrancar: http://127.0.0.1:7861'
Write-Host 'Primera vez: python .\langflow\scripts\setup_flow.py'
