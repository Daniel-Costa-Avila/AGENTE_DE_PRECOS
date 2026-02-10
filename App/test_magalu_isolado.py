# test_magalu_isolado.py
import time

from utils.browser import get_driver
from collectors.magalu import coletar


def main():
    # 1️⃣ Driver NÃO headless, perfil persistente
    driver = get_driver(headless=False)

    try:
        # 2️⃣ PASSO OBRIGATÓRIO: entrar na HOME primeiro
        print("Abrindo home da Magalu...")
        driver.get("https://www.magazineluiza.com.br/")
        time.sleep(10)  # tempo real para contexto de sessão

        # 3️⃣ Produto (APENAS UM)
        link = (
            "https://www.magazineluiza.com.br/"
            "colchao-solteiro-mola-ensacada-probel-versailles-ultra-gel-88x188x30cm-branco/"
            "p/dde864kefe/co/ccbc/"
        )

        print("Abrindo PDP...")
        result = coletar(driver, link)

        print("\nRESULTADO:")
        print(result)

        # 4️⃣ Espera antes de encerrar (importantíssimo)
        time.sleep(20)

    finally:
        print("Encerrando navegador...")
        driver.quit()


if __name__ == "__main__":
    main()
