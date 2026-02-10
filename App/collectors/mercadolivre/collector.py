from __future__ import annotations

from selenium.webdriver.remote.webdriver import WebDriver

from .context import carregar_pagina, extrair_estado_json
from .pricing import extrair_avista
from .installments import extrair_parcelamento
from .pix import extrair_pix
from .dom import (
    produto_disponivel_dom,
    pagina_login_detectada,
    extrair_avista_dom,
    extrair_parcelamento_dom,
    extrair_seller_dom,
)


def coletar(driver: WebDriver, link: str | None = None) -> dict:
    """
    Coletor Mercado Livre.
    Retorna exatamente o que o cliente vê na página,
    com prioridade de seller.
    """

    resultado = {
        "avista": None,
        "pix": None,
        "prazo": None,
        "status": "ML — NÃO EXECUTADO",
    }

    # ---------------- validação básica ----------------
    if not link or "mercadolivre.com.br" not in link:
        resultado["status"] = "ML — LINK INVÁLIDO"
        return resultado

    try:
        # ---------------- carregar página ----------------
        carregar_pagina(driver, link)

        # 🚨 BLOQUEIO / LOGIN
        if pagina_login_detectada(driver):
            resultado["status"] = "ML — LOGIN / BLOQUEIO DE SESSÃO"
            return resultado

        # ---------------- disponibilidade real ----------------
        if not produto_disponivel_dom(driver):
            resultado["status"] = "ML — PRODUTO INDISPONÍVEL"
            return resultado

        # ---------------- seller ativo ----------------
        seller = extrair_seller_dom(driver)

        # ---------------- tentativa via JSON ----------------
        state = extrair_estado_json(driver)

        if isinstance(state, dict):
            avista = extrair_avista(state)
            prazo = extrair_parcelamento(state)
            pix = extrair_pix(state)

            if avista or prazo:
                resultado.update(
                    {
                        "avista": avista,
                        "pix": pix,
                        "prazo": prazo,
                        "status": (
                            "OK — MERCADO LIVRE (JSON) — SELLER PROBEL"
                            if seller and "probel" in seller.lower()
                            else f"OK — MERCADO LIVRE (JSON) — SELLER {seller or 'NÃO IDENTIFICADO'}"
                        ),
                    }
                )
                return resultado

        # ---------------- fallback DOM ----------------
        avista_dom = extrair_avista_dom(driver)
        prazo_dom = extrair_parcelamento_dom(driver)

        if avista_dom:
            resultado.update(
                {
                    "avista": avista_dom,
                    "pix": None,
                    "prazo": prazo_dom,
                    "status": (
                        "OK — MERCADO LIVRE (DOM) — SELLER PROBEL"
                        if seller and "probel" in seller.lower()
                        else f"OK — MERCADO LIVRE (DOM) — SELLER {seller or 'NÃO IDENTIFICADO'}"
                    ),
                }
            )
            return resultado

        # ---------------- nada encontrado ----------------
        resultado["status"] = "ML — PREÇO NÃO IDENTIFICADO"
        return resultado

    except Exception as e:
        resultado["status"] = f"ML — FALHA CONTROLADA: {type(e).__name__}"
        return resultado
