from server.prompt_manager import get_prompt_for_intent, IntentType
from server.gpt_integration import GPTClient
import json
import re
from logger_config import get_logger

logger = get_logger(__name__)

class ReminderHandler:
    def __init__(self):
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
                    "prompt": prompt
                }

            return {
                "status": "ready",
                "action": {
                    "type": "create_reminder",
                    "time": time,
                    "text": message
                },
                "prompt": f"รับทราบ จะเตือนคุณว่า '{message}' เวลา {time}"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"เกิดข้อผิดพลาดในการสกัดข้อมูล: {e}"
            }