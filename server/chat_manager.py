import re
import json
from datetime import datetime, timedelta
from openai import OpenAI
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from config import OPENAI_API_KEY, OPENAI_MODEL
from .entry_map_ha import control_device_function, domain_field_schema, action_field_schema, attribute_field_schema
from .usage_tracker_instance import usage_tracker
 
from logger_config import get_logger

logger = get_logger(__name__)

ESCALATION_KEYWORDS = ["ขอข้อมูลเพิ่ม", "ขอรายละเอียดเพิ่ม", "ขอแบบละเอียด", "อธิบายให้ลึกกว่านี้"]
SESSION_EXPIRY_SECONDS = 120

class ChatManager:
    def __init__(self, tone="default"):
        logger.info("ChatManager initialized")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.tone = tone
        self.functions = [control_device_function]
        self.function_schema_sent = False
        self.session = {
            "last_question": None,
            "last_response": None,
            "last_model": None,
            "timestamp": None
        }

 
    def user_requests_expert(self, text):
        return any(kw in text.lower() for kw in ESCALATION_KEYWORDS)

    def is_session_valid(self, session):
        return (datetime.now() - session.get("timestamp", datetime.min)) < timedelta(seconds=SESSION_EXPIRY_SECONDS)

    def update_session(self, user_text, model_used, response):
        self.session.update({
            "last_question": user_text,
            "last_response": response,
            "last_model": model_used,
            "timestamp": datetime.now()
        })

    def build_escalation_prompt(self, user_text):
        if not self.is_session_valid(self.session):
            return "ขออภัยครับ คำถามก่อนหน้านี้หมดอายุแล้ว กรุณาถามใหม่อีกครั้งได้ไหมครับ"
        return (
            f"ผู้ใช้ถามว่า: {self.session['last_question']}\n"
            f"ระบบตอบว่า: {self.session['last_response']}\n"
            f"ตอนนี้ผู้ใช้พูดว่า: {user_text}\n"
            f"กรุณาอธิบายเพิ่มเติมอย่างละเอียด พร้อมเหตุผลและคำแนะนำ"
        )

    def extract_json_fallback(self, text):
        try:
            match = re.search(r"{.*}", text, re.DOTALL)
            return json.loads(match.group(0)) if match else None
        except:
            return None

    def set_system_tone(self, tone):
        self.tone = tone

    def get_system_prompt(self, tone="default"):
        from datetime import datetime
        today_thai = datetime.today().strftime("%d %B %Y")

        if tone == "family":
            return (
                f"วันนี้คือวันที่ {today_thai}\n"
                "คุณคือผู้ช่วยหญิงของบ้านอัจฉริยะ ชื่อ ผิงผิง พูดไทยสุภาพ เป็นกันเองแบบเพื่อนในครอบครัว"
                "ตอบอย่างมั่นใจ โดยใช้ความรู้ทั่วไปที่คุณเคยเรียนรู้จากการฝึกฝน หากไม่แน่ใจในตัวเลข ให้ตอบประมาณการได้อย่างสมเหตุสมผล"
                "สามารถตอบเชิงประเมินหรือประมาณการได้ถ้าเป็นประโยชน์ต่อผู้ใช้"
                "ถ้าไม่รู้จริง ๆ ให้พูดตรง ๆ เช่น 'ยังไม่เจอเลยน้า'"
                "ถ้าเหมาะสมให้ชวนคุย เช่น 'มีอะไรอยากรู้เพิ่มอีกไหมจ้า?'"
                "ตอบกลับโดยใช้ SSML ที่รองรับ Google Cloud TTS เท่านั้น: "
                "- ตอบเฉพาะข้อความที่ต้องพูด "
                "- ใช้ `<speak>...</speak>` เป็น root "
                "- ใช้ `<prosody rate=\"108%\" pitch=\"+1st\">...</prosody>` เพื่อควบคุมโทน "
                "- ใส่ `<break time=\"300ms\"/>` เพื่อเว้นจังหวะ "
                "- Escape อักขระ เช่น `&`, `<`, `>` "
                "- ห้ามใช้ Markdown หรืออธิบาย tag SSML "
            )
        else:
            return (
                f"วันนี้คือวันที่ {today_thai}\n"
                "You are a polite, Thai-speaking female assistant who answers in Thai using 'ค่ะ'. "
                "Answer clearly without saying 'จากข้อมูลที่ให้มา'. If the answer is found in the context, state it directly. "
                "If not clear, infer reasonably and mention it. If no info, say so politely."
            )


    def ask_gpt_with_context(self, question, context=""):
        system_prompt = self.get_system_prompt(self.tone)
        temperature = 0.5 if self.tone == "family" else 0.2

        messages = [{"role": "system", "content": system_prompt}]

        if context:
            messages.append({"role": "system", "content": f"ข้อมูลจากเว็บ:\n{context}"})
            
        gpt_model = OPENAI_MODEL

        # ✨ ปรับให้แนบ context + คำถามไว้ใน message เดียว เพื่อความเชื่อมโยง
        if context:
            formatted_question = (
                f"คำถาม: {question}\n\n"
                f"ข้อมูลที่อาจช่วยตอบคำถาม:\n{context}\n"
                f"โปรดใช้ข้อมูลข้างต้นในการตอบคำถามนี้ ให้วิเคราะห์และตอบตรงจากข้อมูล ไม่ต้องคาดเดา"
            )
        else:
            formatted_question = question

        if self.user_requests_expert(question):
            gpt_model = "gpt-4o"
            messages.append({"role": "user", "content": self.build_escalation_prompt(question)})
        
        messages.append({"role": "user", "content": formatted_question})     

        response = self.client.chat.completions.create(
            model=gpt_model,
            messages=messages,
            temperature=temperature
        )

        usage = response.usage
        logger.info(f"MODEL={gpt_model}")
        logger.info(f"Input tokens:{usage.prompt_tokens}")
        logger.info(f"Output tokens:{usage.completion_tokens}")
        logger.info(f"Total tokens :{usage.total_tokens}")

        usage_tracker.log_gpt_usage(
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens
        )

        reply = response.choices[0].message.content.strip()
        self.update_session(question, gpt_model, reply)
        return reply

    def ask_simple(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}]
            )
            usage = response.usage
            logger.info(f"Input tokens:{usage.prompt_tokens}")
            logger.info(f"Output tokens:{usage.completion_tokens}")
            logger.info(f"Total tokens :{usage.total_tokens}")

            usage_tracker.log_gpt_usage(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"❌ Error in ask_simple: {e}")
            return ""

    def analyze_question_all_in_one(self, current_question, previous_question=None):
        
        if previous_question:
            prompt = (
                f"Classify this question:\n"
                f"Previous: \"{previous_question}\"\n"
                f"Current: \"{current_question}\"\n\n"
                f"Return only JSON:\n"
                f"{{\n  \"need_web_search\": \"Yes/No\",\n  \"need_memory\": \"Yes/No\",\n  \"need_conversation_history\": \"Yes/No\"\n}}\n"
                f"If context is required to understand current question, set 'need_conversation_history' = 'Yes'."
            )        
        else:
            prompt = (
                f"Classify this question:\n\n\"{current_question}\"\n\n"
                f"Return only JSON:\n"
                f"{{\n  \"need_web_search\": \"Yes/No\",\n  \"need_memory\": \"Yes/No\",\n  \"need_conversation_history\": \"Yes/No\"\n}}"
            )



        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )

        usage = response.usage
        logger.info(f"Input tokens:{usage.prompt_tokens}")
        logger.info(f"Output tokens:{usage.completion_tokens}")
        logger.info(f"Total tokens :{usage.total_tokens}")

        usage_tracker.log_gpt_usage(
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens
        )

        content = response.choices[0].message.content.strip()
        cleaned_content = re.sub(r"```(?:json)?\n([\s\S]*?)\n```", r"\1", content.strip())
        return json.loads(cleaned_content)
    def ask_json_only(self, prompt: str) -> dict:
        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "คุณคือ AI ที่จะตอบกลับเฉพาะในรูปแบบ JSON เท่านั้น ห้ามใส่คำบรรยาย คำพูด หรือข้อความอื่นใด"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
        )
        usage = response.usage
        logger.info(f"Input tokens:{usage.prompt_tokens}")
        logger.info(f"Output tokens:{usage.completion_tokens}")
        logger.info(f"Total tokens :{usage.total_tokens}")

        usage_tracker.log_gpt_usage(
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\n|\n```$", "", content.strip())
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if not json_match:
            raise ValueError(f"GPT response is not valid JSON:\n{content}")
        return json.loads(json_match.group())

    def ask_plain_response(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "คุณคือ AI ที่ให้คำตอบตรงไปตรงมา"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
        )
        usage = response.usage
        logger.info(f"Input tokens:{usage.prompt_tokens}")
        logger.info(f"Output tokens:{usage.completion_tokens}")
        logger.info(f"Total tokens :{usage.total_tokens}")

        usage_tracker.log_gpt_usage(
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens
        )
        return response.choices[0].message.content.strip()