# assistant_manager.py

import threading
import time
import os
import sys
import re
import datetime
from enum import Enum
from dateutil import tz
import soundfile as sf
import sounddevice as sd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import IDLE_TIMEOUT, HELLO_MSG
from audio_controller import AudioController
from voice_listener import VoiceListener
from command_handler import CommandHandler
from latency_logger import LatencyLogger
from gpt_client_proxy import GPTProxyClient
from command_detector import CommandDetector
from reminder_manager import ReminderManager
from logger_config import get_logger
from home_assistant_bridge import transform_command_for_ha, send_command_to_ha


logger = get_logger(__name__)

class AssistantState(Enum):
    IDLE = 0
    LISTENING = 1
    CONFIRMING_COMMAND = 2
    RESPONDING = 3

class AssistantManager:
    def __init__(self):
        logger.info("AssistantManager initialized")

        self.state = AssistantState.IDLE
        self.state_lock = threading.Lock()

        self.wake_word_detected = threading.Event()
        self.should_exit = False
        self.last_interaction_time = time.time()
        self.confirmation_pending_command = None
        self.conversation_active = False

        self.audio_controller = AudioController(self)
        self.voice_listener = VoiceListener(self.audio_controller, self.wake_word_detected)
        self.command_handler = CommandHandler()
        self.gpt_client_proxy = GPTProxyClient()
        self.command_detector = CommandDetector()
        self.reminder_manager = ReminderManager(self.audio_controller)

        self.processing_sound_thread = None
        self.processing_stop_event = threading.Event()

        threading.Thread(target=self.reminder_manager._reminder_loop, daemon=True).start()

    def set_state(self, new_state):
        with self.state_lock:
            logger.info(f"Transition from [{self.state}] to new state [{new_state}]")
            self.state = new_state
            

    def start_processing_loop(self):
        def _loop():
            filepath = "processing_sound.mp3"
            try:
                data, samplerate = sf.read(filepath, dtype='float32')
                channels = data.shape[1] if len(data.shape) > 1 else 1

                self.audio_controller.is_playing = True
                self.processing_stop_event.clear()

                with sd.OutputStream(samplerate=samplerate, channels=channels) as stream:
                    while not self.processing_stop_event.is_set():
                        i = 0
                        while i < len(data):
                            if self.processing_stop_event.is_set():
                                break
                            end = i + 1024
                            stream.write(data[i:end])
                            i = end
                            self.last_interaction_time = time.time()

                        time.sleep(1) #wait before playing next sound
            except Exception as e:
                logger.error(f"Error playing processing sound: {e}")
            finally:
                self.audio_controller.is_playing = False

        self.processing_sound_thread = threading.Thread(target=_loop, daemon=True)
        self.processing_sound_thread.start()

    def stop_processing_loop(self):
        self.processing_stop_event.set()

    def text_to_ssml(self, text: str, rate: str = "108%", pitch: str = "+1st") -> str:
        import html
        escaped_text = html.escape(text)
        return f"<speak><prosody rate=\"{rate}\" pitch=\"{pitch}\">{escaped_text}</prosody></speak>"

    def check_idle(self):
        """ถ้าไม่มี interaction นานเกิน IDLE_TIMEOUT ให้กลับไป Idle Mode"""
        if self.conversation_active and (time.time() - self.last_interaction_time > IDLE_TIMEOUT):
            print("⌛ Conversation idle timeout. Going back to Wake Word mode.")
            self.conversation_active = False
        

    def run(self):
        logger.info("🚀 Assistant Started. Waiting for Wake Word...")

        while not self.should_exit:
            self.check_idle() 
            if not self.conversation_active:
                    self.set_state(AssistantState.IDLE)
            
            if self.state == AssistantState.IDLE:
                logger.info("⌛ Waiting for Wake Word...")
                self.wake_word_detected.wait()
                self.wake_word_detected.clear()
                self.conversation_active = True
                self.set_state(AssistantState.LISTENING)
                self.audio_controller.speak(self.text_to_ssml(HELLO_MSG), is_ssml=True)

            elif self.state == AssistantState.LISTENING:
                self.voice_listener.background_enabled = False
                with self.voice_listener.listening_lock:
                    user_voice = self.voice_listener.listen()
                self.voice_listener.background_enabled = True

                if not user_voice:
                    self.set_state(AssistantState.LISTENING)
                    continue

                logger.info(f"🗣️ User said: {user_voice}")
                self.last_interaction_time = time.time()

                command = self.command_detector.detect_command(user_voice)
                logger.debug(f"command_detector returns = {command}")
                if command:
                    if command['type'] == "home_assistant_command":
                        self.confirmation_pending_command = command
                        summarize_command = self.command_detector.summarize_command(command)
                        self.audio_controller.speak(self.text_to_ssml(summarize_command), is_ssml=True)                        
                        self.set_state(AssistantState.CONFIRMING_COMMAND)
                        continue
                    elif command['type'] == "reminder":
                        self.reminder_manager.add_reminder(command)
                        self.audio_controller.speak(self.text_to_ssml(text="บันทึกการแจ้งเตือนให้แล้ว"), is_ssml=True)
                        self.set_state(AssistantState.LISTENING)
                        continue
                    else:
                        self.audio_controller.speak(self.text_to_ssml("ไม่พบข้อมูลอุปกรณ์ "), is_ssml=True)
                        self.set_state(AssistantState.LISTENING)
                        continue

                self.start_processing_loop()
                logger.info(f"[ChatGPT] Sending text..")
                answer = self.gpt_client_proxy.ask(user_voice)
                logger.info(f"[ChatGPT] Response text: {answer}")
                self.stop_processing_loop()

                if not re.search(r"<speak>.*</speak>", answer, re.DOTALL):
                    answer = self.text_to_ssml(answer)

                self.audio_controller.speak(answer, is_ssml=True)
                self.set_state(AssistantState.LISTENING)

            elif self.state == AssistantState.CONFIRMING_COMMAND:
                self.voice_listener.background_enabled = False
                with self.voice_listener.listening_lock:
                    user_response = self.voice_listener.listen( skip_if_speaking=False,keywords_only=True,silence_timeout=300,post_padding_seconds=0.1)
                    print(f"user_response={user_response}")
                self.voice_listener.background_enabled = True

                if self.command_detector.is_confirmation(user_response):
                    self.command_handler.execute_command(self.confirmation_pending_command)                    
                    logger.info(f"executing command : {self.confirmation_pending_command}")
                    self.audio_controller.speak(self.text_to_ssml("ดำเนินการเรียบร้อยแล้ว"), is_ssml=True)
                    self.confirmation_pending_command = None
                    self.set_state(AssistantState.LISTENING)
                elif self.command_detector.is_cancellation(user_response):
                    self.audio_controller.speak(self.text_to_ssml("ยกเลิกคำสั่งแล้ว"), is_ssml=True)
                    self.confirmation_pending_command = None
                    self.set_state(AssistantState.LISTENING)
                else:
                    self.audio_controller.speak(self.text_to_ssml("ช่วยยืนยันหน่อยนะว่า ใช่ หรือ ไม่"), is_ssml=True)

                
                

        logger.info("👋 Program exiting... Goodbye!")
