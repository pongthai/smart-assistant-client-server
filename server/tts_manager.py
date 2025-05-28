# tts_manager.py
from google.cloud import texttospeech
import uuid
import os
import platform
import html
import re
from .usage_tracker_instance import usage_tracker
from config import GOOGLE_CLOUD_CREDENTIALS_PATH

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_CLOUD_CREDENTIALS_PATH

 
class TTSManager:
    def __init__(self):

        system = platform.system()
        if system == "Linux" and os.path.exists("/dev/shm"):
            self.output_dir = "/dev/shm"  # บน Raspberry Pi หรือ Linux ทั่วไป
        else:
            self.output_dir = "."  # macOS หรือ fallback → เก็บไว้ใน current folder    

    def normalize_ssml_for_neural2(self,text: str) -> str:
        """
        สำหรับ Google TTS Neural2:
        แยก <break> ออกจาก <prosody> เพื่อป้องกัน SSML invalid
        """
        # 1. ค้นหา <prosody ...>...</prosody>
        pattern = r"(<prosody[^>]*>)(.*?)(</prosody>)"
        matches = re.findall(pattern, text, flags=re.DOTALL)

        for full_open, inner_text, full_close in matches:
            # 2. แยก inner_text ด้วย <break .../> ออกมาเป็นหลาย block
            parts = re.split(r'(<break[^/>]*/?>)', inner_text)

            rebuilt = []
            for part in parts:
                if part.strip().startswith("<break"):
                    rebuilt.append(part)
                else:
                    rebuilt.append(f"{full_open}{part.strip()}{full_close}")

            combined = ''.join(rebuilt)
            original = f"{full_open}{inner_text}{full_close}"
            text = text.replace(original, combined)

        return text
    def markdown_to_ssml(self,text: str) -> str:
        """
        แปลง markdown เช่น **bold** เป็น SSML <emphasis> เพื่อให้ TTS พูดด้วยน้ำเสียงเน้น
        """
        # แปลง **bold**
        text = re.sub(r"\*\*(.*?)\*\*", r'<emphasis level="moderate">\1</emphasis>', text)

        # แปลง *italic* หรือ _italic_
        text = re.sub(r"(?<!\*)\*(.*?)\*(?!\*)", r'<emphasis level="reduced">\1</emphasis>', text)
        text = re.sub(r"_(.*?)_", r'<emphasis level="reduced">\1</emphasis>', text)

        # ล้าง strike-through หรืออื่น ๆ ที่ไม่ใช้
        text = re.sub(r"~~(.*?)~~", r"\1", text)
        
        return text.strip()

    def sanitize_ssml_text(self,ssml: str) -> str:
        def escape_inside_tags(match):
            inner_text = match.group(1)
            return f">{html.escape(inner_text)}<"

        # Escapeเฉพาะเนื้อหาที่อยู่ระหว่าง >...< ของแต่ละ tag
        sanitized = re.sub(r'>([^<]+)<', escape_inside_tags, ssml)
        
        return sanitized

    def prepare_ssml_for_google_tts(self,text) -> str:
        """
        Sanitize and wrap text into valid SSML for Google Cloud TTS.
        - Removes emoji
        - Escapes unsafe HTML
        - Restores only safe SSML tags
        - Wraps with <speak><s>...</s></speak>
        """
        # ✅ 1. Force to string safely
        try:
            text = str(text)
        except Exception as e:
            print(f"[SSML] ❌ Cannot convert to string: {e}")
            return "<speak><s></s></speak>"

        # ✅ 2. Remove emoji and invalid characters
        emoji_pattern = re.compile(
            "[" +
            u"\U0001F600-\U0001F64F" +
            u"\U0001F300-\U0001F5FF" +
            u"\U0001F680-\U0001F6FF" +
            u"\U0001F1E0-\U0001F1FF" +
            u"\U00002500-\U00002BEF" +
            u"\U00002702-\U000027B0" +
            u"\U000024C2-\U0001F251" +
            "]+", flags=re.UNICODE)
        text = emoji_pattern.sub('', text)

        # ✅ 3. Escape everything
        text = html.escape(text)

        # ✅ 4. Restore all allowed SSML tags (open/close/self-closing)
        allowed_tags = ['speak', 's', 'p', 'break', 'emphasis', 'prosody', 'say-as']
        text = re.sub(r"&lt;(/?\w+)([^&]*)&gt;", r"<\1\2>", text)  # universal tag restorer

        for tag in allowed_tags:
            text = re.sub(f"&lt;/{tag}&gt;", f"</{tag}>", text)

        # ✅ 5. Ensure <speak> wrapper
        if not re.search(r"<speak>.*</speak>", text, re.DOTALL):
            text = f"<speak>{text}</speak>"

        # ✅ 6. Ensure at least one <s> tag inside
        if "<s>" not in text:
            text = text.replace("<speak>", "<speak><s>").replace("</speak>", "</s></speak>")

        return text

    def synthesize(self, text: str, is_ssml=False) -> str:
        client = texttospeech.TextToSpeechClient()

        if is_ssml:                 
            safe_ssml = self.sanitize_ssml_text(text)
            safe_ssml = self.markdown_to_ssml(safe_ssml)            
            # safe_ssml = self.normalize_ssml_for_neural2(safe_ssml)
            synthesis_input = texttospeech.SynthesisInput(ssml=safe_ssml)
        else:
            synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # synthesis_input = (
        #     texttospeech.SynthesisInput(ssml=text)
        #     if is_ssml else
        #     texttospeech.SynthesisInput(text=text)
        # )

        voice = texttospeech.VoiceSelectionParams(
            language_code="th-TH",
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )
        audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=0.75,
                pitch=1.0
            )        

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        filename = os.path.join(self.output_dir, f"tts_{uuid.uuid4()}.mp3")
        with open(filename, "wb") as out:
            out.write(response.audio_content)
        
        #log tts usage
        usage_tracker.log_tts_usage(len(text), is_ssml=is_ssml)

        return filename  # return path to mp3