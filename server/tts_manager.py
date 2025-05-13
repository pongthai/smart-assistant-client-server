# tts_manager.py
from google.cloud import texttospeech
import uuid
import os
import platform

class TTSManager:
    def __init__(self):

        system = platform.system()
        if system == "Linux" and os.path.exists("/dev/shm"):
            self.output_dir = "/dev/shm"  # บน Raspberry Pi หรือ Linux ทั่วไป
        else:
            self.output_dir = "."  # macOS หรือ fallback → เก็บไว้ใน current folder    

    def synthesize(self, text: str, is_ssml=False) -> str:
        client = texttospeech.TextToSpeechClient()

        synthesis_input = (
            texttospeech.SynthesisInput(ssml=text)
            if is_ssml else
            texttospeech.SynthesisInput(text=text)
        )

        voice = texttospeech.VoiceSelectionParams(
            language_code="th-TH",
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.05,
            pitch=1.5
        )

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        filename = os.path.join(self.output_dir, f"tts_{uuid.uuid4()}.mp3")
        with open(filename, "wb") as out:
            out.write(response.audio_content)

        return filename  # return path to mp3