import requests
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from  config import GPT_SERVER_ENDPOINT

class GPTProxyClient:
    def __init__(self, server_url=GPT_SERVER_ENDPOINT):
        self.server_url = server_url

    def ask(self, user_voice: str) -> str:
        try:
            payload = {
                "user_voice": user_voice                
            }
            response = requests.post(self.server_url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json().get("response", "❌ ไม่มีคำตอบ")
        except Exception as e:
            print(f"❌ Error contacting GPT server: {e}")
            return "❌ เกิดข้อผิดพลาดในการเชื่อมต่อ GPT Server"