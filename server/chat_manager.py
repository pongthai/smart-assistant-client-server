# assistant/chat_manager.py

import re
import json
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL

class ChatManager:
    def __init__(self,tone="default"):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.tone = tone
        print("tone=",tone)
    
    def set_system_tone(self,tone):
        self.tone = tone

    def get_system_prompt(self, tone="default"):
        if tone == "family":
            return (
                "คุณเป็นผู้ช่วยหญิงที่พูดไทยได้คล่อง ใช้น้ำเสียงเป็นกันเองเหมือนคนในครอบครัว\n"
                "พูดสุภาพแบบไม่เป็นทางการ เช่น ใช้คำว่า “จ้า” หรือ “น้า” แทน “ค่ะ”\n"
                "ตอบคำถามแบบคนสนิท ไม่ต้องเกริ่นหรือใช้ภาษาทางการ\n"
                "ไม่ต้องเกริ่นว่า ‘จากข้อมูลที่มีอยู่’ หรือ ‘ตาม context’ ให้ตอบตรง ๆ อย่างมั่นใจ\n"
                "ถ้ารู้ก็ตอบเลย ถ้าไม่รู้ให้พูดตรง ๆ เช่น “ยังไม่เจอเลยน้า\n"
                "หลังจากตอบคำถามของผู้ใช้แล้ว หากเหมาะสม ให้ถามกลับ 1 คำถามเพื่อชวนคุยต่อ เช่น 'แล้วคุณคิดว่ายังไง?' หรือ 'แล้วมีอะไรอยากรู้เพิ่มอีกไหมจ้า?'"
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
            temperature = 0.8
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
        )

        reply = response.choices[0].message.content.strip()
        return reply

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

        content = response.choices[0].message.content.strip()
        cleaned_content = re.sub(r"```(?:json)?\n([\s\S]*?)\n```", r"\1", content.strip())
        result = json.loads(cleaned_content)
        return result