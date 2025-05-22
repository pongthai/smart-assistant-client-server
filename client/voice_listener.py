# voice_listener.py
import sounddevice as sd
import numpy as np
import threading
import time
import webrtcvad
import io
import scipy.io.wavfile as wav
import speech_recognition as sr
from  config import WAKE_WORDS, STOP_WORDS, EXIT_WORDS, CONFIRMATION_KEYWORDS, CANCEL_KEYWORDS, SAMPLE_RATE
import datetime
import wave
import os
import soundfile as sf

from logger_config import get_logger

logger = get_logger(__name__)

CHANNELS = 1
FRAME_DURATION = 40      # ms
VAD_MODE = 2
SILENCE_TIMEOUT_MS = 1200
MAX_RECORD_SECONDS = 15
VOICE_DEBOUNCE_FRAMES = 2
MARGIN_DB = 10

sd.default.device = (0, 0)

class VoiceListener:
    def __init__(self, audio_controller, wake_word_event):
        self.audio_controller = audio_controller
        self.recognizer = sr.Recognizer()
        self.volume_threshold_db = -50.0  # default fallback
        self.background_enabled = True
        self.listening_lock = threading.Lock()
        self.wake_word_event = wake_word_event
        self._stop_event = threading.Event()
        self._listener_thread = threading.Thread(target=self._background_listener, daemon=True)
        self._listener_thread.start()
        self.allowed_keywords = WAKE_WORDS+STOP_WORDS+EXIT_WORDS+CONFIRMATION_KEYWORDS+CANCEL_KEYWORDS

    def stop(self):
        self._stop_event.set()

    def calibrate_ambient_noise(self, duration=3.0):
        logger.info(f"Calibrating ambient noise for {duration:.1f} seconds...")
        samples = []

        def callback(indata, frames, time_info, status):
            samples.append(indata[:, 0].copy())

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=callback, dtype='float32'):
            sd.sleep(int(duration * 1000))

        all_audio = np.concatenate(samples)
        rms = np.sqrt(np.mean(all_audio ** 2)) + 1e-10
        ambient_db = 20 * np.log10(rms)
        self.volume_threshold_db = ambient_db + MARGIN_DB

        logger.info(f"Ambient noise: {ambient_db:.1f} dB, threshold: {self.volume_threshold_db:.1f} dB")

    def _background_listener(self):
        self.calibrate_ambient_noise()
        
        while not self._stop_event.is_set():
            if not self.background_enabled:
                time.sleep(0.2)
                continue

            with self.listening_lock:
                text = self.listen(skip_if_speaking=False,keywords_only=True,silence_timeout=300,post_padding_seconds=0.1)
                logger.debug(f"in background listener: text={text}")

            if not text:
                continue

            # ✅ Check for STOP command
            if any(cmd in text for cmd in STOP_WORDS):
                logger.info(f"🛑 Stop command detected: {text}")
                self.audio_controller.stop_audio()
                continue

            # ✅ Check for Wake Word
            if any(w in text for w in WAKE_WORDS):
                logger.info(f"🔔 Wake word detected: {text}")
                self.wake_word_event.set()

    def save_debug_audio(self, audio_np, sample_rate):
        try:
            now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debug_audio_{now}.wav"
            filepath = os.path.join(".", filename)

            audio_int16 = (audio_np * 32767).astype(np.int16)
            with wave.open(filepath, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(audio_int16.tobytes())

            logger.warning(f"💾 Saved debug audio to {filepath}")
        except Exception as e:
            logger.error(f"❌ Failed to save debug audio: {e}")

    def listen(self, skip_if_speaking=True, keywords_only=False,silence_timeout=SILENCE_TIMEOUT_MS, post_padding_seconds=0.3):
        if skip_if_speaking:
            while self.audio_controller.is_sound_playing:
                time.sleep(0.1)

        vad = webrtcvad.Vad(VAD_MODE)
        frame_len = int(SAMPLE_RATE * FRAME_DURATION / 1000)
        audio_buffer = []
        stop_event = threading.Event()

        consecutive_voice_frames = 0
        last_voice_time = time.time()
        recording_started = False

        POST_PADDING_SECONDS = post_padding_seconds
        post_padding_added = False

        def calculate_volume_db(chunk):
            rms = np.sqrt(np.mean(chunk ** 2)) + 1e-10
            return 20 * np.log10(rms)

        def callback(indata, frames, time_info, status):
            nonlocal last_voice_time, consecutive_voice_frames, recording_started, post_padding_added

            if skip_if_speaking and self.audio_controller.is_sound_playing:
                return

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

            if is_speech or volume_db > self.volume_threshold_db:
                recording_started = True
                last_voice_time = time.time()
                consecutive_voice_frames = min(consecutive_voice_frames + 1, 10)
                audio_buffer.append(audio_chunk)
            elif recording_started:
                consecutive_voice_frames = max(consecutive_voice_frames - 1, 0)
                audio_buffer.append(audio_chunk)
                if time.time() - last_voice_time > (SILENCE_TIMEOUT_MS / 1000.0):
                    if not post_padding_added:
                        logger.debug("🕒 Adding post-speech padding")
                        padding = np.zeros(int(SAMPLE_RATE * POST_PADDING_SECONDS), dtype=np.float32)
                        audio_buffer.append(padding)
                        post_padding_added = True
                    logger.debug("🔇 Silence detected — stopping InputStream")
                    stop_event.set()
                    raise sd.CallbackStop()
            else:
                consecutive_voice_frames = max(consecutive_voice_frames - 1, 0)

        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=callback, dtype='float32', blocksize=1024):
                logger.debug("🎧 InputStream opened — listening...")
                start = time.time()
                while not stop_event.is_set() and time.time() - start < MAX_RECORD_SECONDS:
                    sd.sleep(50)
        except sd.CallbackStop:
            pass
        except Exception as e:
            logger.error(f"❌ Error capturing input: {e}")
            return None

        if not audio_buffer:
            logger.warning("⚠️ No audio captured")
            return None

        try:
            audio_np = np.concatenate(audio_buffer)
        except Exception as e:
            logger.error(f"❌ Failed to concatenate audio: {e}")
            return None

        audio_int16 = (audio_np * 32767).astype(np.int16)

        #self.save_debug_audio(audio_np,SAMPLE_RATE)

        with io.BytesIO() as wav_io:
            wav.write(wav_io, SAMPLE_RATE, audio_int16)
            wav_io.seek(0)
            with sr.AudioFile(wav_io) as source:
                try:
                    audio = self.recognizer.record(source)
                    text = self.recognizer.recognize_google(audio, language="th-TH")
                    logger.debug(f"🗣️ Recognized: {text}")
                    text = text.strip().lower()
                    if keywords_only:
                        if not any(text.strip() == keyword for keyword in self.allowed_keywords):
                            logger.info(f"🛑 Ignored non-matching input: {text}")
                            return None
                    
                    return text
                except sr.UnknownValueError:
                    #logger.warning("🛑 Could not understand audio")
                    return None
                except sr.RequestError as e:
                    logger.error(f"🛑 Google API error: {e}")
                    return None
                except Exception as e:
                    logger.exception(f"🛑 Unexpected recognition error: {e}")
                    return None
