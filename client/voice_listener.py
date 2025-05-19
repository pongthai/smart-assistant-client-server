# assistant/voice_listener.py
import threading
import time
import os
import sys
import numpy as np
import webrtcvad
import sounddevice as sd
import scipy.io.wavfile as wav
import io
import speech_recognition as sr

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import WAKE_WORDS, COMMAND_WORDS
from logger_config import get_logger

logger = get_logger(__name__)

SAMPLE_RATE = 16000
CHANNELS = 1
FRAME_DURATION = 30      # ms
VAD_MODE = 2
SILENCE_TIMEOUT_MS = 1200
MAX_RECORD_SECONDS = 15
VOICE_DEBOUNCE_FRAMES = 2
MARGIN_DB = 10

class VoiceListener:
    def __init__(self, assistant_manager):
        logger.info("VoiceListener initialized")
        self.assistant_manager = assistant_manager
        self.recognizer = sr.Recognizer()
        self.volume_threshold_db = self.calibrate_ambient_noise()
        threading.Thread(target=self.background_listener, daemon=True).start()

    def calibrate_ambient_noise(self, duration=3.0):
        logger.info(f"🔧 Calibrating ambient noise for {duration:.1f} sec...")
        samples = []

        def callback(indata, frames, time_info, status):
            audio_chunk = indata[:, 0].copy()
            samples.append(audio_chunk)

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=callback, dtype='float32'):
            sd.sleep(int(duration * 1000))

        all_audio = np.concatenate(samples)
        rms = np.sqrt(np.mean(all_audio**2)) + 1e-10
        ambient_db = 20 * np.log10(rms)
        threshold = ambient_db + MARGIN_DB

        logger.info(f"🟡 Ambient noise: {ambient_db:.1f} dB → threshold: {threshold:.1f} dB")
        return threshold

    def background_listener(self):
        while True:
            try:
                if not self.assistant_manager.conversation_active:
                    text = self.listen()
                    if not text:
                        continue
                    logger.info(f"🗣️ Detected (Idle): {text}")
                    if any(wake_word in text for wake_word in WAKE_WORDS):
                        logger.info("✅ Wake Word Detected!")
                        self.assistant_manager.wake_word_detected.set()

                    if self.detect_command(text, "exit"):
                        logger.info("👋 Exit command detected")
                        self.assistant_manager.should_exit = True
                        break
                else:
                    text = self.listen()
                    if not text:
                        continue

                    if self.detect_command(text, "stop"):
                        logger.info("🛑 Stop command detected")
                        self.assistant_manager.audio_manager.stop_audio()

                    if self.detect_command(text, "exit"):
                        logger.info("👋 Exit command detected")
                        self.assistant_manager.should_exit = True
                        break

            except Exception as e:
                logger.error(f"❌ Error in background_listener: {e}")
                time.sleep(0.5)

    def listen(self):
        vad = webrtcvad.Vad(VAD_MODE)
        frame_len = int(SAMPLE_RATE * FRAME_DURATION / 1000)
        audio_buffer = []
        stop_event = threading.Event()

        consecutive_voice_frames = 0
        last_voice_time = time.time()

        def calculate_volume_db(chunk):
            rms = np.sqrt(np.mean(chunk**2)) + 1e-10
            return 20 * np.log10(rms)

        def callback(indata, frames, time_info, status):
            nonlocal last_voice_time, consecutive_voice_frames

            audio_chunk = indata[:, 0].copy()
            audio_int16 = (audio_chunk * 32767).astype(np.int16)
            volume_db = calculate_volume_db(audio_chunk)

            is_speech = False
            if len(audio_int16) >= frame_len:
                frame = audio_int16[:frame_len]
                try:
                    is_speech = vad.is_speech(frame.tobytes(), SAMPLE_RATE)
                except:
                    pass

            is_speech = is_speech or (volume_db > self.volume_threshold_db)
            audio_buffer.append(audio_chunk)
            # Decay debounce
            if is_speech:
                consecutive_voice_frames = min(consecutive_voice_frames + 1, 10)
                if consecutive_voice_frames >= VOICE_DEBOUNCE_FRAMES:
                    last_voice_time = time.time()
            else:
                consecutive_voice_frames = max(consecutive_voice_frames - 1, 0)
                if time.time() - last_voice_time > (SILENCE_TIMEOUT_MS / 1000.0):
                    stop_event.set()
                    raise sd.CallbackStop()

        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=callback, dtype='float32'):
                start = time.time()
                while not stop_event.is_set() and time.time() - start < MAX_RECORD_SECONDS:
                    sd.sleep(50)
        except sd.CallbackStop:
            pass

        valid_chunks = [chunk for chunk in audio_buffer if len(chunk) > 0]
        if len(valid_chunks) < 3:
            logger.warning("⚠️ No valid audio captured")
            return None
        audio_np = np.concatenate(valid_chunks)
        audio_int16 = (audio_np * 32767).astype(np.int16)

        with io.BytesIO() as wav_io:
            wav.write(wav_io, SAMPLE_RATE, audio_int16)
            wav_io.seek(0)
            with sr.AudioFile(wav_io) as source:
                audio = self.recognizer.record(source)
            try:
                text = self.recognizer.recognize_google(audio, language="th-TH")
                return text.strip().lower()
            except Exception as e:
                #logger.error(f"Error speech recog...{e}")
                return None


    def listen_bak(self):
        vad = webrtcvad.Vad(VAD_MODE)
        frame_len = int(SAMPLE_RATE * FRAME_DURATION / 1000)
        audio_buffer = []
        stop_event = threading.Event()

        consecutive_voice_frames = 0
        last_voice_time = time.time()

        def calculate_volume_db(chunk):
            rms = np.sqrt(np.mean(chunk**2)) + 1e-10
            return 20 * np.log10(rms)

        def callback(indata, frames, time_info, status):
            nonlocal last_voice_time, consecutive_voice_frames

            audio_chunk = indata[:, 0].copy()
            audio_int16 = (audio_chunk * 32767).astype(np.int16)
            volume_db = calculate_volume_db(audio_chunk)

            is_speech = False
            if len(audio_int16) >= frame_len:
                frame = audio_int16[:frame_len]
                try:
                    is_speech = vad.is_speech(frame.tobytes(), SAMPLE_RATE)
                except:
                    pass

            is_speech = is_speech or (volume_db > self.volume_threshold_db)
            audio_buffer.append(audio_chunk)

            #logger.debug(f"🔊 Volume: {volume_db:.1f} dB | Speech: {is_speech} | VoiceFrames: {consecutive_voice_frames}")

            if is_speech:
                consecutive_voice_frames += 1
                if consecutive_voice_frames >= VOICE_DEBOUNCE_FRAMES:
                    last_voice_time = time.time()
            else:
                consecutive_voice_frames = 0
                if time.time() - last_voice_time > (SILENCE_TIMEOUT_MS / 1000.0):
                    stop_event.set()
                    raise sd.CallbackStop()

        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=callback, dtype='float32'):
                start = time.time()
                while not stop_event.is_set() and time.time() - start < MAX_RECORD_SECONDS:
                    sd.sleep(50)
        except sd.CallbackStop:
            pass

        if not audio_buffer:
            logger.warning("⚠️ No audio captured")
            return None

        audio_np = np.concatenate(audio_buffer)
        audio_int16 = (audio_np * 32767).astype(np.int16)

        recognizer = sr.Recognizer()
        with io.BytesIO() as wav_io:
            wav.write(wav_io, SAMPLE_RATE, audio_int16)
            wav_io.seek(0)
            with sr.AudioFile(wav_io) as source:
                audio = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio, language="th-TH")
                #logger.info(f"🧠 Recognized: {text}")
                return text.strip().lower()
            except Exception as e:
                #logger.warning(f"❌ STT failed: {e}")
                return None

    def detect_command(self, text, command_type):
        keywords = COMMAND_WORDS.get(command_type, [])
        return any(keyword in text for keyword in keywords)

    def listen_old(self, timeout=3, phrase_time_limit=15):
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='float32') as stream:
            audio_data = self.recognizer.record(stream, duration=phrase_time_limit)
            try:
                text = self.recognizer.recognize_google(audio_data, language="th-TH")
                return text.strip()
            except (sr.UnknownValueError, sr.WaitTimeoutError):
                return None
            except sr.RequestError as e:
                logger.error(f"❌ Speech error: {e}")
                return None
