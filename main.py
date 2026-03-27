import time
import os
from playwright.sync_api import sync_playwright
from browser.session import create_session
from bot.pipeline import run_pipeline
from dotenv import load_dotenv

load_dotenv()

INTERVAL = int(os.getenv("POLL_INTERVAL_MINUTES", 3)) * 60

def main():
    print("🤖 Marketplace Bot iniciado!")
    print(f"⏱️ Verificando mensagens a cada {INTERVAL // 60} minutos...\n")

    with sync_playwright() as p:
        context, page = create_session(p)
        print("✅ Navegador pronto. Posicione na lista de mensagens Messenger...")
        input("Pressione ENTER quando estiver na lista de mensagens do Messenger...")

        while True:
            try:
                print("─" * 40)
                print(f"📍 URL atual: {page.url}")

                # Volta para lista se estiver em conversa
                if "/t/" in page.url:
                    page.keyboard.press("ArrowLeft")
                    page.wait_for_timeout(2000)

                # Clica especificamente no Marketplace do Messenger (não anúncios)
                marketplace_btn = None
                for selector in [
                    '[aria-label*="Marketplace"]',
                    'div[aria-label*="Marketplace"]',
                    'a[href*="/messages/marketplace"]'
                ]:
                    marketplace_btn = page.query_selector(selector)
                    if marketplace_btn:
                        print(f"✅ Encontrou Marketplace com seletor: {selector}")
                        break

                if marketplace_btn:
                    marketplace_btn.click()
                    page.wait_for_timeout(4000)
                else:
                    print("⚠️ Botão Marketplace não encontrado")

                run_pipeline(page)

            except Exception as e:
                print(f"⚠️ Erro no ciclo principal: {e}")

            print(f"😴 Aguardando {INTERVAL // 60} minutos...\n")
            time.sleep(INTERVAL)

if __name__ == "__main__":
    main()