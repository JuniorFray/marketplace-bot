import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

cred = credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
firebase_admin.initialize_app(cred)

db = firestore.client()

def save_message(sender_id: str, sender_name: str, role: str, content: str):
    doc_ref = db.collection("conversations").document(sender_id)
    doc_ref.set({"sender_name": sender_name, "last_updated": datetime.now()}, merge=True)
    doc_ref.collection("messages").add({
        "role": role,
        "content": content,
        "timestamp": datetime.now()
    })

def get_history(sender_id: str) -> list:
    messages_ref = (
        db.collection("conversations")
        .document(sender_id)
        .collection("messages")
        .order_by("timestamp")
        .limit(20)
    )
    docs = messages_ref.stream()
    return [{"role": doc.get("role"), "content": doc.get("content")} for doc in docs]

def conversation_exists(sender_id: str) -> bool:
    doc = db.collection("conversations").document(sender_id).get()
    return doc.exists