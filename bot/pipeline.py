"""
bot/pipeline.py
===============
Orquestra o ciclo completo de processamento de mensagens do Marketplace.

Fluxo por conversa:
  1. Clica na conversa
  2. Lê a última mensagem do comprador
  3. Verifica se já foi processada (deduplicação via Firebase)
  4. Gera resposta via OpenAI
  5. Envia a resposta
  6. Volta para o inbox
"""

from browser.messenger import (
    navigate_to_inbox,
    get_unread_conversations,
    get_last_buyer_message,
    get_thread_id,
    send_message,
)
from firebase.client import is_already_processed
from ai.responder import generate_reply
from config.settings import CLICK_WAIT, MARKETPLACE_INBOX_URL
from utils.logger import log


def run_pipeline(page) -> int:
    """
    Executa um ciclo completo de verificação e resposta.
    Retorna o número de mensagens processadas neste ciclo.
    """
    processed = 0

    # Garante que estamos no inbox antes de começar
    if "marketplace/inbox" not in page.url:
        if not navigate_to_inbox(page):
            log.error("❌ Não foi possível navegar para o inbox. Ciclo abortado.")
            return 0

    conversations = get_unread_conversations(page)

    if not conversations:
        log.info("✅ Nenhuma mensagem nova.")
        return 0

    log.info(f"📬 {len(conversations)} conversa(s) não lida(s) encontrada(s).")

    for conv in conversations:
        name = conv["name"]
        log.info(f"\n{'─' * 40}")
        log.info(f"👤 Processando: {name}")

        try:
            # 1. Entra na conversa
            conv["element"].click()
            page.wait_for_timeout(CLICK_WAIT)

            # 2. Extrai o ID do thread a partir da URL
            thread_id = get_thread_id(page)
            log.debug(f"Thread ID: {thread_id}")

            # 3. Lê a última mensagem do comprador
            message = get_last_buyer_message(page)

            if not message:
                log.warning(f"⚠️  Nenhuma mensagem legível em '{name}'. Pulando.")
                _back_to_inbox(page)
                continue

            log.info(f"💬 Mensagem: {message[:100]}")

            # 4. Deduplicação: pula se já respondemos esta mensagem
            if is_already_processed(thread_id, message):
                log.info(f"↩️  Já processada anteriormente. Pulando.")
                _back_to_inbox(page)
                continue

            # 5. Gera a resposta via IA
            reply = generate_reply(thread_id, name, message)

            if not reply:
                log.error(f"❌ Falha ao gerar resposta para '{name}'.")
                _back_to_inbox(page)
                continue

            log.info(f"🤖 Resposta: {reply[:100]}")

            # 6. Envia a resposta
            if send_message(page, reply):
                processed += 1
            else:
                log.error(f"❌ Falha ao enviar mensagem para '{name}'.")

        except Exception as e:
            log.error(f"❌ Erro inesperado em '{name}': {e}", exc_info=True)

        finally:
            # Sempre volta para o inbox após cada conversa
            _back_to_inbox(page)

    log.info(f"\n📊 Ciclo concluído. Mensagens respondidas: {processed}/{len(conversations)}")
    return processed


def _back_to_inbox(page) -> None:
    """Navega de volta para o inbox do Marketplace."""
    try:
        if "marketplace/inbox" not in page.url:
            page.goto(MARKETPLACE_INBOX_URL, wait_until="domcontentloaded", timeout=20_000)
            page.wait_for_timeout(3000)
    except Exception as e:
        log.warning(f"⚠️  Falha ao retornar ao inbox: {e}")