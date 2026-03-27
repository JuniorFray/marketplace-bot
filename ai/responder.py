import os
from openai import OpenAI
from firebase.client import get_history, save_message
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
Você é um assistente de vendas simpático e objetivo respondendo mensagens 
do Facebook Marketplace em nome do vendedor.
Regras:
- Respostas curtas e naturais, como uma pessoa real escreveria no celular
- Nunca invente informações sobre preço ou produto
- Se não souber algo, diga: "Vou verificar e já te falo!"
- Seja cordial mas direto
- Não use emojis em excesso
"""

def generate_reply(sender_id: str, sender_name: str, new_message: str) -> str:
    history = get_history(sender_id)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += history
    messages.append({"role": "user", "content": new_message})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=200
    )

    reply = response.choices[0].message.content

    save_message(sender_id, sender_name, "user", new_message)
    save_message(sender_id, sender_name, "assistant", reply)

    return reply