import threading

from sqlalchemy import Column, String

from TSBSSB.modules.sql import BASE, SESSION


class TSBChats(BASE):
    __tablename__ = "tsb_chats"
    chat_id = Column(String(14), primary_key=True)

    def __init__(self, chat_id):
        self.chat_id = chat_id


TSBChats.__table__.create(checkfirst=True)
INSERTION_LOCK = threading.RLock()


def is_tsb(chat_id):
    try:
        chat = SESSION.query(TSBChats).get(str(chat_id))
        return bool(chat)
    finally:
        SESSION.close()


def set_tsb(chat_id):
    with INSERTION_LOCK:
        tsbchat = SESSION.query(TSBChats).get(str(chat_id))
        if not tsbchat:
            tsbchat = TSBChats(str(chat_id))
        SESSION.add(tsbchat)
        SESSION.commit()


def rem_tsb(chat_id):
    with INSERTION_LOCK:
        tsbchat = SESSION.query(TSBChats).get(str(chat_id))
        if tsbchat:
            SESSION.delete(tsbchat)
        SESSION.commit()
