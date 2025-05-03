# assistant/voice_listener.py

import threading
import time
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import speech_recognition as sr
from config import WAKE_WORDS
from config import COMMAND_WORDS
from logger_config import get_logger

logger = get_logger(__name__)



class VoiceListener:
    def __init__(self, assistant_manager):
        logger.info("VoiceListener initialized")
        self.assistant_manager = assistant_manager
        self.recognizer = sr.Recognizer()

        # 🔥 แยก 2 ไมค์
        self.background_mic = sr.Microphone()
        self.listen_mic = sr.Microphone()
        self.calibrate_energy_threshold()

        # Start background listener thread
        threading.Thread(target=self.background_listener, daemon=True).start()
    
    def calibrate_energy_threshold(self):
        logger.info("🔧 Calibrating ambient noise... Please stay quiet (3 sec)")
        with self.listen_mic as source:
            self.recognizer.dynamic_energy_threshold = False  # ✅ use fixed threshold
            self.recognizer.adjust_for_ambient_noise(source, duration=3)

        logger.info(f"✅ Energy threshold set to: {self.recognizer.energy_threshold}")

    def background_listener(self):
        with self.background_mic as source:
            #self.recognizer.adjust_for_ambient_noise(source)
            while True:
                try:
                    if not self.assistant_manager.conversation_active:
                        # 📢 Idle mode: Listen for Wake Word
                        #logger.info("👂 (Idle) Listening for Wake Word...")
                        audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=3)
                        text = self.recognizer.recognize_google(audio, language="th-TH").lower()
                        logger.info(f"🗣️ Detected (Idle): {text}")
                        if any(wake_word in text for wake_word in WAKE_WORDS):
                            logger.info("✅ Wake Word Detected!")
                            self.assistant_manager.wake_word_detected.set()
                        
                        if self.detect_command(text, "exit"):
                            logger.info("👋 Exit command detected")
                            self.assistant_manager.should_exit = True
                            break

                    else:
                        # 🧠 Conversation mode: Listen for Commands
                        #print("👂 Listening for Commands...")
                        audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=3)
                        text = self.recognizer.recognize_google(audio, language="th-TH").lower()
                        #print(f"🗣️ Detected (command): {text}")
                        
                        # Check command
                        if self.detect_command(text, "stop"):
                            logger.info("🛑 Stop command detected")
                            self.assistant_manager.audio_manager.stop_audio()

                        if self.detect_command(text, "exit"):
                            logger.info("👋 Exit command detected")
                            self.assistant_manager.should_exit = True
                            break

                except (sr.UnknownValueError, sr.WaitTimeoutError):
                    time.sleep(0.1)
                except sr.RequestError as e:
                    logger.error(f"❌ Speech Recognition Error: {e}")
                    time.sleep(1)

    def detect_command(self, text, command_type):
        keywords = COMMAND_WORDS.get(command_type, [])
        return any(keyword in text for keyword in keywords)

    def listen(self, timeout=5, phrase_time_limit=15):
        with self.listen_mic as source:
            #self.recognizer.adjust_for_ambient_noise(source, duration=0.7)
            self.recognizer.pause_threshold = 1

            try:
                #logger.info("🎙️ Listening for question...")
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                text = self.recognizer.recognize_google(audio, language="th-TH")
                return text.strip()
            except (sr.UnknownValueError, sr.WaitTimeoutError):
                return None
            except sr.RequestError as e:
                logger.error(f"❌ Speech error: {e}")
                return None