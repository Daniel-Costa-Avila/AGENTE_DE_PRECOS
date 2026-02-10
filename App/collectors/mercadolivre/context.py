from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def carregar_pagina(driver: WebDriver, url: str, timeout: int = 20) -> None:
    driver.get(url)
    # Espera “algo” do ML carregar. Evita travar em páginas lentas.
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
    )


def detectar_indisponivel(driver: WebDriver) -> bool:
    """
    Best-effort: tenta detectar indisponibilidade sem depender de uma frase fixa.
    """
    try:
        html = driver.page_source.lower()
        sinais = [
            "produto indisponível",
            "indisponível",
            "não está disponível",
            "sem estoque",
            "publicação finalizada",
        ]
        return any(s in html for s in sinais)
    except Exception:
        return False


def extrair_estado_json(driver: WebDriver) -> Optional[Dict[str, Any]]:
    """
    Fonte primária: window.__PRELOADED_STATE__ / window.__APOLLO_STATE__.
    Fallback: scripts application/json (quando existir um bloco grande).
    Retorna dict ou None.
    """
    # 1) PRELOADED_STATE
    try:
        state = driver.execute_script("return window.__PRELOADED_STATE__ || null;")
        if isinstance(state, dict) and state:
            return state
    except Exception:
        pass

    # 2) APOLLO_STATE
    try:
        apollo = driver.execute_script("return window.__APOLLO_STATE__ || null;")
        if isinstance(apollo, dict) and apollo:
            return {"__APOLLO_STATE__": apollo}
    except Exception:
        pass

    # 3) Fallback: scripts application/json
    try:
        scripts = driver.find_elements(By.CSS_SELECTOR, 'script[type="application/json"]')
        # tenta o maior bloco (mais chance de conter estado)
        candidatos = sorted(
            (s.get_attribute("innerHTML") or "" for s in scripts),
            key=lambda t: len(t),
            reverse=True,
        )
        for txt in candidatos[:3]:
            txt = txt.strip()
            if len(txt) < 2000:
                continue
            try:
                parsed = json.loads(txt)
                if isinstance(parsed, dict) and parsed:
                    return {"__APPLICATION_JSON__": parsed}
            except Exception:
                continue
    except Exception:
        pass

    return None


def extrair_titulo(driver: WebDriver, state: Dict[str, Any]) -> Optional[str]:
    """
    Best-effort: tenta achar título via state ou DOM.
    Não afeta contrato, só utilidade.
    """
    # DOM (fallback simples)
    try:
        h1 = driver.find_elements(By.CSS_SELECTOR, "h1")
        if h1:
            t = (h1[0].text or "").strip()
            if t:
                return t
    except Exception:
        pass

    # State: tenta campos comuns
    return _find_first_str(state, keys=("title", "name", "product_title", "productName"))


def _find_first_str(obj: Any, keys: tuple[str, ...]) -> Optional[str]:
    """
    Busca profunda por primeira string em chaves conhecidas.
    """
    try:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in keys and isinstance(v, str) and v.strip():
                    return v.strip()
                found = _find_first_str(v, keys)
                if found:
                    return found
        elif isinstance(obj, list):
            for it in obj:
                found = _find_first_str(it, keys)
                if found:
                    return found
    except Exception:
        return None
    return None
def detectar_indisponivel(driver: WebDriver, state: dict | None = None) -> bool:
    """
    Mercado Livre:
    Produto só é indisponível se o JSON afirmar isso.
    Nunca por texto genérico do HTML.
    """
    if not isinstance(state, dict):
        return False

    try:
        item = state.get("item", {})

        # quantidade disponível
        qty = item.get("available_quantity")
        if isinstance(qty, int) and qty <= 0:
            return True

        # status do anúncio
        status = item.get("status")
        if isinstance(status, str) and status.lower() != "active":
            return True

    except Exception:
        return False

    return False
