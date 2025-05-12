import sounddevice as sd
import scipy.io.wavfile as wav
import tempfile
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from voice_profile_manager import VoiceProfileManager

SAMPLE_RATE = 16000
DURATION = 6  # วินาที

def record_audio(filename):
    print(f"🎙️ กำลังบันทึกเสียง... ({DURATION} วินาที)")
    audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="int16")
    sd.wait()
    wav.write(filename, SAMPLE_RATE, audio)
    print(f"✅ บันทึกเสร็จสิ้น: {filename}")

def main():
    name = input("👤 ป้อนชื่อผู้พูด (เช่น arth, metta): ").strip().lower()
    if not name:
        print("❌ กรุณาใส่ชื่อก่อน")
        return

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
        tmp_path = tmpfile.name
        input("🔴 กด Enter เพื่อเริ่มบันทึกเสียง...")
        record_audio(tmp_path)

        vpm = VoiceProfileManager()
        vpm.train_profile(name, tmp_path)

if __name__ == "__main__":
    main()