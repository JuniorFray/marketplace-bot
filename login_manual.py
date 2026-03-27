import json
from playwright.sync_api import sync_playwright

COOKIES_FILE = "./browser/cookies.json"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=100)
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()

    page.goto("https://www.facebook.com/messages", wait_until="networkidle")

    print("=" * 50)
    print("👤 Faça o login MANUALMENTE na janela do navegador.")
    print("✅ Quando estiver na página de mensagens, volte aqui.")
    print("=" * 50)
    input("Pressione ENTER após estar logado e na página de mensagens...")

    cookies = context.cookies()
    with open(COOKIES_FILE, "w") as f:
        json.dump(cookies, f)

    print(f"✅ {len(cookies)} cookies salvos com sucesso!")
    print("🤖 Agora pode rodar: python main.py")
    browser.close()