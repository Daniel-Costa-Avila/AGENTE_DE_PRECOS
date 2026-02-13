$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Resolve-VenvPython {
    $candidates = @(
        (Join-Path $root ".venv\Scripts\python.exe"),
        (Join-Path $root "venv\Scripts\python.exe")
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    return $null
}

function Get-RandomToken {
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    } finally {
        $rng.Dispose()
    }
    return [Convert]::ToBase64String($bytes)
}

$venvPython = Resolve-VenvPython
if (-not $venvPython) {
    Write-Error "Ambiente virtual nao encontrado em .\\.venv ou .\\venv. Execute .\\install.ps1 primeiro."
    exit 1
}

$apiHost = $env:API_HOST
if (-not $apiHost) { $apiHost = "127.0.0.1" }

$apiPort = $env:API_PORT
if (-not $apiPort) { $apiPort = "8000" }

if ($env:API_BASE) {
    $apiBase = $env:API_BASE
    try {
        $apiPort = ([Uri]$apiBase).Port
    } catch {
        $apiPort = "8000"
        $apiBase = "http://127.0.0.1:$apiPort"
    }
} else {
    $apiBase = "http://127.0.0.1:$apiPort"
}

$uiHost = $env:UI_HOST
if (-not $uiHost) { $uiHost = "0.0.0.0" }

$uiPort = $env:UI_PORT
if (-not $uiPort) { $uiPort = "8501" }

if (-not $env:API_TOKEN) {
    $env:API_TOKEN = Get-RandomToken
    Write-Host "API_TOKEN temporario gerado para esta sessao." -ForegroundColor Yellow
}

function Test-Api($url) {
    try {
        Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 "$url/api/health" | Out-Null
        return $true
    } catch {
        return $false
    }
}

if (-not (Test-Api $apiBase)) {
    $apiCmd = "& `"$venvPython`" -m uvicorn ui.server:app --host $apiHost --port $apiPort"
    Start-Process -FilePath "powershell" -WorkingDirectory $root -ArgumentList "-NoExit", "-Command", $apiCmd
    Start-Sleep -Seconds 2
}

$env:API_BASE = $apiBase

if (-not $env:APP_AUTH_USER -or -not $env:APP_AUTH_PASSWORD) {
    Write-Warning "APP_AUTH_USER/APP_AUTH_PASSWORD nao definidos. Defina para proteger acesso remoto da UI."
}

Write-Host ""
Write-Host "Acesso local: http://localhost:$uiPort" -ForegroundColor Cyan
try {
    $ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
        Where-Object { $_.IPAddress -ne "127.0.0.1" -and $_.IPAddress -notlike "169.254*" } |
        Select-Object -ExpandProperty IPAddress -Unique

    foreach ($ip in $ips) {
        Write-Host "Acesso remoto (rede): http://${ip}:$uiPort" -ForegroundColor Cyan
    }
} catch {}

$streamlitArgs = @(
    "-m", "streamlit", "run", "ui_streamlit/app.py",
    "--server.address", $uiHost,
    "--server.port", $uiPort
)

$sslCert = $env:SSL_CERT_FILE
$sslKey = $env:SSL_KEY_FILE
if ($sslCert -and $sslKey -and (Test-Path $sslCert) -and (Test-Path $sslKey)) {
    $streamlitArgs += @("--server.sslCertFile", $sslCert, "--server.sslKeyFile", $sslKey)
    Write-Host "HTTPS habilitado para Streamlit." -ForegroundColor Green
} elseif ($sslCert -or $sslKey) {
    Write-Warning "SSL_CERT_FILE/SSL_KEY_FILE invalidos. Iniciando sem HTTPS."
}

& $venvPython @streamlitArgs


