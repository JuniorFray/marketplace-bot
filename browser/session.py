import os
from dotenv import load_dotenv

load_dotenv()

SESSION_DIR = "./browser/session_data"

def create_session(playwright):
    os.makedirs(SESSION_DIR, exist_ok=True)
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=SESSION_DIR,
        headless=False,
        slow_mo=150,
        viewport={"width": 1280, "height": 800},
        args=["--disable-blink-features=AutomationControlled"]
    )
    page = context.new_page()
    
    # Vai para mensagens normais (mais estável)
    page.goto("https://www.facebook.com/messages",
              wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)

    if page.query_selector('input[name="email"]'):
        print("🔐 Faça login manual na janela do navegador...")
        input("Pressione ENTER após estar logado...")

    return context, page