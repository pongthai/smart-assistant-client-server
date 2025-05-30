

from abc import ABC, abstractmethod
from typing import Any, Dict
from logger_config import get_logger
import json

logger = get_logger(__name__)


class BaseIntentHandler(ABC):
    def __init__(self, session):
        self.session = session
        self.session_id = session.user_id
        self.context = session.context

            
    @abstractmethod
    def handle(self, user_input: str) -> Dict[str, Any]:
        """
        Handle user input according to the current intent state.
        Must return a dictionary containing keys like:
        - 'response': text to be sent back to the user
        - 'next_state': optional, to guide flow transition
        - 'requires_follow_up': whether to keep session in current intent
        """
        pass

    def update_context(self, updates: Dict[str, Any]) -> None:
        """
        Update the session's context state for multi-turn handling.
        """
        self.context.update(updates)

    def reset_context(self) -> None:
        """
        Reset any stored context in this handler.
        """
        self.context = {}