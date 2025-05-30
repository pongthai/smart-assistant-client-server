from .base_handler import BaseIntentHandler
from server.prompt_manager import get_prompt_for_intent, IntentType
from server.gpt_integration import GPTClient
import json
import re
from logger_config import get_logger
from server.session_manager import session_manager

logger = get_logger(__name__)

class ReminderHandler(BaseIntentHandler):
    def __init__(self, session):
        super().__init__(session)
        self.gpt_client = GPTClient()
    
    def extract_json(self,response_text: str) -> dict:
        try:
            # Adjusted regex to capture JSON objects within the text without recursion
            json_match = re.search(r'\{(?:[^{}]|(?:))*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            else:
                raise ValueError("No valid JSON found in the response")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error decoding JSON: {e}")
            return {"status": "error", "message": f"Error parsing JSON: {e}"}
        except Exception as e:
            logger.error(f"❌ General error in JSON extraction: {e}")
            return {"status": "error", "message": f"General error: {e}"}
    
    def handle_test(self,response_text: str):
        try:
            # Assume the response_text is a string; parse it into JSON
            parsed_response = json.loads(response_text)  # This results in a dict

            # If further processing assumes a string, ensure it's handled appropriately
            if isinstance(parsed_response, dict):
                # Process as dict directly
                logger.info(f"✅ Processed JSON: {parsed_response}")
                
                # Example of accessing data
                time = parsed_response.get("time", "")
                message = parsed_response.get("message", "")

                # Use values; do not attempt strip() on a dict
            else:
                # If for some reason this isn't what you expect, log or handle it
                logger.error("Expected a dict after JSON parsing.")

        except json.JSONDecodeError as e:
            logger.error(f"❌ Error decoding JSON: {e}")
        except Exception as e:
            logger.error(f"❌ General error: {e}")

    def handle(self, user_input: str):
        try:
            current_state = self.session.state
            if current_state == "awaiting_confirmation":
                confirmation_words = ["ใช่", "ตกลง", "โอเค", "ได้เลย", "yes"]
                cancellation_words = ["ไม่", "ไม่ใช่", "ยกเลิก", "หยุด", "no"]
                lowered = user_input.strip().lower()
                if lowered in confirmation_words:
                    self.session.update(state="complete")
                    return {
                        "status": "confirmed",
                        "reply": "บันทึกการเตือนเรียบร้อยแล้ว",
                        "action": {
                            "type": "reminder",
                            "time": self.context.get("time"),
                            "text": self.context.get("message")
                        },
                        "next_state": "complete"
                    }
                elif lowered in cancellation_words:
                    self.session.update(state="complete")
                    return {
                        "status": "cancelled",
                        "reply": "ยกเลิกการสร้างการเตือนแล้ว",
                        "action": {
                            "type": "reminder"
                        },
                        "next_state": "complete"
                    }
                else:
                    return {
                        "status": "awaiting_confirmation",
                        "reply": "กรุณายืนยันว่าใช่หรือไม่",
                        "action": {
                            "type": "reminder"
                        },
                        "next_state": "awaiing_confirmation"
                    }
            prompt = get_prompt_for_intent(IntentType.REMINDER, context=user_input)
            response_text = self.gpt_client.ask_json(prompt)  # ✅ ให้ return raw text ก่อน parse
            if isinstance(response_text, dict):
                parsed = response_text
            else:
                # If unexpected, handle as an error (though should not occur if return type is consistent)
                raise ValueError("Expected the response to be a dictionary")            

            time = parsed.get("time")
            message = parsed.get("message")

            if not time or not message:
                missing = []
                if not time:
                    missing.append("เวลา")
                if not message:
                    missing.append("เนื้อหา")
                prompt = f"กรุณาระบุ {'และ'.join(missing)} สำหรับการเตือนครับ"
                return {
                    "status": "incomplete",
                    "reply": prompt,
                    "action": {
                        "type": "reminder"
                    },
                    "next_state": "awaiting_reminder_info",
                    "context_update": {"partial_input": user_input}
                }

            self.session.update(state="awaiting_confirmation", context_update={
                "time": time,
                "reply": message,

            })

            return {
                "status": "ready",
                "action": {
                    "type": "reminder",
                    "time": time,
                    "text": message
                },
                "reply": f"รับทราบ จะเตือนคุณว่า '{message}' เวลา {time} ใช่หรือไม่?",
                "next_state": "awaiting_confirmation"
            }

        except Exception as e:
            return {
                "status": "error",
                "action": {
                    "type": "reminder"
                },
                "reply": f"เกิดข้อผิดพลาดในการสกัดข้อมูล: {e}"
            }