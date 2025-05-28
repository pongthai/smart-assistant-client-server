from .command_handler import CommandHandler
from .reminder_handler import ReminderHandler
from .chat_handler import ChatHandler
from ..intent_classifier.classifier import IntentClassifier
from ..gpt_integration import GPTClient
from logger_config import get_logger

class IntentRouter:
    def __init__(self, gpt_client: GPTClient, intent_classifier: IntentClassifier):
        self.gpt_client = gpt_client
        self.intent_classifier = intent_classifier

    def route(self, user_input: str):
        result = self.intent_classifier.classify_intent(user_input)
        intent = result.get("intent", "chat")
        confidence = result.get("confidence", 0.0)

        if confidence < 0.6:
            intent = "chat"

        if intent == "command":
            handler = CommandHandler(context=user_input)
        elif intent == "reminder":
            handler = ReminderHandler()            
        else:
            handler = ChatHandler(self.gpt_client)

        return handler.handle(user_input)