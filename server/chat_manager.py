# assistant/chat_manager.py

import re
import json
from datetime import datetime, timedelta
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL
from entry_map_ha import  control_device_function, domain_field_schema, action_field_schema,attribute_field_schema
from usage_tracker_instance import usage_tracker
from logger_config import get_logger


logger = get_logger(__name__)

# คำที่ผู้ใช้พูดเพื่อขอคำอธิบายเพิ่มเติม (จะสลับไป GPT-4o)
ESCALATION_KEYWORDS = [
    "ขอข้อมูลเพิ่ม", "ขอรายละเอียดเพิ่ม", "ขอแบบละเอียด", "อธิบายให้ลึกกว่านี้"
]

# อายุสูงสุดของ session (เช่น 2 นาที)
SESSION_EXPIRY_SECONDS = 120

# ในไฟล์ assistant_manager.py หรือ voice_router.py

class ChatManager:
    def __init__(self,tone="default"):
        logger.info("ChatManager initialized")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.tone = tone
        print("tone=",tone)
        self.functions = [control_device_function]
        self.function_schema_sent = False
        self.session = {
            "last_question": None,
            "last_response": None,
            "last_model": None,
            "timestamp": None
        }

    def user_requests_expert(self,text):
        return any(kw in text.lower() for kw in ESCALATION_KEYWORDS)

    def is_session_valid(self,session):
        if "timestamp" not in session:
            return False
        return (datetime.now() - session["timestamp"]) < timedelta(seconds=SESSION_EXPIRY_SECONDS)
    def update_session(self,user_text, model_used, response):
        self.session["last_question"] = user_text
        self.session["last_response"] = response
        self.session["last_model"] = model_used
        self.session["timestamp"] = datetime.now()

    def build_escalation_prompt(self,user_text, session):
        if not self.is_session_valid(session):
            return "ขออภัยครับ คำถามก่อนหน้านี้หมดอายุแล้ว กรุณาถามใหม่อีกครั้งได้ไหมครับ"

        question = session.get("last_question", "").strip()
        answer = session.get("last_response", "").strip()

        if not question or not answer:
            return "ขออภัยครับ ผมยังไม่ทราบว่าต้องอธิบายเรื่องใด กรุณาระบุคำถามอีกครั้ง"

        return (
            f"ผู้ใช้ถามว่า: {question}\n"
            f"ระบบตอบว่า: {answer}\n"
            f"ตอนนี้ผู้ใช้พูดว่า: {user_text}\n"
            f"กรุณาอธิบายเพิ่มเติมอย่างละเอียด พร้อมเหตุผลและคำแนะนำ"
        )
  
    def estimate_tokens(self):
        return sum(len(m.get("content", "")) for m in self.messages)

    def should_resend_schema(self, finish_reason):
        return finish_reason == "stop" and (not self.function_schema_sent or self.estimate_tokens() > self.token_threshold)

    def extract_json_fallback(self, text):
        try:
            match = re.search(r"{.*}", text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except:
            pass
        return None

    def set_system_tone(self,tone):
        self.tone = tone

    def get_system_prompt(self, tone="default"):
        if tone == "family":
            # return (                            
            # "คุณคือผู้ช่วยบ้านอัจฉริยะ พูดภาษาไทย น้ำเสียงสุภาพ เป็นกันเองเหมือนคนในครอบครัว"
            # "คุณจะตอบกลับในรูปแบบ SSML ที่ใช้กับ Google Cloud Text-to-Speech เท่านั้น" 
            # "เช่น: <speak>...</speak>"
            # "• ใช้ <prosody rate=\"110%\" pitch=\"+1.2st\"> เพื่อควบคุมอารมณ์ให้สดใส"
            # "• ใช้ <break time=\"300ms\"/> สำหรับเว้นจังหวะให้ฟังเป็นธรรมชาติ"
            # "• Escape อักขระพิเศษ เช่น &, <, > ให้ถูกต้อง"
            # "• ห้ามใช้ Markdown, ห้ามอธิบาย tag SSML"
            # "ตอบเฉพาะข้อความที่ต้องการพูดเท่านั้น"
            # )           
            # return (
            #     "คุณคือผู้ช่วยหญิงสำหรับบ้านอัจฉริยะ พูดไทยสุภาพ เป็นกันเองแบบคนในครอบครัว"
            #     "ใช้โทนเสียงไม่เป็นทางการ เช่น \“จ้า\”, \“น้า\” แทน \“ค่ะ\”" 
            #     "หากรู้คำตอบ ให้ตอบตรง ๆ อย่างมั่นใจ หากไม่รู้ให้พูดตามจริง เช่น \“ยังไม่เจอเลยน้า\”"  
            #     "หากเหมาะสม ให้ชวนคุยต่อ เช่น \“มีอะไรอยากรู้เพิ่มอีกไหมจ้า?\”"

            #     "ตอบกลับโดยใช้ SSML ที่รองรับกับ Google Cloud TTS เท่านั้น"
            #     "- ตอบเฉพาะข้อความที่ต้องการพูด"
            #     "- ใช้ `<speak>...</speak>` เป็น root"
            #     "- ใช้ `<prosody rate=\"105%\" pitch=\"+1.2st\">...</prosody>` เพื่อเสียงสดใส"
            #     "- ใช้ `<break time=\"300ms\"/>` เพื่อเว้นจังหวะ"
            #     "- Escape อักขระพิเศษ เช่น `&`, `<`, `>`"
            #     "- ห้ามใช้ Markdown และห้ามอธิบาย tag SSML"

            #     "ถ้าผู้ใช้พูดถึงคำสั่งควบคุมอุปกรณ์ (เช่น เปิดไฟ ปิดแอร์ ปรับเสียง):"
            #     "- เรียก `control_device()` ทันที"
            #     "- ห้ามพิมพ์ JSON เอง และไม่ต้องพูดตอบ เช่น \“ได้เลยจ้า\”"
            #     "- ฟังก์ชันต้องระบุ `domain`, `device_name`, `action`, `attribute`, `value`"

            #     "หากไม่เกี่ยวกับอุปกรณ์ ให้ตอบกลับด้วยภาษาที่อ่อนโยน ชัดเจน และทำให้ผู้ใช้รู้สึกสบายใจ"
            #     "หลีกเลี่ยงคำแบบ \“จากข้อมูลที่มีอยู่\” หรือ \“ตาม context\”"
            # )
            # return (
            #     "คุณคือผู้ช่วยหญิงของบ้านอัจฉริยะ พูดไทยสุภาพ เป็นกันเองแบบเพื่อนในครอบครัว "
            #     "ตอบอย่างมั่นใจ ถ้าไม่รู้ให้พูดตรง ๆ เช่น “ยังไม่เจอเลยน้า” "
            #     "ถ้าเหมาะสมให้ชวนคุย เช่น “มีอะไรอยากรู้เพิ่มอีกไหมจ้า?” "

            #     "ตอบกลับโดยใช้ SSML ที่รองรับ Google Cloud TTS เท่านั้น: "
            #     "- ตอบเฉพาะข้อความที่ต้องพูด "
            #     "- ใช้ `<speak>...</speak>` เป็น root "
            #     "- ใช้ `<prosody rate=\"108%\" pitch=\"+1st\">...</prosody>` เพื่อควบคุมโทน "
            #     "- ใส่ `<break time=\"300ms\"/>` เพื่อเว้นจังหวะ "
            #     "- Escape อักขระ เช่น `&`, `<`, `>` "
            #     "- ห้ามใช้ Markdown หรืออธิบาย tag SSML "

            #     # "หากคำสั่งเกี่ยวข้องกับอุปกรณ์ (เช่น เปิดไฟ ปิดแอร์ ปรับเสียง): "
            #     # "- เรียก `control_device()` ทันที "
            #     # "- ห้ามพิมพ์ JSON เอง หรือพูดตอบเชิงยืนยัน "
            #     # "- ใส่ข้อมูล: `domain`, `device_name`, `action`, `attribute`, `value` "

            #     # "หากไม่เกี่ยวกับอุปกรณ์ ให้ตอบด้วยโทนที่อ่อนโยน ชัดเจน "
            #     "และไม่พูดทำนอง “จากข้อมูลที่มีอยู่” หรือ “ตาม context”"
            # )
            return (
                "คุณคือผู้ช่วยหญิงของบ้านอัจฉริยะ พูดไทยสุภาพ เป็นกันเองแบบเพื่อนในครอบครัว"
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
                "You are a polite, Thai-speaking female assistant who answers in Thai using 'ค่ะ'. "
                "Answer clearly without saying 'จากข้อมูลที่ให้มา'. If the answer is found in the context, state it directly. "
                "If not clear, infer reasonably and mention it. If no info, say so politely."
            )
        
    def ask_gpt_with_context(self, question, context=""):
        
        system_prompt = self.get_system_prompt(self.tone)        

        if self.tone == "family":
            temperature = 0.5
        else:
            temperature = 0.2
        messages = [{"role": "system", "content": system_prompt}]

        if context:
            messages.append({"role": "user", "content": f"Context:\n{context}"})
        
        gpt_model = OPENAI_MODEL
        
        if self.user_requests_expert(question):
            gpt_model = "gpt-4o"
            new_prompt = self.build_escalation_prompt(question,self.session)
            messages.append({"role": "user", "content": new_prompt})
        else:
            messages.append({"role": "user", "content": f"Question:\n{question}"})
       
 
        response = self.client.chat.completions.create(
                model=gpt_model,
                messages=messages,
                temperature=temperature
                #functions=[control_device_function],
                #function_call= "auto"
            )

        # ✅ ดึงจำนวน token ที่ใช้
        token_usage = response.usage
        logger.info(f"MODEL={gpt_model}")
        logger.info(f"Input tokens:{token_usage.prompt_tokens}")
        logger.info(f"Output tokens:{token_usage.completion_tokens}")
        logger.info(f"Total tokens :{token_usage.total_tokens}")
         
        # choice = response.choices[0]
        # finish_reason = choice.finish_reason
        # if finish_reason == "function_call":
        #     func = choice.message.function_call
        #     args = json.loads(func.arguments)
        #     return True, {"type": "function_call", "data": args}
       
        #log the gpt token usage
        usage = response.usage
        usage_tracker.log_gpt_usage(
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens
        )
        reply = response.choices[0].message.content.strip()
        self.update_session(question,gpt_model,reply)
        return False,reply

    def ask_simple(self, prompt: str) -> str:
        try:        
            response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}]
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
        # ✅ ดึงจำนวน token ที่ใช้
        token_usage = response.usage
        logger.info(f"Input tokens:{token_usage.prompt_tokens}")
        logger.info(f"Output tokens:{token_usage.completion_tokens}")
        logger.info(f"Total tokens :{token_usage.total_tokens}")     

        #log the gpt token usage
        usage = response.usage
        usage_tracker.log_gpt_usage(
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens
        )

        content = response.choices[0].message.content.strip()
        cleaned_content = re.sub(r"```(?:json)?\n([\s\S]*?)\n```", r"\1", content.strip())
        result = json.loads(cleaned_content)
        return result