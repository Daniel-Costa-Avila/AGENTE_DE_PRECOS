from __future__ import annotations

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

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

st.set_page_config(
    page_title="Price Monitor",
    layout="wide",
)

# ---------------- HEADER ----------------

st.title("📊 Price Monitor — Price Agent")
st.caption("Coleta automática de preços a partir de planilhas")

# ---------------- MODELO ----------------

st.subheader("📥 Modelo de planilha")
st.markdown(
    """
    Utilize **exclusivamente** o modelo oficial para preencher os produtos.
    Não altere o nome das colunas.
    """
)

with open(MODEL_FILE, "rb") as f:
    st.download_button(
        label="📥 Baixar modelo de planilha",
        data=f,
        file_name="modelo_input.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.divider()

# ---------------- MANUAL ----------------

st.subheader("📘 Como utilizar o sistema")

with st.expander("Clique aqui para ver o passo a passo"):
    st.markdown(
        """
        ### 1. Baixe o modelo de planilha
        Utilize o botão acima para baixar o arquivo padrão.

        ### 2. Preencha a planilha
        - **id_produto**: código interno (obrigatório)
        - **titulo**: nome do produto (opcional)
        - **link**: URL do produto (obrigatório)

        ⚠️ Não altere o nome das colunas.

        ### 3. Envie a planilha
        Faça o upload do arquivo preenchido no campo abaixo.

        ### 4. Processamento automático
        Clique em **Processar automaticamente** e aguarde.

        ### 5. Resultado
        Ao final, será possível visualizar e baixar o arquivo com os preços.

        ---
        **Regra de Ouro:**  
        > Melhor nenhum dado do que um dado errado.
        """
    )

st.divider()

# ---------------- UPLOAD ----------------

st.subheader("📤 Enviar planilha preenchida")

uploaded = st.file_uploader(
    "Selecione o arquivo .xlsx",
    type=["xlsx"],
)

uploaded_bytes: bytes | None = None
df_input = None

if uploaded:
    uploaded_bytes = uploaded.getbuffer().tobytes()
    df_input = pd.read_excel(BytesIO(uploaded_bytes))
    st.success(f"Planilha carregada com {len(df_input)} produtos.")
    st.dataframe(df_input, use_container_width=True)
else:
    if DEFAULT_INPUT.exists():
        st.info("Nenhuma planilha enviada. Usaremos o input.xlsx padrão.")
    else:
        st.warning("Envie uma planilha .xlsx para continuar.")

st.divider()

# ---------------- PROCESSAMENTO ----------------

if "job_id" not in st.session_state:
    st.session_state.job_id = None


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
    resp = requests.post(f"{API_BASE}/api/run", files=files, timeout=30)
    if resp.status_code == 429:
        st.error("Limite de execuções simultâneas atingido. Tente novamente.")
        return None
    if not resp.ok:
        st.error(f"Falha ao iniciar job: {resp.status_code}")
        return None
    data = resp.json()
    return data.get("job_id")


def _get_status(job_id: str):
    resp = requests.get(f"{API_BASE}/api/status/{job_id}", timeout=30)
    if not resp.ok:
        return None
    return resp.json()


if st.button("🚀 Processar automaticamente"):
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
    st.subheader("📡 Status da execução")

    status_placeholder = st.empty()
    data = _get_status(job_id)
    if data is None:
        status_placeholder.error("Não foi possível obter o status.")
    else:
        status_placeholder.info(f"Status: {data.get('status')}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Atualizar status"):
            data = _get_status(job_id)
            if data is None:
                status_placeholder.error("Não foi possível obter o status.")
            else:
                status_placeholder.info(f"Status: {data.get('status')}")

    with col2:
        if st.button("Acompanhar até concluir"):
            with st.spinner("Aguardando conclusão..."):
                for _ in range(240):
                    data = _get_status(job_id)
                    if data is None:
                        break
                    status_placeholder.info(f"Status: {data.get('status')}")
                    if data.get("status") in {"DONE", "FAILED"}:
                        break
                    time.sleep(5)

    if data and data.get("status") == "DONE":
        st.success("Processamento concluído com sucesso!")
        download_url = f"{API_BASE}/download/{job_id}"
        r = requests.get(download_url, timeout=60)
        if r.ok:
            st.download_button(
                "⬇️ Baixar resultados.xlsx",
                data=r.content,
                file_name=f"resultados_{job_id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            df_out = pd.read_excel(BytesIO(r.content))
            st.subheader("📊 Prévia do resultado")
            st.dataframe(df_out, use_container_width=True)
        else:
            st.error("Erro ao baixar o arquivo de saída.")
    elif data and data.get("status") == "FAILED":
        st.error("Falha na execução do job.")
