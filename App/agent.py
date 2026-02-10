from collectors.webcontinental import coletar as webcontinental
import os
import subprocess
import pandas as pd
from openai import OpenAI

# cria o cliente usando a variável de ambiente
client = OpenAI()

SYSTEM_PROMPT = """
Você é um agente de monitoramento de preços.

Funções:
- Analisar produtos de e-commerce
- Decidir quais scrapers executar
- Interpretar resultados
- Gerar resumos claros

Regras:
- Nunca faça scraping diretamente
- Sempre use os scripts locais
"""

def detectar_sites():
    df = pd.read_excel("input.xlsx", engine="openpyxl")
    sites = set()

    for url in df["link"]:
        if "magazineluiza" in url:
            sites.add("Magazine Luiza")
        elif "casasbahia" in url:
            sites.add("Casas Bahia")
        elif "mercadolivre" in url:
            sites.add("Mercado Livre")

    return list(sites)

def perguntar_ao_gpt(sites):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Sites detectados na planilha: {sites}. O que devo executar?"
            }
        ]
    )
    return response.choices[0].message.content

def executar_scraper():
    print("🚀 Executando scraper (main.py)...")
    subprocess.run(["python", "main.py"])

def analisar_saida():
    df = pd.read_excel("output.xlsx")
    resumo = df["status"].value_counts().to_dict()
    return resumo

if __name__ == "__main__":
    print("🤖 Agente GPT iniciado")

    sites = detectar_sites()
    print("Sites encontrados:", sites)

    decisao = perguntar_ao_gpt(sites)
    print("\n🧠 Resposta do ChatGPT:")
    print(decisao)

    executar_scraper()

    resumo = analisar_saida()
    print("\n📊 Resumo da execução:")
    print(resumo)
