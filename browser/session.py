"""
browser/session.py
==================
Gerencia o contexto persistente do Playwright (mantém cookies/login entre execuções).
"""

import os
from pathlib import Path
from playwright.sync_api import Playwright, BrowserContext, Page

from config.settings import SESSION_DIR, HEADLESS, SLOW_MO, MARKETPLACE_INBOX_URL
from utils.logger import log


def create_session(playwright: Playwright) -> tuple[BrowserContext, Page]:
    """
    Abre (ou reabre) uma sessão persistente do Chromium.

    - Se já existe uma sessão salva, o usuário não precisa fazer login novamente.
    - Navega direto para o inbox do Marketplace.
    - Se detectar tela de login, aguarda o usuário fazer login manualmente.

    Retorna (context, page).
    """
    Path(SESSION_DIR).mkdir(parents=True, exist_ok=True)
    log.info(f"📁 Diretório de sessão: {SESSION_DIR}")

    context: BrowserContext = playwright.chromium.launch_persistent_context(
        user_data_dir=SESSION_DIR,
        headless=HEADLESS,
        slow_mo=SLOW_MO,
        viewport={"width": 1366, "height": 768},
        locale="pt-BR",
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-sandbox",
        ],
        ignore_default_args=["--enable-automation"],
    )

    page: Page = context.new_page()

    # Mascara o webdriver para reduzir detecção
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    """)

    # Navega para o Marketplace Inbox (não Messenger genérico)
    log.info(f"🌐 Abrindo: {MARKETPLACE_INBOX_URL}")
    page.goto(MARKETPLACE_INBOX_URL, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(5000)

    # Verifica se precisa de login
    if _is_login_page(page):
        log.warning("🔐 Sessão não encontrada. Faça login manual na janela do navegador.")
        input("   → Pressione ENTER após estar logado no Facebook Marketplace...")
        page.wait_for_timeout(3000)

        # Segunda verificação
        if _is_login_page(page):
            raise RuntimeError("Login não detectado após espera. Verifique se o login foi feito corretamente.")

    log.info(f"✅ Sessão ativa. URL atual: {page.url}")
    return context, page


def _is_login_page(page: Page) -> bool:
    """Detecta se estamos na tela de login do Facebook."""
    return bool(
        page.query_selector('input[name="email"]') or
        page.query_selector('input[name="pass"]') or
        page.query_selector('[data-testid="royal_login_button"]')
    )