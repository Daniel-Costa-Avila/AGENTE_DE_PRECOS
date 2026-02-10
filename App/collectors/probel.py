# collectors/probel.py
from __future__ import annotations

import re
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException


MONEY_RE = re.compile(r"R\$\s?\d{1,3}(\.\d{3})*(,\d{2})")
PIX_RE = re.compile(r"(R\$\s?\d{1,3}(\.\d{3})*(,\d{2}))\s*no\s*pix", re.IGNORECASE)
INSTALLMENT_RE = re.compile(
    r"(\d{1,2})\s*[x×]\s*de\s*(R\$\s?\d{1,3}(\.\d{3})*(,\d{2}))",
    re.IGNORECASE,
)


def _first_money(text: str) -> Optional[str]:
    if not text:
        return None
    m = MONEY_RE.search(text)
    return m.group(0).strip() if m else None


def coletar(driver, link: str | None = None) -> dict:
    """
    Probel — Coletor baseado em DOM
    (preço Pix, avista, parcelamento)
    """

    if not link:
        return {"avista": None, "pix": None, "prazo": None, "status": "LINK AUSENTE"}

    if driver is None:
        return {"avista": None, "pix": None, "prazo": None, "status": "ERRO DE COLETA"}

    try:
        driver.set_page_load_timeout(25)
        driver.get(link)

        wait = WebDriverWait(driver, 15)
        try:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except TimeoutException:
            pass

        # scroll para renderizar dinâmico
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        except Exception:
            pass

        # pega o texto completo do body
        body_text = driver.find_element(By.TAG_NAME, "body").text or ""

        # -------- PIX --------
        pix = None
        # tenta achar com regex específico
        m_pix = PIX_RE.search(body_text)
        if m_pix:
            pix = m_pix.group(1).strip()

        # -------- PARCELAMENTO --------
        prazo = None
        m_parc = INSTALLMENT_RE.search(body_text)
        if m_parc:
            prazo = f"{m_parc.group(1)}x de {m_parc.group(2).strip()}"

        # -------- À VISTA --------
        # se tem pix, avista = pix
        avista = pix

        # se não tem pix, tenta pegar o primeiro preço (normal)
        if not avista:
            # tenta pegar primeiro dinheiro que não pareça ser parcela
            avista = _first_money(body_text)

        # -------- STATUS --------
        if avista and pix and prazo:
            status = "OK"
        elif avista and pix and not prazo:
            status = "OK (SEM PARCELAMENTO)"
        elif avista and not pix and prazo:
            status = "OK (SEM PIX)"
        elif avista:
            status = "OK (SOMENTE À VISTA)"
        else:
            status = "DADO NÃO DISPONÍVEL"

        return {"avista": avista, "pix": pix, "prazo": prazo, "status": status}

    except WebDriverException:
        return {"avista": None, "pix": None, "prazo": None, "status": "ERRO DE COLETA"}
    except Exception:
        return {"avista": None, "pix": None, "prazo": None, "status": "ERRO DE COLETA"}
