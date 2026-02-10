from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright


DEBUG_DIR = Path("debug_magalu")
PROFILE_DIR = Path("chrome_profile_magalu")
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)


def _launch_context(p, headless: bool):
    """
    Tenta abrir contexto persistente (perfil fixo).
    Se falhar (perfil travado/corrompido), cai para contexto temporário.
    Retorna (context, browser_ou_None).
    """
    PROFILE_DIR.mkdir(exist_ok=True)
    args = ["--disable-blink-features=AutomationControlled"]

    try:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=headless,
            args=args,
            locale="pt-BR",
            user_agent=DEFAULT_UA,
            viewport={"width": 1366, "height": 768},
        )
        return context, None
    except Exception:
        browser = p.chromium.launch(
            headless=headless,
            args=args,
        )
        context = browser.new_context(
            locale="pt-BR",
            user_agent=DEFAULT_UA,
            viewport={"width": 1366, "height": 768},
        )
        return context, browser


def _save_debug(page, reason: str) -> None:
    try:
        DEBUG_DIR.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        info = (
            f"reason: {reason}\n"
            f"url: {page.url}\n"
            f"title: {page.title()}\n"
        )
        (DEBUG_DIR / f"{stamp}_info.txt").write_text(
            info,
            encoding="utf-8",
            errors="ignore",
        )
        (DEBUG_DIR / f"{stamp}.html").write_text(
            page.content(),
            encoding="utf-8",
            errors="ignore",
        )
        page.screenshot(path=str(DEBUG_DIR / f"{stamp}.png"), full_page=True)
    except Exception:
        pass


def coletar(url: str, headless: bool = False) -> dict:
    """
    Coletor Magalu (Playwright)
    - Pix: somente se explicitamente entregue no DOM
    - Avista: valor do 'ou R$ ...'
    - Prazo: texto de parcelamento
    - Nunca calcula valores
    - Nunca quebra pipeline
    """

    resultado = {
        "avista": None,
        "pix": None,
        "prazo": None,
        "status": "INICIAL",
    }

    if not url:
        resultado["status"] = "LINK AUSENTE"
        return resultado

    try:
        with sync_playwright() as p:
            context, browser = _launch_context(p, headless)
            page = context.new_page()

            # -------- ACESSO --------
            page.goto(url, timeout=60000)

            # -------- ESPERA REAL PELO VALOR --------
            try:
                page.wait_for_function(
                    """
                    () => {
                        const el = document.querySelector(
                          '[data-testid="price-value-integer"]'
                        );
                        return el && el.textContent.trim().length > 0;
                    }
                    """,
                    timeout=15000,
                )
            except Exception:
                # Se não aparecer, seguimos com status explícito
                pass

            # -------- PIX --------
            try:
                metodo_pix = page.locator(
                    '[data-testid="price-method"]:has-text("no Pix")'
                )

                if metodo_pix.count() > 0:
                    price = page.locator('[data-testid="price-value"]').first

                    inteiro = price.locator(
                        '[data-testid="price-value-integer"]'
                    ).text_content()

                    decimal = price.locator(
                        '[data-testid="price-value-split-cents-decimal"]'
                    ).text_content()

                    fracao = price.locator(
                        '[data-testid="price-value-split-cents-fraction"]'
                    ).text_content()

                    if inteiro and decimal and fracao:
                        resultado["pix"] = f"{inteiro}{decimal}{fracao}"
            except Exception:
                pass

            # -------- AVISTA / PRAZO --------
            try:
                installment = page.locator(
                    '[data-testid="price-installment"]'
                ).text_content()

                if installment:
                    match_avista = re.search(
                        r"R\$\s*([\d\.]+,\d{2})",
                        installment,
                    )
                    if match_avista:
                        resultado["avista"] = match_avista.group(1)

                    match_prazo = re.search(
                        r"(\d+x de R\$\s*[\d\.]+,\d{2} sem juros)",
                        installment,
                    )
                    if match_prazo:
                        resultado["prazo"] = match_prazo.group(1)
            except Exception:
                pass

            # -------- STATUS FINAL --------
            if resultado["pix"]:
                resultado["status"] = "OK"
            elif resultado["avista"] or resultado["prazo"]:
                resultado["status"] = "MAGALU — PIX REQUER INPUT MANUAL"
            else:
                resultado["status"] = "MAGALU — PREÇO NÃO DISPONÍVEL"
                _save_debug(page, "preco_nao_disponivel")

            context.close()
            if browser is not None:
                browser.close()

    except Exception as e:
        resultado["status"] = f"MAGALU — EXCEÇÃO: {type(e).__name__} | {e}"

    return resultado
