# gpt_client_proxy.py

import requests
import os
import sys
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import GPT_SERVER_ENDPOINT, SESSION_ID

logger = logging.getLogger(__name__)

class GPTProxyClient:
    def __init__(self, server_url=GPT_SERVER_ENDPOINT):
        self.server_url = server_url

    def ask(self, user_text: str) -> str:
        payload = {
            "user_voice": user_text,
            "session_id": SESSION_ID
        }
        try:
            response = requests.post(self.server_url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "❌ ไม่พบคำตอบจาก GPT Server")
        except requests.exceptions.Timeout:
            logger.error("❌ Request to GPT server timed out.")
            return "⏱️ GPT Server ใช้เวลานานเกินไปในการตอบกลับ"
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error contacting GPT server: {e}")
            return "❌ เกิดข้อผิดพลาดในการเชื่อมต่อ GPT Server"
        except Exception as e:
            logger.exception("❌ Unexpected error while contacting GPT server")
            return "❌ เกิดข้อผิดพลาดภายในระบบ"