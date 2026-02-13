# Agente de Precos

Interface Streamlit + API FastAPI para processamento de planilhas de precos.

## Requisitos
- Windows com PowerShell
- Python 3.10+
- pip

## Instalacao automatica (Windows)
Opcao 1 (mais simples):
```bat
.\instalar.bat
```

Opcao 2 (PowerShell):
```powershell
.\install.ps1
```

Se quiser pular a instalacao do browser do Playwright:
```powershell
.\install.ps1 -SkipPlaywright
```

Ao final da instalacao, use:
```bat
.\iniciar.bat
```

## Ativar .venv manualmente (Windows)
PowerShell (shell atual):
```powershell
. .\.venv\Scripts\Activate.ps1
```

CMD:
```bat
.\.venv\Scripts\activate.bat
```

## Instalacao manual
```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r App/requirements.txt
```

## Acesso remoto seguro (PC e celular)
Defina variaveis antes de rodar:

```powershell
$env:APP_AUTH_USER="admin"
$env:APP_AUTH_PASSWORD="troque-esta-senha-forte"
$env:UI_HOST="0.0.0.0"
$env:UI_PORT="8501"
$env:API_HOST="127.0.0.1"
$env:API_PORT="8000"
```

Inicie:
```powershell
.\run.ps1
```

Acesse pelo navegador de outro dispositivo usando o IP da maquina:
```text
http://SEU_IP_LOCAL:8501
```

Observacoes de seguranca:
- A UI pede login quando `APP_AUTH_USER` e `APP_AUTH_PASSWORD` estao definidos.
- A API usa `API_TOKEN` automaticamente na sessao de execucao.
- Mantenha `API_HOST=127.0.0.1` para nao expor a API na rede.
- Libere no firewall apenas a porta da UI (padrao 8501).

## HTTPS (recomendado fora da rede local)
Se tiver certificado e chave:

```powershell
$env:SSL_CERT_FILE="C:\caminho\cert.pem"
$env:SSL_KEY_FILE="C:\caminho\key.pem"
.\run.ps1
```

## Rodando API (FastAPI)
```bash
uvicorn ui.server:app --host 127.0.0.1 --port 8000
```

## Rodando UI (Streamlit)
```bash
streamlit run ui_streamlit/app.py --server.address 0.0.0.0 --server.port 8501
```

## API_BASE (opcional)
Por padrao, a UI usa `http://127.0.0.1:8000`.

CMD:
```bat
set API_BASE=http://127.0.0.1:8001
streamlit run ui_streamlit/app.py
```

PowerShell:
```powershell
$env:API_BASE="http://127.0.0.1:8001"
streamlit run ui_streamlit/app.py
```

## Rodar tudo com um comando (PowerShell)
```powershell
.\run.ps1
```

## Rodar tudo com um comando (Codespaces/Linux)
```bash
bash ./run.sh
```
