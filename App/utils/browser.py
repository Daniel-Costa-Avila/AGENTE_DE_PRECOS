# utils/browser.py
from __future__ import annotations

import os
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def get_driver(headless: bool = False) -> webdriver.Chrome:
    """
    ChromeDriver robusto para Windows
    - Perfil persistente
    - Captura Network (XHR/GraphQL) — Selenium 4
    - Evita crash DevToolsActivePort
    """

    options = Options()

    if headless:
        options.add_argument("--headless=new")

    # 🔑 PERFIL ABSOLUTO (OBRIGATÓRIO NO WINDOWS)
    profile_dir = Path(__file__).resolve().parent.parent / "chrome_profile"
    os.makedirs(profile_dir, exist_ok=True)

    options.add_argument(f"--user-data-dir={profile_dir}")

    # 🔧 FLAGS ANTI-CRASH
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-debugging-port=9222")

    options.add_argument("--lang=pt-BR")
    options.add_argument("--window-size=1366,768")
    options.add_argument("--disable-blink-features=AutomationControlled")

    # 🔥 ESSENCIAL PARA O CARREFOUR (SELENIUM 4)
    options.set_capability(
        "goog:loggingPrefs",
        {"performance": "ALL"}
    )

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    return driver
