# collectors/zema.py
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


DEBUG_DIR = Path("debug_zema")


def _first_money(text: str) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"R\$\s?\d{1,3}(\.\d{3})*(,\d{2})", text)
    return m.group(0).strip() if m else None


def _extract_from_jsonld(page_source: str) -> dict:
    out = {"avista": None}
    scripts = re.findall(
        r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
        page_source,
        flags=re.DOTALL | re.IGNORECASE,
    )

    for raw in scripts:
        try:
            data = json.loads(raw)
        except Exception:
            continue

        items = data if isinstance(data, list) else [data]
        for it in items:
            offers = it.get("offers") if isinstance(it, dict) else None
            if isinstance(offers, dict) and offers.get("price"):
                price = str(offers.get("price"))
                if "R$" not in price:
                    try:
                        p = float(price)
                        price = f"R$ {p:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    except Exception:
                        pass
                out["avista"] = out["avista"] or price
    return out


def _extract_from_next_data(page_source: str) -> dict:
    out = {"avista": None}
    m = re.search(
        r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        page_source,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if not m:
        return out

    try:
        data = json.loads(m.group(1))
        dumped = json.dumps(data, ensure_ascii=False)
        out["avista"] = _first_money(dumped)
    except Exception:
        pass

    return out


def coletar(driver, link: str | None = None) -> dict:
    if not link:
        return {"avista": None, "pix": None, "prazo": None, "status": "LINK AUSENTE"}

    if driver is None:
        return {"avista": None, "pix": None, "prazo": None, "status": "DADO NÃO CONFIÁVEL"}

    try:
        driver.set_page_load_timeout(25)
        driver.get(link)

        wait = WebDriverWait(driver, 12)
        try:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except TimeoutException:
            pass

        # 🔧 AJUSTE 1 — scroll para renderizar componentes
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        page = driver.page_source or ""

        # -------- À VISTA (fonte confiável) --------
        avista = None
        r1 = _extract_from_jsonld(page)
        r2 = _extract_from_next_data(page)
        avista = r1.get("avista") or r2.get("avista")

        if not avista:
            try:
                el_price = driver.find_element(By.CSS_SELECTOR, ".price, .product-price, [class*='price']")
                avista = _first_money(el_price.text) or el_price.text.strip()
            except Exception:
                avista = None

        # 🔧 AJUSTE 2 — PIX = avista se houver menção explícita a Pix
        pix = None
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            if "pix" in body_text and avista:
                pix = avista
        except Exception:
            pix = None

        # 🔧 AJUSTE 3 — parcelamento após scroll
        prazo = None
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            m = re.search(
                r"(\d{1,2}x\s+de\s+R\$\s?\d{1,3}(\.\d{3})*(,\d{2}))",
                body_text,
                re.IGNORECASE,
            )
            if m:
                prazo = m.group(1).strip()
        except Exception:
            prazo = None

        # -------- STATUS (Estratégia B) --------
        if avista and pix and prazo:
            status = "OK"
        elif avista and pix and not prazo:
            status = "OK (SEM PARCELAMENTO)"
        elif avista and not pix and prazo:
            status = "OK (SEM PIX)"
        elif avista and not pix and not prazo:
            status = "OK (SOMENTE À VISTA)"
        else:
            status = "DADO NÃO CONFIÁVEL"

        # Debug automático se não confiável
        if status == "DADO NÃO CONFIÁVEL":
            DEBUG_DIR.mkdir(exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            (DEBUG_DIR / f"page_{stamp}.html").write_text(page, encoding="utf-8", errors="ignore")
            try:
                driver.save_screenshot(str(DEBUG_DIR / f"shot_{stamp}.png"))
            except Exception:
                pass

        return {
            "avista": avista,
            "pix": pix,
            "prazo": prazo,
            "status": status,
        }

    except WebDriverException:
        return {"avista": None, "pix": None, "prazo": None, "status": "DADO NÃO CONFIÁVEL"}
    except Exception:
        return {"avista": None, "pix": None, "prazo": None, "status": "DADO NÃO CONFIÁVEL"}
