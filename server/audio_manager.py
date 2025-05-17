# assistant/audio_manager.py

import pygame
import threading
import time
import os
import uuid
import re
from gtts import gTTS
from progressive_tts_manager import ProgressiveTTSManager
from logger_config import get_logger
from PIL import Image, ImageSequence
from config import ENABLE_AVATAR_DISPLAY


logger = get_logger(__name__)

class AssistantAvatarPygame:
    def __init__(self, static_img_path, gif_path):
        pygame.init()

        self.static_img = pygame.image.load(static_img_path)
        self.screen = pygame.display.set_mode(self.static_img.get_size())
        pygame.display.set_caption("PingPing Avatar")

        gif = Image.open(gif_path)
        self.gif_frames = [pygame.image.fromstring(frame.convert("RGB").tobytes(), frame.size, "RGB")
                           for frame in ImageSequence.Iterator(gif)]

        self.gif_index = 0
        self.running = True
        self.is_animating = False

        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _play_static(self):
        self.screen.blit(self.static_img, (0, 0))
        pygame.display.flip()

    def _play_gif(self):
        frame = self.gif_frames[self.gif_index]
        self.screen.blit(frame, (0, 0))
        pygame.display.flip()
        self.gif_index = (self.gif_index + 1) % len(self.gif_frames)

    def _run_loop(self):
        clock = pygame.time.Clock()
        self._play_static()
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            if self.is_animating:
                self._play_gif()
            else:
                time.sleep(0.05)
            clock.tick(4)

        pygame.quit()

    def start_animation(self):
        self.is_animating = True

    def stop_animation(self):
        self.is_animating = False
        self._play_static()

class AudioManager:
    def __init__(self,assistant_manager):
        logger.info("AudioManager initialized")
        pygame.mixer.init()               

        self.assistant_manager = assistant_manager
        self.tts_manager = ProgressiveTTSManager(assistant_manager)

        if ENABLE_AVATAR_DISPLAY:
            self.avatar = AssistantAvatarPygame("pingping_mouth_closed.png", "pingping_animation.gif")
        else:
            self.avatar = None
        

        self.current_audio_file = None
        self.current_sound_channel = None
        self.is_sound_playing = False

    def clean_text_for_gtts(self,text):
        # 1. รักษาจุด (.) ระหว่างตัวเลข เช่น 2.14
        text = re.sub(r"(?<=\d)\.(?=\d)", "DOTPLACEHOLDER", text)
        
        # 2. รักษาจุด (.) ติดกับตัวอักษร เช่น U.S.A.
        text = re.sub(r"(?<=\w)\.(?=\w)", "DOTPLACEHOLDER", text)
        
        # 3. กรองเฉพาะ ก-ฮ, a-z, A-Z, 0-9, เว้นวรรค, เครื่องหมาย %, :
        text = re.sub(r"[^ก-๙a-zA-Z0-9\s%:-]", "", text)
        # 4. คืน DOT กลับ
        text = text.replace("DOTPLACEHOLDER", ".")

        # 5. ลบช่องว่างซ้ำ
        text = re.sub(r"\s+", " ", text).strip()

        return text
    
    def speak(self,text):
        self.stop_audio()
        self.tts_manager.speak(text)
   
    def speak_org(self, text):
        try:
            filename = f"temp_{uuid.uuid4()}.mp3"
            cleaned_text = self.clean_text_for_gtts(text)
            print("cleaned text =",cleaned_text)
            tts = gTTS(text=cleaned_text, lang="th")
            tts.save(filename)

            self.stop_audio()

            self.current_audio_file = filename
            threading.Thread(target=self.play_audio, args=(filename,), daemon=True).start()

        except Exception as e:
            print(f"❌ TTS Error: {e}")

    def play_audio(self, filename):
        try:
            self.is_sound_playing = True
            if self.avatar:
                self.avatar.start_animation()

            sound = pygame.mixer.Sound(filename)
            self.current_sound_channel = sound.play()           

            def monitor_playback():
                while self.current_sound_channel.get_busy():
                    self.assistant_manager.last_interaction_time = time.time()
                    pygame.time.wait(100)
                print("🎵 Sound playback finished.")
                self.is_sound_playing = False
                if self.avatar:
                    self.avatar.stop_animation()
                if self.current_audio_file and os.path.exists(self.current_audio_file):
                    try:
                        os.remove(self.current_audio_file)
                        logger.info(f"\U0001F9F9 Removed audio file: {self.current_audio_file}")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not delete audio file: {e}")
                    self.current_audio_file = None        

            threading.Thread(target=monitor_playback, daemon=True).start()

        except Exception as e:
            print(f"❌ Error playing sound: {e}")

        finally:
            if os.path.exists(filename):
                try:
                    os.remove(filename)
                except:
                    pass
    def stop_audio(self):
        self.tts_manager.stop()
        self.is_sound_playing = False

    def stop_audio_org(self):
        if self.current_sound_channel and self.current_sound_channel.get_busy():
            print("🛑 Stopping audio...")
            self.current_sound_channel.stop()

        if self.current_audio_file and os.path.exists(self.current_audio_file):
            try:
                os.remove(self.current_audio_file)
            except:
                pass

        self.current_audio_file = None
        self.is_sound_playing = False