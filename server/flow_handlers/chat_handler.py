# server/flow_handlers/chat_handler.py

class ChatHandler:
    def __init__(self, gpt_client=None, context=None):
        self.gpt_client = gpt_client
        self.context = context

    def handle(self, user_input: str, context: dict = None):
        context_to_use = context or self.context
        reply = self.gpt_client.ask(user_voice=user_input)
        return {
            "status": "complete",
            "reply": reply
        }