from __future__ import annotations

import re
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver


# ------------------------------------------------------------------
# LOGIN / BLOQUEIO
# ------------------------------------------------------------------

def pagina_login_detectada(driver: WebDriver) -> bool:
    """
    Detecta página de login / bloqueio do Mercado Livre.
    """
    try:
        elementos = driver.find_elements(
            By.XPATH,
            (
                "//*[contains(., 'acesse sua conta') "
                "or contains(., 'Sou novo') "
                "or contains(., 'Já tenho conta')]"
            ),
        )
        return bool(elementos)
    except Exception:
        return False


# ------------------------------------------------------------------
# DISPONIBILIDADE
# ------------------------------------------------------------------

def produto_disponivel_dom(driver: WebDriver) -> bool:
    """
    Produto disponível se existir CTA de compra ativo.
    """
    try:
        botoes_compra = driver.find_elements(
            By.XPATH,
            (
                "//button["
                "contains(., 'Comprar agora') "
                "or contains(., 'Adicionar ao carrinho')"
                "]"
            ),
        )

        if botoes_compra:
            return True

        avisos_indisponivel = driver.find_elements(
            By.XPATH,
            (
                "//*[contains(., 'Produto indisponível') "
                "or contains(., 'Publicação finalizada') "
                "or contains(., 'Avise-me')]"
            ),
        )

        if avisos_indisponivel:
            return False

    except Exception:
        # fail-safe: assume disponível
        return True

    return True


# ------------------------------------------------------------------
# PREÇO DOM
# ------------------------------------------------------------------

def extrair_avista_dom(driver: WebDriver) -> Optional[str]:
    """
    Preço principal exibido ao cliente (DOM estruturado).
    """
    seletores = [
        '[data-testid="price-part"]',
        '[data-testid="price"]',
        '.ui-pdp-price__second-line',
        '.andes-money-amount__fraction',
    ]

    for sel in seletores:
        try:
            elementos = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elementos:
                txt = el.text.strip()
                if txt and ("R$" in txt or _parece_preco(txt)):
                    return _normalizar_preco(txt)
        except Exception:
            continue

    return None


# ------------------------------------------------------------------
# PARCELAMENTO DOM
# ------------------------------------------------------------------

def extrair_parcelamento_dom(driver: WebDriver) -> Optional[str]:
    """
    Parcelamento exibido ao cliente.
    """
    seletores = [
        '[data-testid="installments"]',
        '.ui-pdp-installments',
        '.ui-pdp-price__subtitles',
    ]

    for sel in seletores:
        try:
            elementos = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elementos:
                txt = el.text.lower().strip()
                if "x" in txt and "r$" in txt:
                    return txt.replace("  ", " ")
        except Exception:
            continue

    return None


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------

def _parece_preco(txt: str) -> bool:
    return bool(re.search(r"\d{1,3}(\.\d{3})*,\d{2}", txt))


def _normalizar_preco(txt: str) -> Optional[str]:
    """
    Normaliza preços como:
    - 'R$171,84'
    - '171,84'
    - 'R$ 1.234,56'
    """
    m = re.search(r"R?\$?\s?\d{1,3}(\.\d{3})*,\d{2}", txt)
    if not m:
        return None

    val = m.group(0).strip()
    if not val.startswith("R$"):
        val = "R$ " + val.replace("$", "").strip()

    return val

def extrair_seller_dom(driver: WebDriver) -> Optional[str]:
    """
    Identifica o seller ativo exibido ao cliente.
    Ex: 'Probel', 'Loja Oficial Probel', 'Magazine Luiza', etc.
    """
    try:
        elementos = driver.find_elements(
            By.XPATH,
            (
                "//*[contains(text(), 'Vendido por') "
                "or contains(text(), 'Vendido e entregue por')]"
            ),
        )

        for el in elementos:
            txt = el.text.strip()
            if "vendido" in txt.lower():
                # Exemplo: "Vendido por Probel"
                partes = txt.split("por", 1)
                if len(partes) == 2:
                    return partes[1].strip()
    except Exception:
        pass

    return None
