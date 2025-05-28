from typing import Dict
from openai import OpenAI
from .intent_definitions import INTENT_DEFINITIONS
from config import OPENAI_API_KEY, OPENAI_MODEL
from logger_config import get_logger

logger = get_logger(__name__)

class IntentClassifier:
    def __init__(self, model=OPENAI_MODEL, api_key=OPENAI_API_KEY):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.intent_definitions = INTENT_DEFINITIONS

    def classify(self, text: str):
        return self.classify_intent(text)

    def classify_intent(self, user_input: str) -> Dict:
        prompt = self._build_prompt(user_input)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "คุณคือ AI ที่ช่วยระบุ intent ของข้อความผู้ใช้"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
            )
            result = response.choices[0].message.content.strip()
            logger.info(f"[classify_intent] 🧠 Result: {result}")
            logger.info(f"[classify_intent] 🔢 Token usage: {response.usage}")
            return self._parse_result(result)
        except Exception as e:
            logger.error(f"[classify_intent] ❌ Error: {e}")
            return {"intent": "unknown", "confidence": 0.0}

    def _build_prompt(self, user_input: str) -> str:
        intent_lines = []
        for intent, meta in self.intent_definitions.items():
            desc = meta["description"]
            examples = "\n".join(f"- {ex}" for ex in meta["examples"])
            intent_lines.append(f"{intent}:\n  ความหมาย: {desc}\n  ตัวอย่าง:\n{examples}")
        intents_description = "\n\n".join(intent_lines)

        return (
            f"ต่อไปนี้คือคำอธิบาย intent ต่าง ๆ ที่ระบบรู้จัก:\n\n"
            f"{intents_description}\n\n"
            f"ตอนนี้มีข้อความจากผู้ใช้ดังนี้:\n\"{user_input}\"\n"
            f"โปรดระบุ intent ที่ตรงที่สุด พร้อมระดับความมั่นใจ (0-1) และคำอธิบายเหตุผล\n"
            f"ตอบกลับในรูปแบบ JSON เช่น: "
            f"{{\"intent\": \"command\", \"confidence\": 0.92, \"explanation\": \"ผู้ใช้มีเจตนาสั่งเปิดอุปกรณ์\"}}"
        )

    def _parse_result(self, result_str: str):
        try:
            import json
            return json.loads(result_str)
        except Exception:
            return {"intent": "unknown", "confidence": 0.0}