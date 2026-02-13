param(
    [switch]$SkipPlaywright
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Write-Step([string]$message) {
    Write-Host ""
    Write-Host "==> $message" -ForegroundColor Cyan
}

function Resolve-PythonCommand {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try {
            $v = & py -3 -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"
            if ([version]$v -ge [version]"3.10") {
                return "py -3"
            }
        } catch {}
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        try {
            $v = & python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"
            if ([version]$v -ge [version]"3.10") {
                return "python"
            }
        } catch {}
    }

    throw "Python 3.10+ nao encontrado. Instale Python e execute novamente."
}

function Resolve-VenvDirectory {
    $dotVenvDir = Join-Path $root ".venv"
    $legacyVenvDir = Join-Path $root "venv"

    if (Test-Path (Join-Path $dotVenvDir "Scripts\python.exe")) {
        return $dotVenvDir
    }

    if (Test-Path (Join-Path $legacyVenvDir "Scripts\python.exe")) {
        return $legacyVenvDir
    }

    return $dotVenvDir
}

function New-Launchers {
    $startBat = @"
@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1"
set EXIT_CODE=%ERRORLEVEL%
if not "%EXIT_CODE%"=="0" (
  echo.
  echo Erro ao iniciar o sistema. Codigo: %EXIT_CODE%
  pause
)
exit /b %EXIT_CODE%
"@
    Set-Content -Path (Join-Path $root "iniciar.bat") -Value $startBat -Encoding ascii
}

if (-not (Test-Path (Join-Path $root "App\requirements.txt"))) {
    throw "Arquivo App\requirements.txt nao encontrado. Execute o instalador na raiz do projeto."
}

$venvDir = Resolve-VenvDirectory
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$pythonCmd = Resolve-PythonCommand

if (-not (Test-Path $venvPython)) {
    Write-Step "Criando ambiente virtual em .\\.venv"
    Invoke-Expression "$pythonCmd -m venv .venv"
    $venvDir = Join-Path $root ".venv"
    $venvPython = Join-Path $venvDir "Scripts\python.exe"
} else {
    if ((Split-Path -Leaf $venvDir) -eq "venv") {
        Write-Step "Ambiente virtual legado detectado em .\\venv (recomendado migrar para .\\.venv)"
    } else {
        Write-Step "Ambiente virtual ja existe em .\\.venv"
    }
}

if (-not (Test-Path $venvPython)) {
    throw "Falha ao criar/achar o Python do venv em: $venvPython"
}

Write-Step "Atualizando pip/setuptools/wheel"
& $venvPython -m pip install --upgrade pip setuptools wheel

Write-Step "Instalando dependencias de App\requirements.txt"
& $venvPython -m pip install -r App\requirements.txt

if (-not $SkipPlaywright) {
    Write-Step "Instalando browser do Playwright (chromium)"
    try {
        & $venvPython -m playwright install chromium
    } catch {
        Write-Warning "Falha ao instalar chromium do Playwright. O sistema pode funcionar sem isso dependendo do fluxo."
        Write-Warning $_
    }
} else {
    Write-Step "Playwright ignorado por parametro -SkipPlaywright"
}

Write-Step "Criando atalho de inicio (iniciar.bat)"
New-Launchers

Write-Host ""
Write-Host "Instalacao concluida." -ForegroundColor Green
Write-Host "Para iniciar: .\\iniciar.bat"
Write-Host "Ou: .\\run.ps1"
Write-Host "Para ativar manualmente o venv no PowerShell: . .\\.venv\\Scripts\\Activate.ps1"
