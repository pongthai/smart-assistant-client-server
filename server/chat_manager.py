# assistant/chat_manager.py

import re
import json
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL
from entry_map_ha import  control_device_function, domain_field_schema, action_field_schema,attribute_field_schema
from usage_tracker_instance import usage_tracker
from logger_config import get_logger

logger = get_logger(__name__)

class ChatManager:
    def __init__(self,tone="default"):
        logger.info("ChatManager initialized")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.tone = tone
        print("tone=",tone)
        self.functions = [control_device_function]
        self.function_schema_sent = False

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
            return (
                "คุณคือผู้ช่วยหญิงของบ้านอัจฉริยะ พูดไทยสุภาพ เป็นกันเองแบบเพื่อนในครอบครัว "
                "ตอบอย่างมั่นใจ ถ้าไม่รู้ให้พูดตรง ๆ เช่น “ยังไม่เจอเลยน้า” "
                "ถ้าเหมาะสมให้ชวนคุย เช่น “มีอะไรอยากรู้เพิ่มอีกไหมจ้า?” "

                "ตอบกลับโดยใช้ SSML ที่รองรับ Google Cloud TTS เท่านั้น: "
                "- ตอบเฉพาะข้อความที่ต้องพูด "
                "- ใช้ `<speak>...</speak>` เป็น root "
                "- ใช้ `<prosody rate=\"105%\" pitch=\"+1.1st\">...</prosody>` เพื่อควบคุมโทน "
                "- ใส่ `<break time=\"300ms\"/>` เพื่อเว้นจังหวะ "
                "- Escape อักขระ เช่น `&`, `<`, `>` "
                "- ห้ามใช้ Markdown หรืออธิบาย tag SSML "

                "หากคำสั่งเกี่ยวข้องกับอุปกรณ์ (เช่น เปิดไฟ ปิดแอร์ ปรับเสียง): "
                "- เรียก `control_device()` ทันที "
                "- ห้ามพิมพ์ JSON เอง หรือพูดตอบเชิงยืนยัน "
                "- ใส่ข้อมูล: `domain`, `device_name`, `action`, `attribute`, `value` "

                "หากไม่เกี่ยวกับอุปกรณ์ ให้ตอบด้วยโทนที่อ่อนโยน ชัดเจน "
                "และไม่พูดทำนอง “จากข้อมูลที่มีอยู่” หรือ “ตาม context”"
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
        
        messages.append({"role": "user", "content": f"Question:\n{question}"})
 
        response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=temperature,
                functions=[control_device_function],
                function_call= "auto"
            )

        # ✅ ดึงจำนวน token ที่ใช้
        token_usage = response.usage
        logger.info(f"MODEL={OPENAI_MODEL}")
        logger.info(f"Input tokens:{token_usage.prompt_tokens}")
        logger.info(f"Output tokens:{token_usage.completion_tokens}")
        logger.info(f"Total tokens :{token_usage.total_tokens}")
         
        choice = response.choices[0]
        finish_reason = choice.finish_reason
        if finish_reason == "function_call":
            func = choice.message.function_call
            args = json.loads(func.arguments)
            return True, {"type": "function_call", "data": args}
       
        #log the gpt token usage
        usage = response.usage
        usage_tracker.log_gpt_usage(
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens
        )
        reply = response.choices[0].message.content.strip()
        return False,reply

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