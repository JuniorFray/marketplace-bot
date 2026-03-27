import os
import hashlib
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

from utils.logger import log

load_dotenv()

# ── Inicialização ──────────────────────────────────────────────────────────
_cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if not _cred_path:
    raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS não definida no .env")

cred = credentials.Certificate(_cred_path)
firebase_admin.initialize_app(cred)
db = firestore.client()


# ── Helpers ────────────────────────────────────────────────────────────────

def _msg_hash(content: str) -> str:
    """Hash curto para identificar uma mensagem pelo conteúdo."""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


# ── Histórico de conversa ──────────────────────────────────────────────────

def save_message(sender_id: str, sender_name: str, role: str, content: str) -> None:
    """Salva uma mensagem no histórico da conversa."""
    try:
        doc_ref = db.collection("conversations").document(sender_id)
        doc_ref.set(
            {"sender_name": sender_name, "last_updated": datetime.now()},
            merge=True,
        )
        doc_ref.collection("messages").add(
            {"role": role, "content": content, "timestamp": datetime.now()}
        )
    except Exception as e:
        log.error(f"[Firebase] Erro ao salvar mensagem: {e}")


def get_history(sender_id: str) -> list[dict]:
    """Retorna as últimas N mensagens da conversa."""
    try:
        from config.settings import MAX_HISTORY
        docs = (
            db.collection("conversations")
            .document(sender_id)
            .collection("messages")
            .order_by("timestamp")
            .limit_to_last(MAX_HISTORY)
            .stream()
        )
        return [{"role": d.get("role"), "content": d.get("content")} for d in docs]
    except Exception as e:
        log.error(f"[Firebase] Erro ao buscar histórico: {e}")
        return []


# ── Deduplicação ───────────────────────────────────────────────────────────

def get_last_processed_hash(sender_id: str) -> str | None:
    """
    Retorna o hash da última mensagem que o bot JÁ processou e respondeu.
    Usado para evitar responder duas vezes à mesma mensagem.
    """
    try:
        doc = db.collection("conversations").document(sender_id).get()
        if doc.exists:
            return doc.to_dict().get("last_processed_hash")
        return None
    except Exception as e:
        log.error(f"[Firebase] Erro ao buscar hash: {e}")
        return None


def mark_as_processed(sender_id: str, sender_name: str, message_content: str) -> None:
    """Marca a mensagem atual como processada, salvando seu hash."""
    try:
        db.collection("conversations").document(sender_id).set(
            {
                "sender_name":          sender_name,
                "last_processed_hash":  _msg_hash(message_content),
                "last_processed_at":    datetime.now(),
            },
            merge=True,
        )
    except Exception as e:
        log.error(f"[Firebase] Erro ao marcar como processada: {e}")


def is_already_processed(sender_id: str, message_content: str) -> bool:
    """True se esta mensagem já foi processada anteriormente."""
    stored = get_last_processed_hash(sender_id)
    return stored == _msg_hash(message_content)