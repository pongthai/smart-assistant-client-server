# assistant/assistant_manager.py

import threading
import time
import os
import sys
import re
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import IDLE_TIMEOUT,  HELLO_MSG
from audio_manager import AudioManager
from voice_listener import VoiceListener
from voice_command_handler import VoiceCommandHandler
from latency_logger import LatencyLogger
from gpt_client_proxy import GPTProxyClient


from logger_config import get_logger

logger = get_logger(__name__)

class AssistantManager:
    def __init__(self):
        logger.info("AssistantManager initialized")
        # 🔥 เตรียม Event เพื่อ Sync Wake Word
        self.wake_word_detected = threading.Event()
        self.should_exit = False
        self.conversation_active = False
        self.last_interaction_time = time.time()
        self.previous_question = None

        self.audio_manager = AudioManager(self)
        self.voice_listener = VoiceListener(self)
        self.voice_command_handler = VoiceCommandHandler()      
        
        self.gpt_client_proxy = GPTProxyClient()
        
        # Start command listener
       # threading.Thread(target=self.voice_listener.command_listener, daemon=True).start()

    import re

    def is_valid_ssml(self,text: str) -> bool:
        """
        ตรวจว่า text อยู่ในรูปแบบ SSML ที่ใช้งานได้กับ Google Cloud TTS หรือไม่
        - ต้องมี <speak>...</speak> ครอบ
        - tag ต้องไม่ผิดรูป เช่น <prosody><break/></prosody> → ❌
        - ไม่ควรมี tag ที่ไม่รองรับ เช่น <b>, <i>, <markdown>
        - <break> ต้องเป็น self-closing
        """

        if not isinstance(text, str):
            return False

        # ต้องมี <speak> ครอบ
        if not re.search(r"<speak>.*</speak>", text, re.DOTALL):
            return False

        # ตรวจว่าไม่มี <break> อยู่ใน <prosody>
        prosody_blocks = re.findall(r"<prosody[^>]*>(.*?)</prosody>", text, re.DOTALL)
        for inner in prosody_blocks:
            if "<break" in inner:
                return False

        # ตรวจว่า <break> เป็น self-closing
        invalid_breaks = re.findall(r"<break[^>]*/?>", text)
        for b in invalid_breaks:
            if not b.endswith("/>"):
                return False

        # tag ที่ Google TTS รองรับ
        allowed_tags = {"speak", "prosody", "break", "emphasis", "p", "s", "say-as"}
        found_tags = re.findall(r"</?(\w+)", text)
        for tag in found_tags:
            if tag not in allowed_tags:
                return False

        return True

    def check_idle(self):
        """ถ้าไม่มี interaction นานเกิน IDLE_TIMEOUT ให้กลับไป Idle Mode"""
        if self.conversation_active and (time.time() - self.last_interaction_time > IDLE_TIMEOUT):
            print("⌛ Conversation idle timeout. Going back to Wake Word mode.")
            self.conversation_active = False

    def run(self):
        logger.info("🚀 Assistant Started. Waiting for Wake Word...")

        while not self.should_exit:
            self.check_idle()

            if not self.conversation_active and not self.audio_manager.is_sound_playing:                
                logger.info("⌛ Waiting for Wake Word...")
                self.wake_word_detected.wait()      # ✅ รอ Wake Word
                self.wake_word_detected.clear()     # ✅ เคลียร์ event สำหรับรอบถัดไป
                self.conversation_active = True
                self.audio_manager.speak_from_server(HELLO_MSG)
                self.last_interaction_time = time.time()
                time.sleep(1)
                continue            
            
            if not self.audio_manager.is_sound_playing:
                #logger.info("Start Listening")                

                user_voice = self.voice_listener.listen()
                
                if not user_voice:
                    continue
                self.tracker = LatencyLogger()
                self.tracker.mark("user_said")                
                logger.info(f"🗣️ User said: {user_voice}")
                self.last_interaction_time = time.time()   
                
                #response = self.voice_command_handler.parse_command_action(user_voice)
                
                #if the user_voice is command then skip - not send to chatGPT
                #if response:
                #    continue

                self.tracker.mark("sending to chatgpt")
                logger.info(f"Sending to ChatGPT..text={user_voice}")                      
                answer = self.gpt_client_proxy.ask(user_voice)     
                logger.info(f"ChatGPT={answer}")                         
                
                self.tracker.mark("return from server - start speaking")
                if re.search(r"<speak>.*</speak>", answer, re.DOTALL):
                    is_ssml = True 
                else:
                    is_ssml = False
                self.audio_manager.speak_from_server(answer,is_ssml)
                self.tracker.mark("return from speaking")
                self.tracker.report()
                self.last_interaction_time = time.time()

        logger.info("👋 Program exiting... Goodbye!")
        #self.memory_manager.close()

    def get_conversation_history(self, limit=5):
        memories = self.memory_manager.get_recent_memories(limit=limit)

        if not memories:
            return ""

        context = ""
        for role, summary in reversed(memories):
            context += f"{role.capitalize()}: {summary}\n"

        return context.strip()
