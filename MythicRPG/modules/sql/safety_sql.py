import threading
from sqlalchemy import Column, String, Boolean
from MythicRPG.modules.sql import SESSION, BASE

class SafetySettings(BASE):
    __tablename__ = "safety_settings"
    chat_id = Column(String(14), primary_key=True)
    nsfw_enabled = Column(Boolean, default=False)
    piracy_enabled = Column(Boolean, default=False)
    ai_enabled = Column(Boolean, default=True)

    def __init__(self, chat_id):
        self.chat_id = str(chat_id)

SafetySettings.__table__.create(checkfirst=True)
INSERTION_LOCK = threading.Lock()

def is_ai_enabled(chat_id):
    try:
        chat = SESSION.query(SafetySettings).get(str(chat_id))
        return chat.ai_enabled if chat else True
    finally:
        SESSION.close()

def set_ai_status(chat_id, status: bool):
    with INSERTION_LOCK:
        curr = SESSION.query(SafetySettings).get(str(chat_id))
        if not curr:
            curr = SafetySettings(str(chat_id))
        curr.ai_enabled = status
        SESSION.add(curr)
        SESSION.commit()

def is_nsfw_enabled(chat_id):
    try:
        chat = SESSION.query(SafetySettings).get(str(chat_id))
        return chat.nsfw_enabled if chat else False
    finally:
        SESSION.close()

def set_nsfw_status(chat_id, status: bool):
    with INSERTION_LOCK:
        curr = SESSION.query(SafetySettings).get(str(chat_id))
        if not curr:
            curr = SafetySettings(str(chat_id))
        curr.nsfw_enabled = status
        SESSION.add(curr)
        SESSION.commit()

def is_piracy_enabled(chat_id):
    try:
        chat = SESSION.query(SafetySettings).get(str(chat_id))
        return chat.piracy_enabled if chat else False
    finally:
        SESSION.close()

def set_piracy_status(chat_id, status: bool):
    with INSERTION_LOCK:
        curr = SESSION.query(SafetySettings).get(str(chat_id))
        if not curr:
            curr = SafetySettings(str(chat_id))
        curr.piracy_enabled = status
        SESSION.add(curr)
        SESSION.commit()
