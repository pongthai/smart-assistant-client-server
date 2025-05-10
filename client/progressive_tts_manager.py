import os
from gtts import gTTS
import pygame
import re
import uuid
import platform
import threading
import time
from queue import Queue, Empty
from mutagen.mp3 import MP3
from logger_config import get_logger
from latency_logger import LatencyLogger
from pythainlp.tokenize import sent_tokenize, word_tokenize

logger = get_logger(__name__)

class ProgressiveTTSManager:
    def __init__(self, assistant_manager):
        logger.info("ProgressiveTTSManager initialized")
        pygame.mixer.init()
        self.assistant_manager = assistant_manager
        self.chunk_queue = Queue()
        self.generating_done = False
        self.stop_flag = threading.Event()

    def clean_text_for_gtts(self, text):
        text = re.sub(r"(?<=\d)\.(?=\d)", "DOTPLACEHOLDER", text)
        text = re.sub(r"(?<=\w)\.(?=\w)", "DOTPLACEHOLDER", text)
        text = re.sub(r"[^\u0E00-\u0E7Fa-zA-Z0-9\s%:-]", "", text)
        text = text.replace("DOTPLACEHOLDER", ".")
        return re.sub(r"\s+", " ", text).strip()

    def thai_chunks(self, text, initial_limit=5, grow_rate=2):
        words = word_tokenize(text, engine="newmm")
        chunks = []
        start = 0
        limit = initial_limit

        while start < len(words):
            end = int(start + limit)
            chunk = ''.join(words[start:end])
            chunks.append(chunk)
            start = end
            limit *= grow_rate

        return chunks

    def generate_chunks(self):
        try:
            logger.debug("Enter generate_chunks")
            for chunk in self.chunks:
                if self.stop_flag.is_set():
                    break
                if not chunk.strip():
                    continue

                is_macos = platform.system() == "Darwin"
                temp_dir = "/tmp" if is_macos else "/dev/shm"
                filename = f"{temp_dir}/temp_{uuid.uuid4()}.mp3"

                cleaned_text = self.clean_text_for_gtts(chunk)
                if not cleaned_text:
                    logger.error("? Empty text chunk")
                    continue

                tts = gTTS(text=cleaned_text, lang="th")
                tts.save(filename)
                audio = MP3(filename)
                logger.debug(f"file={filename} saved, duration={audio.info.length:.2f}s")

                self.chunk_queue.put(filename)

            self.generating_done = True
            logger.info("Exit generate_chunks")

        except Exception as e:
            logger.error(f"? Error during chunk generation: {e}")

    def play_chunks(self):
        logger.info("? Start playing chunks")
        while True:
            if self.stop_flag.is_set():
                logger.info("? Stop flag received during playback")
                break

            try:
                filename = self.chunk_queue.get(timeout=1.0)
            except Empty:
                if self.generating_done:
                    break
                continue

            sound = pygame.mixer.Sound(filename)
            channel = sound.play()
            logger.debug(f"? Playing {filename}")

            while channel.get_busy():
                if self.stop_flag.is_set():
                    channel.stop()
                    logger.info("? Playback interrupted")
                    break
                self.assistant_manager.last_interaction_time = time.time()
                time.sleep(0.1)

            try:
                os.remove(filename)
            except:
                pass

    def speak(self, text):
        logger.info("Enter speak")
        self.tracker = LatencyLogger()
        self.tracker.mark("tts - enter speak")

        self.stop_flag.clear()
        self.chunks = self.thai_chunks(text, initial_limit=3, grow_rate=1.5)
        self.generating_done = False

        self.tracker.mark("tts - start generate_chunk")
        threading.Thread(target=self.generate_chunks, daemon=True).start()

        self.tracker.mark("tts - start play_chunks")
        self.play_chunks()
        self.tracker.mark("tts - end play_chunks")
        self.tracker.report()

    def stop(self):
        logger.info("? Stop requested")
        self.stop_flag.set()

