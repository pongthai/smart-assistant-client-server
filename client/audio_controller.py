# audio_controller.py
import sounddevice as sd
import soundfile as sf
import threading
import os
import uuid
import requests
import scipy.signal
import time

from avatar_display import AssistantAvatarPygame

from config import TEMP_AUDIO_PATH, TTS_SERVER_ENDPOINT, SAMPLE_RATE, AVATAR_SCALE, AVATAR_STATIC, AVATAR_ANIMATION
from logger_config import get_logger

sd.default.device = (0, 0)

logger = get_logger(__name__)


class AudioController:
    def __init__(self, assistant_manager):
        self.assistant_manager = assistant_manager
        self.current_audio_file = None
        self.is_sound_playing = False
        self.stop_flag = threading.Event()
        self.avatar = AssistantAvatarPygame(AVATAR_STATIC, AVATAR_ANIMATION, scale=AVATAR_SCALE)

    def cleanup_audio_file(self,file_path):
        def worker():
            try:
                os.remove(file_path)
                logger.info(f"🗑️ Removed temp file: {file_path}")
            except Exception as e:
                logger.error(f"❌ Failed to remove file {file_path}: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def is_speaking(self):
        """Check if currently speaking"""
        return self.is_playing and not self.stop_flag.is_set()
        
    def stop_audio(self):
        self.stop_flag.set()
        sd.stop()

        if self.current_audio_file and os.path.exists(self.current_audio_file):
   
            self.cleanup_audio_file(self.current_audio_file)   
            self.current_audio_file = None

        self.is_playing = False
        if self.avatar:
                self.avatar.stop_animation()

    def play_audio(self, filepath):
        def _play():
            try:
                data, samplerate = sf.read(filepath, dtype='float32')
                channels = data.shape[1] if len(data.shape) > 1 else 1

                # 🎯 RESAMPLE to 48000 Hz (commonly supported)
         
                if samplerate != SAMPLE_RATE:
                    num_samples = int(len(data) * SAMPLE_RATE / samplerate)
                    data = scipy.signal.resample(data, num_samples)
                    samplerate = SAMPLE_RATE                   

                self.is_sound_playing = True
                self.stop_flag.clear()

                if self.avatar:
                    self.avatar.start_animation()

                with sd.OutputStream(device=None, samplerate=samplerate, channels=channels) as stream:
                    blocksize = 1024
                    i = 0
                    while i < len(data):
                        if self.stop_flag.is_set():
                            break
                        end = i + blocksize
                        stream.write(data[i:end])
                        i = end
                        self.assistant_manager.last_interaction_time = time.time()

            except Exception as e:
                logger.error(f"❌ Error during playback: {e}")

            finally:
                self.is_sound_playing = False
                logger.debug("is_sound_playing is set to False")
                if self.avatar:
                    self.avatar.stop_animation()

                # 🔥 Clean up audio file if it's a temporary one
                if self.current_audio_file and os.path.exists(self.current_audio_file):
                    if TEMP_AUDIO_PATH in self.current_audio_file or "tts_" in os.path.basename(self.current_audio_file):
                        self.cleanup_audio_file(self.current_audio_file)
                    self.current_audio_file = None

        threading.Thread(target=_play, daemon=True).start()

    def save_and_play(self, audio_content, ext=".mp3"):
        filename = os.path.join(TEMP_AUDIO_PATH, f"tts_{uuid.uuid4()}{ext}")
        try:
            with open(filename, "wb") as f:
                f.write(audio_content)
            self.current_audio_file = filename
            self.play_audio(filename)
        except Exception as e:
            logger.error(f"❌ Failed to save audio file: {e}")

    def speak(self, text: str, is_ssml: bool = False):
        """
        ติดต่อ TTS server และเล่นเสียงจากข้อความ
        """
        self.stop_audio()

        try:
            response = requests.post(
                TTS_SERVER_ENDPOINT,
                json={"text": text, "is_ssml": is_ssml},
                timeout=15
            )
            response.raise_for_status()
            if response.headers.get("Content-Type") == "audio/mpeg":
                self.save_and_play(response.content)
            else:
                logger.error(f"❌ Invalid TTS content-type: {response.headers.get('Content-Type')}")
        except Exception as e:
            logger.error(f"❌ Failed to fetch TTS audio: {e}")

