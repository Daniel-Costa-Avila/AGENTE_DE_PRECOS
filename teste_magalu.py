from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled"]
    )

    context = browser.new_context(locale="pt-BR")
    page = context.new_page()

    page.goto(
        "https://www.magazineluiza.com.br/colchao-solteiro-mola-ensacada-probel-versailles-ultra-gel-88x188x30cm-branco/p/dde864kefe/co/ccbc/",
        timeout=60000
    )

    input("Pressione ENTER para fechar...")
    browser.close()
