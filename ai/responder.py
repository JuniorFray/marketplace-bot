"""
ai/responder.py
===============
Gera respostas usando GPT via OpenAI, mantendo contexto do histórico de conversa.
"""

from openai import OpenAI
from firebase.client import get_history, save_message, mark_as_processed
from config.settings import OPENAI_API_KEY, OPENAI_MODEL, MAX_TOKENS, TEMPERATURE
from utils.logger import log

_client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """
Você é um assistente de vendas simpático e objetivo, respondendo mensagens
do Facebook Marketplace em nome do vendedor.

Regras obrigatórias:
- Respostas curtas e naturais, como uma pessoa real escreveria no celular
- Nunca invente informações sobre preço, produto ou disponibilidade
- Se não souber algo, diga: "Vou verificar e já te falo!"
- Seja cordial mas direto
- Não use emojis em excesso (máximo 1 por mensagem)
- Não repita saudações se já houver histórico de conversa
- Nunca revele que você é um bot ou IA
""".strip()


def generate_reply(
    sender_id: str,
    sender_name: str,
    new_message: str,
) -> str | None:
    """
    Gera uma resposta para a mensagem recebida.

    - Busca o histórico de conversa no Firebase
    - Chama a API do OpenAI
    - Salva a mensagem recebida e a resposta gerada no Firebase
    - Marca a mensagem como processada (deduplicação)

    Retorna a resposta gerada, ou None em caso de falha.
    """
    try:
        history = get_history(sender_id)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages += history
        messages.append({"role": "user", "content": new_message})

        log.debug(f"Chamando OpenAI ({OPENAI_MODEL}) com {len(history)} msgs de histórico...")

        response = _client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )

        reply: str = response.choices[0].message.content.strip()

        # Persiste no Firebase
        save_message(sender_id, sender_name, "user",      new_message)
        save_message(sender_id, sender_name, "assistant", reply)
        mark_as_processed(sender_id, sender_name, new_message)

        log.debug(f"Resposta gerada: {reply[:80]}")
        return reply

    except Exception as e:
        log.error(f"❌ Erro ao gerar resposta via OpenAI: {e}")
        return None