# server/session_manager.py

import time
from typing import Dict, Optional
from logger_config import get_logger

logger = get_logger(__name__)

SESSION_TIMEOUT = 300  # seconds (5 minutes)

class Session:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.intent = None
        self.state = None
        self.context = {}
        self.last_updated = time.time()

    def update(self, intent=None, state=None, context_update=None):
        if intent:
            self.intent = intent
        if state:
            self.state = state
        if context_update:
            self.context.update(context_update)
        self.last_updated = time.time()
        logger.debug(f"session updated: intent={self.intent} , state={self.state}, last_udpate={self.last_updated}")

    def is_expired(self):
        return time.time() - self.last_updated > SESSION_TIMEOUT

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "intent": self.intent,
            "state": self.state,
            "context": self.context,
            "last_updated": self.last_updated
        }

    def has_state(self):
        return self.intent is not None and self.state is not None

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Session] = {}

    def get_session(self, user_id: str) -> Session:
        session = self.sessions.get(user_id)
        
        if not session or session.is_expired():
            session = Session(user_id)
            self.sessions[user_id] = session
        logger.debug(f"get_session : {session.to_dict()}")
        return session

    def clear_session(self, user_id: str):
        if user_id in self.sessions:
            del self.sessions[user_id]

    def get_state_info(self, user_id: str):
        session = self.sessions.get(user_id)
        
        if session and not session.is_expired():
            return {
                "intent": session.intent,
                "state": session.state,
                "context": session.context
            }
        return None

    def update_session(self, user_id: str, intent=None, state=None, context_update=None):
        session = self.get_session(user_id)
        session.update(intent=intent, state=state, context_update=context_update)

# Initialize the session manager instance for global use
session_manager = SessionManager()