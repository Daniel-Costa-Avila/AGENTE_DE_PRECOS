# collectors/madeiramadeira.py
from __future__ import annotations

import re
import unicodedata
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException


_MONEY_RE = re.compile(r"R\$\s?\d{1,3}(\.\d{3})*(,\d{2})")


def _first_money(text: str) -> Optional[str]:
    if not text:
        return None
    m = _MONEY_RE.search(text)
    return m.group(0).strip() if m else None


def _norm(s: str) -> str:
    """normaliza para comparar sem acentos"""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower()


def _find_pix_avista_from_lines(body_text: str) -> tuple[Optional[str], Optional[str]]:
    """
    Regra MadeiraMadeira:
    - o preço exibido como "à vista no Pix" é o preço real à vista/pix.
    - o texto pode estar antes ou depois do valor, ou em linhas separadas.
    Estratégia:
      1) achar linha com "pix" ou "a vista"
      2) extrair dinheiro na mesma linha; senão, na linha anterior; senão, na próxima
    """
    lines = [ln.strip() for ln in body_text.splitlines() if ln.strip()]
    nlines = len(lines)

    for i, ln in enumerate(lines):
        ln_norm = _norm(ln)
        if ("pix" in ln_norm) or ("a vista" in ln_norm) or ("avista" in ln_norm):
            # tenta na mesma linha
            money = _first_money(ln)
            if money:
                return money, money  # avista, pix

            # tenta linha anterior
            if i - 1 >= 0:
                money = _first_money(lines[i - 1])
                if money:
                    return money, money

            # tenta linha seguinte
            if i + 1 < nlines:
                money = _first_money(lines[i + 1])
                if money:
                    return money, money

    return None, None


def coletar(driver, link: str | None = None) -> dict:
    """
    MadeiraMadeira — Estratégia B (corrigida)
    - avista/pix: preço associado ao contexto 'Pix'/'à vista' (com desconto quando existir)
    - prazo: 'Nx de R$ ...'
    - status: OK / OK (SEM PIX) / OK (SEM PARCELAMENTO) / OK (SOMENTE À VISTA) / ERRO DE COLETA
    """

    if not link:
        return {"avista": None, "pix": None, "prazo": None, "status": "LINK AUSENTE"}

    if driver is None:
        return {"avista": None, "pix": None, "prazo": None, "status": "ERRO DE COLETA"}

    try:
        driver.set_page_load_timeout(25)
        driver.get(link)

        wait = WebDriverWait(driver, 15)

        # Carregamento mínimo
        try:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except TimeoutException:
            pass

        # Scroll para renderizar blocos
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        except Exception:
            pass

        body_text = driver.find_element(By.TAG_NAME, "body").text

        # ---------------- AVISTA / PIX (CORRIGIDO) ----------------
        avista, pix = _find_pix_avista_from_lines(body_text)

        # fallback: se não achou pelo contexto, pega o primeiro preço como avista (sem afirmar pix)
        if not avista:
            avista = _first_money(body_text)

        # ---------------- PARCELAMENTO (JÁ ESTAVA OK) ----------------
        prazo = None
        try:
            m = re.search(
                r"(\d{1,2}x\s+de\s+R\$\s?\d{1,3}(\.\d{3})*(,\d{2}))",
                body_text,
                re.IGNORECASE,
            )
            if m:
                prazo = m.group(1).strip()
        except Exception:
            prazo = None

        # ---------------- STATUS (mais informativo) ----------------
        if avista and pix and prazo:
            status = "OK"
        elif avista and pix and not prazo:
            status = "OK (SEM PARCELAMENTO)"
        elif avista and not pix and prazo:
            status = "OK (SEM PIX)"
        elif avista and not pix and not prazo:
            status = "OK (SOMENTE À VISTA)"
        else:
            # aqui significa que nem preço foi encontrado
            status = "ERRO DE COLETA"

        return {"avista": avista, "pix": pix, "prazo": prazo, "status": status}

    except WebDriverException:
        return {"avista": None, "pix": None, "prazo": None, "status": "ERRO DE COLETA"}
    except Exception:
        return {"avista": None, "pix": None, "prazo": None, "status": "ERRO DE COLETA"}
