from .command_handler import CommandHandler
from .reminder_handler import ReminderHandler
from .chat_handler import ChatHandler
from .stock_analysis_handler import StockAnalysisHandler
from .news_handler import NewsHandler
from .daily_briefing_handler import DailyBriefingHandler
from .weather_handler import WeatherHandler
from ..intent_classifier.classifier import IntentClassifier
from ..gpt_integration import GPTClient
from ..session_manager import Session
from logger_config import get_logger

logger = get_logger(__name__)

class IntentRouter:
    def __init__(self, gpt_client: GPTClient, intent_classifier: IntentClassifier):
        self.gpt_client = gpt_client
        self.intent_classifier = intent_classifier

    def route(self, user_input: str, session: Session):
        result = self.intent_classifier.classify_intent(user_input)
        intent = result.get("intent", "chat")
        confidence = result.get("confidence", 0.0)

        if confidence < 0.6:
            intent = "chat"

        session.update(intent=intent)
        return self._handle_intent(intent, user_input, session)

    def route_by_state(self, state: str, user_input: str, session: Session):
        if state == "complete":
            # Reset to chat intent for new general input
            session.update(intent="chat", state=None, context_update={})
            return self._handle_intent("chat", user_input, session)

        intent = session.intent or "chat"
        return self._handle_intent(intent, user_input, session)

    def _handle_intent(self, intent: str, user_input: str, session: Session):
        logger.info(f"Intent: {intent}")
        if intent == "home_command":
            handler = CommandHandler(session=session)
        elif intent == "reminder":
            handler = ReminderHandler(session=session)
        elif intent == "stock_analysis":
            handler = StockAnalysisHandler(session=session)
        elif intent == "news_summary":
            handler = NewsHandler(session=session)
        elif intent == "daily_briefing":
            handler = DailyBriefingHandler(session=session)
        elif intent == "weather":
            handler = WeatherHandler(session=session)
        else:
            handler = ChatHandler(self.gpt_client)

        result = handler.handle(user_input)
        context_update = {}
        action_data = result.get("action")
        if isinstance(action_data, dict):
            context_update.update(action_data)
        if result.get("status") == "complete":
            # Clear session after successful completion
            session.update(state=None, context_update={})
        else:
            session.update(state=result.get("next_state"), context_update=context_update)
        return result