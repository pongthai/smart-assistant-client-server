# assistant/audio_manager.py

import pygame
import threading
import time
import os
import requests
import platform
import uuid
import re
import queue
from gtts import gTTS
from progressive_tts_manager import ProgressiveTTSManager
from google.cloud import texttospeech
from config import GOOGLE_CLOUD_CREDENTIALS_PATH, TTS_SERVER_ENDPOINT, ENABLE_AVATAR_DISPLAY
from PIL import Image, ImageSequence


from logger_config import get_logger

logger = get_logger(__name__)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_CLOUD_CREDENTIALS_PATH



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
        self.command_queue = queue.Queue()

    def run(self):
        self._run_loop()

    def _play_static(self):
        self.screen.blit(self.static_img, (0, 0))
        try:
            pygame.display.flip()
        except pygame.error as e:
            logger.error(f"❌ pygame.flip() error (static): {e}")

    def _play_gif(self):
        frame = self.gif_frames[self.gif_index]
        self.screen.blit(frame, (0, 0))
        try:
            pygame.display.flip()
        except pygame.error as e:
            logger.error(f"❌ pygame.flip() error (gif): {e}")
        self.gif_index = (self.gif_index + 1) % len(self.gif_frames)

    def _run_loop(self):
        clock = pygame.time.Clock()
        self._play_static()
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            while not self.command_queue.empty():
                cmd = self.command_queue.get()
                if cmd == "animate":
                    self.is_animating = True
                elif cmd == "static":
                    self.is_animating = False
                    self._play_static()

            if self.is_animating:
                self._play_gif()
            else:
                time.sleep(0.05)
            clock.tick(4)

        pygame.quit()

    def start_animation(self):
        self.command_queue.put("animate")

    def stop_animation(self):
        self.command_queue.put("static")


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
    
    def get_temp_audio_path(self):

        system = platform.system()
        if system == "Linux" and os.path.exists("/dev/shm"):
            return "/dev/shm"  # บน Raspberry Pi หรือ Linux ทั่วไป
        else:
            return "."  # macOS หรือ fallback → เก็บไว้ใน current folder
    

    def speak_from_server(self, text,is_ssml=False):

        self.stop_audio()

        try:
            response = requests.post(
                    TTS_SERVER_ENDPOINT, 
                    json={
                        "text": text, 
                        "is_ssml":is_ssml}
                    )
            if response.status_code == 200 and response.headers.get("Content-Type") == "audio/mpeg":
                base_path = self.get_temp_audio_path()
                filename = os.path.join(base_path, f"tts_{uuid.uuid4()}.mp3")
                #temp_filename = f"/tmp/tts_{uuid.uuid4()}.mp3"
                with open(filename, "wb") as f:
                    f.write(response.content)
                
                self.stop_audio()
                self.current_audio_file = filename
                threading.Thread(target=self.play_audio, args=(filename,), daemon=True).start()

            else:
                print(f"? Server TTS error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Error during server TTS playback: {e}")


    def speak(self, text_or_ssml, is_ssml=False):
        try:            

            client = texttospeech.TextToSpeechClient()
            synthesis_input = texttospeech.SynthesisInput(ssml=text_or_ssml) if is_ssml else texttospeech.SynthesisInput(text=text_or_ssml)

            voice = texttospeech.VoiceSelectionParams(
                language_code="th-TH",
                ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=0.8,
                pitch=1.2
            )

            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            # 🔽 จุดนี้ใช้ path ตามระบบ
            base_path = self.get_temp_audio_path()
            filename = os.path.join(base_path, f"tts_{uuid.uuid4()}.mp3")

            with open(filename, "wb") as out:
                out.write(response.audio_content)

            self.stop_audio()
            self.current_audio_file = filename
            threading.Thread(target=self.play_audio, args=(filename,), daemon=True).start()

        except Exception as e:
            print(f"❌ Google TTS Error: {e}")
    
    def speak_tts_manager(self,text):
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

                # ✅ Auto-clean: ลบไฟล์หลังเล่นจบ
                if self.current_audio_file and os.path.exists(self.current_audio_file):
                    try:
                        os.remove(self.current_audio_file)
                        print(f"🧹 Removed audio file: {self.current_audio_file}")
                    except Exception as e:
                        print(f"⚠️ Could not delete audio file: {e}")
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
        # self.tts_manager.stop()
        # self.is_sound_playing = False

        if self.current_sound_channel and self.current_sound_channel.get_busy():
            self.current_sound_channel.stop()

        if self.current_audio_file and os.path.exists(self.current_audio_file):
            try:
                os.remove(self.current_audio_file)
                print(f"🧹 Removed audio file: {self.current_audio_file}")
            except Exception as e:
                print(f"⚠️ Could not delete audio file: {e}")
            self.current_audio_file = None
            

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
