import sys
import os
import tempfile
import sounddevice as sd
import scipy.io.wavfile as wav

# เพิ่ม path ไปยัง voice_profile_manager.py ที่อยู่นอกโฟลเดอร์นี้
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from voice_profile_manager import VoiceProfileManager

SAMPLE_RATE = 16000
DURATION = 5  # วินาที

def record_audio(filename):
    print(f"🎙️ กำลังบันทึกเสียง... ({DURATION} วินาที)")
    audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="int16")
    sd.wait()
    wav.write(filename, SAMPLE_RATE, audio)
    print(f"✅ บันทึกเสร็จสิ้น: {filename}")

def main():
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
        tmp_path = tmpfile.name
        input("🔴 กด Enter เพื่อเริ่มบันทึกเสียงและระบุว่าใครพูด...")
        record_audio(tmp_path)

        vpm = VoiceProfileManager()
        speaker = vpm.identify_speaker(tmp_path)

        print("\n🧠 เสียงนี้เป็นของ:", speaker)

if __name__ == "__main__":
    main()
