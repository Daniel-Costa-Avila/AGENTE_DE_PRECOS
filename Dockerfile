# 1) Dockerfile
cat > Dockerfile <<'DOCKER'
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dependências do Chrome
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates \
    fonts-liberation \
    libnss3 libxss1 libasound2 \
    libatk-bridge2.0-0 libgtk-3-0 \
    libx11-xcb1 libxcomposite1 libxdamage1 \
    libxrandr2 libgbm1 libu2f-udev libvulkan1 libdrm2 \
    && rm -rf /var/lib/apt/lists/*

# Google Chrome
RUN wget -qO- https://dl.google.com/linux/linux_signing_key.pub \
    | gpg --dearmor -o /usr/share/keyrings/google-linux-signing-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-signing-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
    > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY App/requirements.txt /app/App/requirements.txt
RUN pip install --no-cache-dir -r /app/App/requirements.txt

COPY . /app

ENV CHROME_BINARY=/usr/bin/google-chrome
ENV HEADLESS=1
DOCKER

# 2) docker-compose.yml
cat > docker-compose.yml <<'YAML'
services:
  api:
    build: .
    command: uvicorn ui.server:app --host 0.0.0.0 --port 8000
    environment:
      - HEADLESS=1
      - CHROME_BINARY=/usr/bin/google-chrome
      - PYTHONPATH=/app
    volumes:
      - ./runs:/app/runs
      - ./chrome_profile:/app/App/chrome_profile
    ports:
      - "8000:8000"
    shm_size: "1gb"
    restart: unless-stopped

  ui:
    build: .
    command: streamlit run ui_streamlit/app.py --server.address 0.0.0.0 --server.port 8501
    environment:
      - API_BASE=http://api:8000
      - PYTHONPATH=/app
    ports:
      - "8501:8501"
    depends_on:
      - api
    restart: unless-stopped
YAML

# 3) .dockerignore
cat > .dockerignore <<'IGNORE'
.git
.venv
__pycache__
*.pyc
runs
chrome_profile
Outputs
debug_magalu
App/chrome_profile
IGNORE

# 4) Scripts
mkdir -p scripts

cat > scripts/install.sh <<'BASH'
#!/usr/bin/env bash
set -euo pipefail

if ! command -v docker >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y ca-certificates curl gnupg
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo usermod -aG docker $USER
  echo "Docker instalado. Reabra a sessão SSH e rode novamente."
  exit 0
fi

docker compose up -d --build
echo "API : http://IP_DA_VM:8000"
echo "UI  : http://IP_DA_VM:8501"
BASH
chmod +x scripts/install.sh

cat > scripts/start.sh <<'BASH'
#!/usr/bin/env bash
docker compose up -d
BASH
chmod +x scripts/start.sh

cat > scripts/stop.sh <<'BASH'
#!/usr/bin/env bash
docker compose down
BASH
chmod +x scripts/stop.sh

cat > scripts/update.sh <<'BASH'
#!/usr/bin/env bash
set -euo pipefail
git pull
docker compose up -d --build
BASH
chmod +x scripts/update.sh

# 5) Windows installer assets
mkdir -p installer/windows

cat > installer/windows/start_app.ps1 <<'PS1'
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName PresentationFramework

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  [System.Windows.MessageBox]::Show(
    "Docker Desktop não encontrado. Instale o Docker Desktop e habilite WSL2.",
    "Agente de Preços"
  ) | Out-Null
  exit 1
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Resolve-Path (Join-Path $scriptDir "..\..")
Set-Location $root

docker compose up -d --build

[System.Windows.MessageBox]::Show(
  "Serviço iniciado. Acesse: http://IP_DA_MAQUINA:8501",
  "Agente de Preços"
) | Out-Null
PS1

cat > installer/windows/stop_app.ps1 <<'PS1'
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName PresentationFramework

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  [System.Windows.MessageBox]::Show(
    "Docker Desktop não encontrado.",
    "Agente de Preços"
  ) | Out-Null
  exit 1
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Resolve-Path (Join-Path $scriptDir "..\..")
Set-Location $root

docker compose down

[System.Windows.MessageBox]::Show(
  "Serviço parado.",
  "Agente de Preços"
) | Out-Null
PS1

cat > installer/windows/StartApp.vbs <<'VBS'
Set WshShell = CreateObject("WScript.Shell")
cmd = "powershell -ExecutionPolicy Bypass -File """ & WScript.ScriptFullName & "\..\start_app.ps1"""
WshShell.Run cmd, 0
VBS

cat > installer/windows/StopApp.vbs <<'VBS'
Set WshShell = CreateObject("WScript.Shell")
cmd = "powershell -ExecutionPolicy Bypass -File """ & WScript.ScriptFullName & "\..\stop_app.ps1"""
WshShell.Run cmd, 0
VBS

cat > installer/windows/AgentePrecos.iss <<'ISS'
[Setup]
AppName=Agente de Preços
AppVersion=1.0.0
DefaultDirName={pf}\Agente_de_Precos
DefaultGroupName=Agente de Preços
OutputDir=.
OutputBaseFilename=AgenteDePrecos-Installer
Compression=lzma
SolidCompression=yes

[Files]
Source: "..\..\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs; \
    Excludes: ".git;.venv;__pycache__;runs;chrome_profile;Outputs;debug_magalu;App\chrome_profile"

Source: "start_app.ps1"; DestDir: "{app}\installer\windows"; Flags: ignoreversion
Source: "stop_app.ps1"; DestDir: "{app}\installer\windows"; Flags: ignoreversion
Source: "StartApp.vbs"; DestDir: "{app}\installer\windows"; Flags: ignoreversion
Source: "StopApp.vbs"; DestDir: "{app}\installer\windows"; Flags: ignoreversion

[Icons]
Name: "{group}\Agente de Preços (Iniciar)"; Filename: "{app}\installer\windows\StartApp.vbs"
Name: "{group}\Agente de Preços (Parar)"; Filename: "{app}\installer\windows\StopApp.vbs"
Name: "{commondesktop}\Agente de Preços"; Filename: "{app}\installer\windows\StartApp.vbs"

[Run]
Filename: "{app}\installer\windows\StartApp.vbs"; Description: "Iniciar agora"; Flags: nowait postinstall
ISS

# 6) Ajuste em App/utils/browser.py (prioriza CHROME_BINARY)
python - <<'PY'
from pathlib import Path
p = Path("App/utils/browser.py")
text = p.read_text(encoding="utf-8")
old = "chrome_binary = _find_chrome_binary()"
new = "chrome_binary = os.getenv(\"CHROME_BINARY\") or _find_chrome_binary()"
if old in text:
    text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")
    print("browser.py atualizado.")
else:
    print("browser.py já estava atualizado.")
PY

# 7) Forçar headless via env em App/main.py
python - <<'PY'
from pathlib import Path
import re

p = Path("App/main.py")
text = p.read_text(encoding="utf-8")

pattern = r"get_driver\(headless=False\)"
replacement = "get_driver(headless=(os.getenv(\"HEADLESS\",\"1\").strip().lower() not in {\"0\",\"false\",\"no\",\"off\"}))"

if re.search(pattern, text):
    text = re.sub(pattern, replacement, text)
    p.write_text(text, encoding="utf-8")
    print("App/main.py atualizado para HEADLESS.")
else:
    print("App/main.py já estava atualizado.")
PY

# 8) README
cat >> README.md <<'MD'

## Instalacao Docker (Ubuntu 22/24)
```bash
./scripts/install.sh
