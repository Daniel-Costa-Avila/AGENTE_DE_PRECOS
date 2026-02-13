from __future__ import annotations

import hmac
import os
import time
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

# ---------------- CONFIG ----------------

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_FILE = BASE_DIR / "modelo_input.xlsx"
DEFAULT_INPUT = BASE_DIR / "input.xlsx"

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000").rstrip("/")
API_TOKEN = os.getenv("API_TOKEN", "").strip()

APP_AUTH_USER = os.getenv("APP_AUTH_USER", "").strip()
APP_AUTH_PASSWORD = os.getenv("APP_AUTH_PASSWORD", "").strip()
AUTH_ENABLED = bool(APP_AUTH_USER and APP_AUTH_PASSWORD)

st.set_page_config(
    page_title="Price Monitor",
    layout="wide",
)


def _api_headers() -> dict[str, str]:
    if API_TOKEN:
        return {"Authorization": f"Bearer {API_TOKEN}"}
    return {}


def _require_login() -> None:
    if not AUTH_ENABLED:
        st.warning(
            "Acesso sem login. Defina APP_AUTH_USER e APP_AUTH_PASSWORD para proteger acesso remoto."
        )
        return

    if st.session_state.get("app_authenticated"):
        with st.sidebar:
            st.caption("Sessao autenticada")
            if st.button("Sair"):
                st.session_state.app_authenticated = False
                st.rerun()
        return

    st.title("Login")
    st.caption("Acesso remoto protegido")
    with st.form("login_form"):
        user = st.text_input("Usuario")
        password = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar")

    if submit:
        user_ok = hmac.compare_digest(user, APP_AUTH_USER)
        pass_ok = hmac.compare_digest(password, APP_AUTH_PASSWORD)
        if user_ok and pass_ok:
            st.session_state.app_authenticated = True
            st.rerun()
        st.error("Credenciais invalidas.")

    st.stop()


_require_login()

# ---------------- HEADER ----------------

st.title("Price Monitor - Price Agent")
st.caption("Coleta automatica de precos a partir de planilhas")

# ---------------- MODELO ----------------

st.subheader("Modelo de planilha")
st.markdown(
    """
    Utilize exclusivamente o modelo oficial para preencher os produtos.
    Nao altere o nome das colunas.
    """
)

with open(MODEL_FILE, "rb") as f:
    st.download_button(
        label="Baixar modelo de planilha",
        data=f,
        file_name="modelo_input.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.divider()

# ---------------- MANUAL ----------------

st.subheader("Como utilizar o sistema")

with st.expander("Clique aqui para ver o passo a passo"):
    st.markdown(
        """
        ### 1. Baixe o modelo de planilha
        Utilize o botao acima para baixar o arquivo padrao.

        ### 2. Preencha a planilha
        - **id_produto**: codigo interno (obrigatorio)
        - **titulo**: nome do produto (opcional)
        - **link**: URL do produto (obrigatorio)

        Nao altere o nome das colunas.

        ### 3. Envie a planilha
        Faca o upload do arquivo preenchido no campo abaixo.

        ### 4. Processamento automatico
        Clique em **Processar automaticamente** e aguarde.

        ### 5. Resultado
        Ao final, sera possivel visualizar e baixar o arquivo com os precos.
        """
    )

st.divider()

# ---------------- UPLOAD ----------------

st.subheader("Enviar planilha preenchida")

uploaded = st.file_uploader(
    "Selecione o arquivo .xlsx",
    type=["xlsx"],
)

uploaded_bytes: bytes | None = None

if uploaded:
    uploaded_bytes = uploaded.getbuffer().tobytes()
    df_input = pd.read_excel(BytesIO(uploaded_bytes))
    st.success(f"Planilha carregada com {len(df_input)} produtos.")
    st.dataframe(df_input, use_container_width=True)
else:
    if DEFAULT_INPUT.exists():
        st.info("Nenhuma planilha enviada. Usaremos o input.xlsx padrao.")
    else:
        st.warning("Envie uma planilha .xlsx para continuar.")

st.divider()

# ---------------- PROCESSAMENTO ----------------

if "job_id" not in st.session_state:
    st.session_state.job_id = None


def _api_health():
    try:
        resp = requests.get(f"{API_BASE}/api/health", timeout=3)
    except requests.RequestException as exc:
        return False, str(exc)
    if resp.ok:
        return True, None
    return False, f"HTTP {resp.status_code}"


def _show_api_down(error: str | None = None):
    st.error(
        "API indisponivel. Inicie com ./run.ps1 ou uvicorn ui.server:app --host 127.0.0.1 --port 8000"
    )
    if error:
        st.caption(f"Detalhe: {error}")


def _start_job(file_bytes: bytes | None):
    files = None
    if file_bytes is not None:
        files = {
            "file": (
                "input.xlsx",
                file_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        }
    try:
        resp = requests.post(
            f"{API_BASE}/api/run",
            files=files,
            headers=_api_headers(),
            timeout=30,
        )
    except requests.RequestException as exc:
        _show_api_down(str(exc))
        return None
    if resp.status_code == 401:
        st.error("Falha de autenticacao com API. Verifique API_TOKEN.")
        return None
    if resp.status_code == 429:
        st.error("Limite de execucoes simultaneas atingido. Tente novamente.")
        return None
    if not resp.ok:
        st.error(f"Falha ao iniciar job: {resp.status_code}")
        return None
    data = resp.json()
    return data.get("job_id")


def _get_status(job_id: str):
    try:
        resp = requests.get(
            f"{API_BASE}/api/status/{job_id}",
            headers=_api_headers(),
            timeout=30,
        )
    except requests.RequestException as exc:
        _show_api_down(str(exc))
        return None
    if resp.status_code == 401:
        st.error("Falha de autenticacao com API. Verifique API_TOKEN.")
        return None
    if not resp.ok:
        return None
    return resp.json()


# ---------------- STATUS API ----------------

st.subheader("Status da API")
api_ok, api_err = _api_health()
if api_ok:
    st.success("API online.")
else:
    _show_api_down(api_err)

if st.button("Processar automaticamente"):
    if uploaded_bytes is None and not DEFAULT_INPUT.exists():
        st.error("Envie uma planilha .xlsx para iniciar.")
    else:
        job_id = _start_job(uploaded_bytes)
        if job_id:
            st.session_state.job_id = job_id
            st.success(f"Job iniciado: {job_id}")

job_id = st.session_state.job_id

if job_id:
    st.divider()
    st.subheader("Status da execucao")

    status_placeholder = st.empty()
    data = _get_status(job_id)
    if data is None:
        status_placeholder.error("Nao foi possivel obter o status.")
    else:
        status_placeholder.info(f"Status: {data.get('status')}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Atualizar status"):
            data = _get_status(job_id)
            if data is None:
                status_placeholder.error("Nao foi possivel obter o status.")
            else:
                status_placeholder.info(f"Status: {data.get('status')}")

    with col2:
        if st.button("Acompanhar ate concluir"):
            with st.spinner("Aguardando conclusao..."):
                for _ in range(240):
                    data = _get_status(job_id)
                    if data is None:
                        break
                    status_placeholder.info(f"Status: {data.get('status')}")
                    if data.get("status") in {"DONE", "FAILED"}:
                        break
                    time.sleep(5)

    if data and data.get("status") == "DONE":
        st.success("Processamento concluido com sucesso!")
        download_url = f"{API_BASE}/download/{job_id}"
        r = requests.get(download_url, headers=_api_headers(), timeout=60)
        if r.ok:
            st.download_button(
                "Baixar resultados.xlsx",
                data=r.content,
                file_name=f"resultados_{job_id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            df_out = pd.read_excel(BytesIO(r.content))
            st.subheader("Previa do resultado")
            st.dataframe(df_out, use_container_width=True)
        else:
            st.error("Erro ao baixar o arquivo de saida.")
    elif data and data.get("status") == "FAILED":
        st.error("Falha na execucao do job.")

