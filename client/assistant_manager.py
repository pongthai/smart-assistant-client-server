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
    CONFIRMING = 2
    RESPONDING = 3

class AssistantManager:
    def __init__(self):
        logger.info("AssistantManager initialized")

        self.state = AssistantState.IDLE
        self.state_lock = threading.Lock()

        self.wake_word_detected = threading.Event()
        self.should_exit = False
        self.last_interaction_time = time.time()
        self.conversation_active = False

        self.audio_controller = AudioController(self)
        self.voice_listener = VoiceListener(self.audio_controller, self.wake_word_detected)
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
                self.last_interaction_time = time.time()
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

                self.start_processing_loop()
                response = self.gpt_client_proxy.ask(user_voice)
                logger.info(f"[ChatGPT] Response received: {response}")
                self.stop_processing_loop()

                
                action = response.get("action")
                action_type = action.get("type") if isinstance(action, dict) else None
                status = response.get("status",None)
                message = response.get("reply", None)   
                logger.debug(f" action_type: {action_type} ,  message: {message}, status: {status}")  

                if action_type == "home_assistant_command" or action_type == "reminder":     
                    logger.debug("Enter command for Home Assistant and Creating reminder")             
                    self.audio_controller.speak(self.text_to_ssml(message), is_ssml=True)                
                    self.set_state(AssistantState.CONFIRMING)
                    continue               
                else:
                    if not re.search(r"<speak>.*</speak>", message, re.DOTALL):
                        message = self.text_to_ssml(message)
                    
                    self.audio_controller.speak(message, is_ssml=True)
                    self.set_state(AssistantState.LISTENING)
                    continue
            

            elif self.state == AssistantState.CONFIRMING:
                self.voice_listener.background_enabled = False
                with self.voice_listener.listening_lock:
                    user_voice = self.voice_listener.listen()
                self.voice_listener.background_enabled = True
                if not user_voice:
                    self.set_state(AssistantState.LISTENING)
                    continue

                logger.info(f"🗣️ User said (confirmation): {user_voice}")
                self.last_interaction_time = time.time()

                response = self.gpt_client_proxy.ask(user_voice)
                logger.info(f"[ChatGPT] Response received: {response}")

                status = response.get("status",None)
                message = response.get("reply", None)  
         
                self.audio_controller.speak(self.text_to_ssml(message), is_ssml=True)
                if status == "confirmed" or status == "cancelled":
                    self.set_state(AssistantState.LISTENING)                            
               

        logger.info("👋 Program exiting... Goodbye!")
