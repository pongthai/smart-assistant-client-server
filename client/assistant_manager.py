# assistant/assistant_manager.py

import threading
import time
import os
import sys
import re
import platform
import datetime
from dateutil import tz
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import IDLE_TIMEOUT,  HELLO_MSG
from audio_manager import AudioManager
from voice_listener import VoiceListener
from voice_command_handler import VoiceCommandHandler
from latency_logger import LatencyLogger
from gpt_client_proxy import GPTProxyClient


from logger_config import get_logger
stop_processing_sound_event = threading.Event()  # ใช้หยุด loop การเล่นเสียง

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

    def stop_processing_sound(self):
        stop_processing_sound_event.set()

    def play_processing_loop(self):
        def _play():
            sound_file = "processing_sound.mp3"
            system = platform.system()
            while not stop_processing_sound_event.is_set():
                if system == "Darwin":
                    os.system(f"afplay {sound_file}")
                elif system == "Linux":
                    os.system(f"mpg123 {sound_file}")
                elif system == "Windows":
                    import winsound
                    winsound.PlaySound(sound_file, winsound.SND_FILENAME)
                time.sleep(1.0)  # เว้นช่วงระหว่างเสียง

        stop_processing_sound_event.clear()  # reset ก่อนเล่นใหม่
        threading.Thread(target=_play, daemon=True).start()

    def play_processing_sound(self,n_times=1, delay=0.2):
        def _play():
            sound_file = "processing_sound.mp3"
            system = platform.system()
            for _ in range(n_times):
                if system == "Darwin":  # macOS
                    os.system(f"afplay {sound_file}")
                elif system == "Linux":
                    os.system(f"mpg123 {sound_file}")  # หรือ aplay ถ้าใช้ .wav
                elif system == "Windows":
                    import winsound
                    winsound.PlaySound(sound_file, winsound.SND_FILENAME)
                time.sleep(delay)  # เว้นจังหวะระหว่างรอบ

        threading.Thread(target=_play, daemon=True).start()

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

    def insert_today_if_needed(self,text):
        keywords = ["วันนี้", "พรุ่งนี้", "เมื่อวาน"]
        now = datetime.datetime.now(tz=tz.gettz("Asia/Bangkok"))

        replacements = {
            "วันนี้": now.strftime("%A, %d %B %Y"),  # หรือ just: now.date().isoformat()
            "พรุ่งนี้": (now + datetime.timedelta(days=1)).strftime("%A, %d %B %Y"),
            "เมื่อวาน": (now - datetime.timedelta(days=1)).strftime("%A, %d %B %Y"),
        }

        for k, v in replacements.items():
            if k in text:
                text = text.replace(k, f"{k} ({v})")
        
        return text

    def text_to_ssml(self,text: str, rate: str = "100%", pitch: str = "+1.1st") -> str:
        """
        Convert normal text into a simple SSML format for Google Cloud TTS.

        Args:
            text (str): Input text to convert.
            rate (str): Speaking rate (e.g., "105%").
            pitch (str): Voice pitch (e.g., "+2st", "-1st").

        Returns:
            str: SSML string.
        """
        import html

        # Escape special XML characters like &, <, > etc.
        escaped_text = html.escape(text)

        ssml = f"""<speak><prosody rate="{rate}" pitch="{pitch}">{escaped_text}</prosody></speak>"""
        return ssml


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
                self.audio_manager.speak_from_server(self.text_to_ssml(HELLO_MSG),is_ssml=True)
                self.last_interaction_time = time.time()
                time.sleep(1)
                continue            
            
            if not self.audio_manager.is_sound_playing:
                #logger.info("Start Listening")                

                user_voice = self.voice_listener.listen()
                #user_voice = self.insert_today_if_needed(user_voice)
                
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
                self.play_processing_loop()
                self.tracker.mark("sending to chatgpt")
                logger.info(f"Sending to ChatGPT..text={user_voice}")                      
                answer = self.gpt_client_proxy.ask(user_voice)
                self.stop_processing_sound()     
                logger.info(f"ChatGPT={answer}")                         
                
                self.tracker.mark("return from server - start speaking")
                
                if not re.search(r"<speak>.*</speak>", answer, re.DOTALL):
                    answer = self.text_to_ssml(answer)
                
                self.audio_manager.speak_from_server(answer,is_ssml=True)
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
