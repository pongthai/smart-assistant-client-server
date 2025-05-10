# assistant/assistant_manager.py

import threading
import time
import os
import sys
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
        self.tracker = LatencyLogger()
        self.gpt_client_proxy = GPTProxyClient()
        
        # Start command listener
       # threading.Thread(target=self.voice_listener.command_listener, daemon=True).start()

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
                self.audio_manager.speak(HELLO_MSG)
                self.last_interaction_time = time.time()
                time.sleep(1)
                continue            
            
            if not self.audio_manager.is_sound_playing:
                #logger.info("Start Listening")
                
                user_voice = self.voice_listener.listen()
                
                if not user_voice:
                    continue
                self.tracker.mark("user_said")                
                logger.info(f"🗣️ User said: {user_voice}")
                self.last_interaction_time = time.time()

                response = self.voice_command_handler.parse_command_action(user_voice)
                
                #if the user_voice is command then skip - not send to chatGPT
                if response:
                    continue
                self.tracker.mark("sending to chatgpt")
                logger.info(f"Sending to ChatGPT..text={user_voice}")                      
                answer = self.gpt_client_proxy.ask(user_voice)     
                logger.info(f"ChatGPT={answer}")                         
                
                self.tracker.mark("return from server - start speaking")
                self.audio_manager.speak(answer)
                self.tracker.mark("return from speaking")
                self.tracker.report()
                self.last_interaction_time = time.time()

        logger.info("👋 Program exiting... Goodbye!")
        self.memory_manager.close()

    def get_conversation_history(self, limit=5):
        memories = self.memory_manager.get_recent_memories(limit=limit)

        if not memories:
            return ""

        context = ""
        for role, summary in reversed(memories):
            context += f"{role.capitalize()}: {summary}\n"

        return context.strip()
