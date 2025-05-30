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
        return f"""
            คุณคือ AI ที่ทำหน้าที่วิเคราะห์ข้อความของผู้ใช้ แล้วระบุ "intent" ที่ตรงที่สุดเพียงหนึ่งรายการจากรายการด้านล่าง พร้อมระบุระดับความมั่นใจ (0-1) และคำอธิบายประกอบ

            รายการ intent ที่รองรับมีดังนี้:

            - general_chat:
            ความหมาย: การพูดคุยทั่วไป ไม่ได้ขอข้อมูลหรือสั่งงาน
            ตัวอย่าง:
                - สบายดีไหม
                - วันนี้อากาศดีจัง
                - เล่าเรื่องสนุก ๆ ให้ฟังหน่อย
                - How are you?

            - home_command:
            ความหมาย: คำสั่งควบคุมอุปกรณ์ในบ้าน เช่น ไฟ แอร์ ประตู
            ตัวอย่าง:
                - เปิดไฟห้องนั่งเล่น
                - ปิดแอร์ตอนตีหนึ่ง
                - เปิดม่าน
                - Turn off the bedroom light

            - reminder:
            ความหมาย: ขอให้สร้าง ลบ หรือแจ้งเตือนสิ่งใดสิ่งหนึ่ง
            ตัวอย่าง:
                - เตือนฉันให้กินยา 2 ทุ่ม
                - ลบการเตือนเมื่อวาน
                - ตั้งเตือนตอน 9 โมงให้โทรหาหมอ
                - Remind me to take my meds at 8PM

            - news_summary:
            ความหมาย: ขอให้สรุปข่าวล่าสุด หรือข่าวเฉพาะหมวด เช่น เทคโนโลยี พลังงาน
            ตัวอย่าง:
                - ช่วยสรุปข่าวเทคโนโลยีล่าสุดวันนี้
                - ข่าว AI มีอะไรใหม่
                - Trending news in Thailand
                - ข่าวที่เกี่ยวกับพลังงานสะอาดมีอะไรบ้าง

            - stock_analysis:
            ความหมาย: ขอวิเคราะห์แนวโน้มหรือสถานการณ์ของหุ้นตัวใดตัวหนึ่ง
            ตัวอย่าง:
                - วิเคราะห์หุ้น BBL หน่อย
                - หุ้นพลังงานน่าเข้าตอนนี้มั้ย
                - ADVANC มีแนวโน้มยังไง

            - weather:
            ความหมาย: ถามพยากรณ์อากาศ
            ตัวอย่าง:
                - หัวหินพรุ่งนี้ฝนตกไหม
                - วันนี้ที่กรุงเทพอากาศกี่องศา
                - Will it rain tomorrow?

            - daily_briefing:
            ความหมาย: ขอรายงานสรุปประจำวัน
            ตัวอย่าง:
                - แจ้งเตือนวันนี้มีอะไรบ้าง
                - สรุปข่าว หุ้น และกิจกรรมให้หน่อยตอนเช้า
                - Today’s daily briefing please

            - unknown:
            ความหมาย: ข้อความไม่สามารถระบุเจตนาได้แน่ชัด

            โปรดวิเคราะห์ข้อความผู้ใช้ต่อไปนี้:
            \"{user_input}\"

            และตอบกลับในรูปแบบ JSON ที่ถูกต้อง เช่น:
            {{
            "intent": "reminder",
            "confidence": 0.88,
            "explanation": "ผู้ใช้ขอให้ช่วยเตือนเรื่องสำคัญ ซึ่งตรงกับเจตนา reminder"
            }}
            """

    def _parse_result(self, result_str: str):
        try:
            import json
            cleaned = result_str.strip()

            # Remove triple backticks if present
            if cleaned.startswith("```json"):
                cleaned = cleaned.removeprefix("```json").removesuffix("```").strip()
            elif cleaned.startswith("```"):
                cleaned = cleaned.removeprefix("```").removesuffix("```").strip()

            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"[classify_intent] ❌ Failed to parse JSON result: {e}")
            return {"intent": "unknown", "confidence": 0.0}