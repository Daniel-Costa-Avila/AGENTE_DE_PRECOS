# collectors/magalu.py
from __future__ import annotations

import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# -------------------------
# REGEXES SIMPLES
# -------------------------

PRICE_RE = re.compile(r"R\$\s?\d{1,3}(\.\d{3})*(,\d{2})")
AVISTA_RE = re.compile(r"ou\s*(R\$\s?\d{1,3}(\.\d{3})*(,\d{2}))", re.I)
PARCELA_RE = re.compile(r"(\d{1,2})x\s*de\s*(R\$\s?\d{1,3}(\.\d{3})*(,\d{2}))", re.I)


def coletar(driver, link: str | None = None) -> dict:
    """
    MAGALU — COLETOR SIMPLES (VISUAL COMO HUMANO)

    Regras:
    - pix  = preço principal em destaque (primeiro R$ X visível)
    - avista = preço secundário após 'ou R$'
    - prazo = parcelamento explícito
    """

    out = {
        "avista": None,
        "pix": None,
        "prazo": None,
        "status": "",
    }

    if not link:
        out["status"] = "LINK AUSENTE"
        return out

    try:
        driver.get(link)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # força renderização
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        except Exception:
            pass

        text = driver.find_element(By.TAG_NAME, "body").text or ""

        # -------------------------
        # PARCELAMENTO
        # -------------------------
        m_parc = PARCELA_RE.search(text)
        if m_parc:
            out["prazo"] = f"{m_parc.group(1)}x de {m_parc.group(2)}"

        # -------------------------
        # AVISTA (ou R$ ...)
        # -------------------------
        m_avista = AVISTA_RE.search(text)
        if m_avista:
            out["avista"] = m_avista.group(1)

        # -------------------------
        # PREÇO PRINCIPAL (PIX VISUAL)
        # -------------------------
        prices = PRICE_RE.findall(text)
        prices_full = PRICE_RE.finditer(text)

        for m in prices_full:
            price = m.group(0)

            # ignora o preço que já é o "ou R$ ..."
            if out["avista"] and price == out["avista"]:
                continue

            # primeiro preço válido é o principal
            out["pix"] = price
            break

        # -------------------------
        # STATUS
        # -------------------------
        if out["pix"] and out["avista"]:
            out["status"] = "MAGALU — OK"
        elif out["pix"]:
            out["status"] = "MAGALU — OK (SOMENTE PREÇO PRINCIPAL)"
        elif out["avista"]:
            out["status"] = "MAGALU — OK (SEM PREÇO PRINCIPAL)"
        else:
            out["status"] = "MAGALU — PREÇO NÃO ENCONTRADO"

        return out

    except Exception:
        out["status"] = "MAGALU — ERRO DE COLETA"
        return out
