"""
main.py
=======
Ponto de entrada do Marketplace Bot.
"""

import sys
import time
from playwright.sync_api import sync_playwright

from browser.session import create_session
from bot.pipeline import run_pipeline
from config.settings import POLL_INTERVAL_SEC
from utils.logger import log


def main() -> None:
    log.info("=" * 50)
    log.info("🤖  Marketplace Bot — iniciando")
    log.info(f"⏱️   Intervalo de verificação: {POLL_INTERVAL_SEC // 60} min")
    log.info("=" * 50)

    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 5

    try:
        with sync_playwright() as pw:
            context, page = create_session(pw)

            cycle = 0
            while True:
                cycle += 1
                log.info(f"\n🔄 Ciclo #{cycle} | URL: {page.url}")

                try:
                    run_pipeline(page)
                    consecutive_errors = 0  # reset em caso de sucesso

                except Exception as e:
                    consecutive_errors += 1
                    log.error(
                        f"❌ Erro no ciclo #{cycle} "
                        f"({consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}): {e}",
                        exc_info=True,
                    )

                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        log.critical("🚨 Muitos erros consecutivos. Encerrando.")
                        break

                log.info(f"😴 Aguardando {POLL_INTERVAL_SEC // 60} minuto(s)...\n")
                time.sleep(POLL_INTERVAL_SEC)

    except KeyboardInterrupt:
        log.info("\n⛔  Bot interrompido pelo usuário.")
        sys.exit(0)
    except Exception as e:
        log.critical(f"💥 Erro fatal: {e}", exc_info=True)
        sys.exit(1)
    finally:
        log.info("👋  Bot encerrado.")


if __name__ == "__main__":
    main()