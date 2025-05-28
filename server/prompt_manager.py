from enum import Enum
from logger_config import get_logger
from datetime import datetime
import re

logger = get_logger(__name__)

class IntentType(str, Enum):
    COMMAND = "command"
    REMINDER = "reminder"
    CHAT = "chat"

PROMPT_TEMPLATES = {
    IntentType.COMMAND: (
        "คุณคือผู้ช่วยอัจฉริยะที่สามารถสั่งการอุปกรณ์ต่าง ๆ ได้\n"
        "คำสั่งจากผู้ใช้:\n{context}\n"
        "โปรดแปลงเป็น action ที่ชัดเจนและเข้าใจได้"
    ),
    IntentType.REMINDER: (
        "คุณคือ AI ที่ช่วยตั้งเตือนความจำให้ผู้ใช้\n"
        "คำขอจากผู้ใช้:\n{context}\n"
        "โปรดวิเคราะห์คำขอและแปลงเป็น JSON ที่ประกอบด้วยสองฟิลด์คือ 'time' และ 'message'\n"
        "- 'time' ควรเป็นวันและเวลาในรูปแบบ ISO 8601 เช่น '2025-05-29T10:00' (รวมทั้งวันที่และเวลา)\n"
        "- 'message' คือสิ่งที่ต้องการให้เตือน เช่น 'กินยา' หรือ 'ประชุมกับทีม'\n"
        "ตัวอย่าง:\n{{ \"time\": \"2025-05-29T08:00\", \"message\": \"กินยา\" }}"
    ),
    IntentType.CHAT: (
        "คุณคือผู้ช่วย AI ที่ตอบคำถามและพูดคุยกับผู้ใช้\n"
        "คำถามหรือข้อความ:\n{context}"
    ),
}

def parse_reminder_request(text: str) -> dict:
    logger.debug(f"🗣️ Original input text: {text}")
    try:
        # Debug log to show regex matching progress
        time_match = re.search(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b|\b[0-1]?[0-9](?:AM|PM)\b", text)
        if time_match:
            time_str = time_match.group(0)
        else:
            logger.warning("⚠️ No time found, defaulting to '08:00'")
            time_str = "08:00"

        # Assuming the message is the remainder of the input after the time
        message = text.replace(time_str, "").strip()

        logger.debug(f"🔧 Parsed time: {time_str}, Parsed message: {message}")

        return {"time": time_str, "message": message}
    except Exception as e:
        logger.error(f"❌ Error parsing reminder request: {e}")
        return {"status": "error", "message": f"เกิดข้อผิดพลาดในการสกัดข้อมูล: {e}"}
    
def get_prompt_for_intent(intent_type: IntentType, context: str) -> str:
    logger.info(f"🔧 Generating prompt for intent: {intent_type}")
    logger.debug(f"📝 Raw context: {context}")
    template = PROMPT_TEMPLATES.get(intent_type)
    if template:
        try:
            # Substitute the context using str.format()
            today = datetime.now().strftime("%Y-%m-%d")
            enriched_context = f"วันนี้คือวันที่ {today}\n{context}"
            prompt = template.format(context=enriched_context)
            logger.debug(f"📜 Substituted Prompt: {prompt}")
            return prompt
        except KeyError as e:
            logger.error(f"❌ Error in template substitution: {e}")
            return template.replace("{context}", context)
    logger.warning("⚠️ Unknown intent type")
    return context

# Singleton instance for external use
class PromptManager:
    def get_prompt(self, intent_type: IntentType, context: str) -> str: 
        logger.info(f"🔧 Generating prompt for intent: {intent_type}") 
        logger.info(f"🧩 Context: {context}")
        if intent_type == IntentType.REMINDER:
            parsed_data = parse_reminder_request(context)
            logger.info(f"📦 Prepared JSON response: {parsed_data}")
            return str(parsed_data)
        return get_prompt_for_intent(intent_type, context)

prompt_manager_instance = PromptManager()
