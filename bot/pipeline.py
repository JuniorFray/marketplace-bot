from browser.messenger import get_unread_conversations, get_last_message, get_sender_id, send_message
from ai.responder import generate_reply

def run_pipeline(page):
    conversations = get_unread_conversations(page)

    if not conversations:
        print("✅ Nenhuma mensagem nova.")
        return

    for conv in conversations:
        try:
            conv["element"].click()
            page.wait_for_timeout(2000)

            sender_id = get_sender_id(page)
            sender_name = conv["name"]
            last_message = get_last_message(page)

            if not last_message:
                continue

            print(f"💬 [{sender_name}]: {last_message}")
            reply = generate_reply(sender_id, sender_name, last_message)
            print(f"🤖 Resposta: {reply}")
            send_message(page, reply)
            page.wait_for_timeout(2000)

        except Exception as e:
            print(f"⚠️ Erro na conversa {conv['name']}: {e}")
            continue