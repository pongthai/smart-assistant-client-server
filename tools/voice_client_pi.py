import sounddevice as sd
import scipy.io.wavfile as wav
import requests
import tempfile
import os

SAMPLE_RATE = 16000
DURATION = 5  # วินาที
SERVER_URL = "http://<MAC-IP>:8000"  # เปลี่ยน <MAC-IP> เป็น IP จริงของ Mac Mini

def record_audio(path):
    print(f"🎙️ บันทึกเสียง {DURATION} วินาที...")
    audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='int16')
    sd.wait()
    wav.write(path, SAMPLE_RATE, audio)
    print(f"✅ บันทึกเสร็จ: {path}")

def create_profile(name):
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        record_audio(tmp.name)
        with open(tmp.name, 'rb') as f:
            files = {'audio': f}
            data = {'name': name}
            res = requests.post(f"{SERVER_URL}/create-profile", files=files, data=data)
        print("📦 สร้างโปรไฟล์:", res.json())
    os.remove(tmp.name)

def identify_speaker():
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        record_audio(tmp.name)
        with open(tmp.name, 'rb') as f:
            files = {'audio': f}
            res = requests.post(f"{SERVER_URL}/upload-audio", files=files)
        print("🧠 ผู้พูดคือ:", res.json())
    os.remove(tmp.name)

if __name__ == "__main__":
    while True:
        mode = input("เลือกโหมด [1] สร้างโปรไฟล์  [2] ระบุตัวผู้พูด  [q] ออก: ").strip()
        if mode == "1":
            name = input("ชื่อโปรไฟล์: ").strip()
            create_profile(name)
        elif mode == "2":
            identify_speaker()
        elif mode == "q":
            break