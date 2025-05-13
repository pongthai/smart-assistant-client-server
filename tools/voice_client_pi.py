import sounddevice as sd
import scipy.io.wavfile as wav
import requests
import tempfile
import os
import random

SAMPLE_RATE = 16000
DURATION = 6  # วินาทีต่อรอบ
SERVER_URL = "http://192.168.1.100:8000"  # เปลี่ยน <MAC-IP> เป็น IP จริงของ Mac Mini

# ตัวอย่างประโยคภาษาไทย
SAMPLE_SENTENCES = [
    "สวัสดีจ้า วันนี้อากาศดีมากเลยนะ",
    "กำลังทดสอบระบบระบุเสียงอัจฉริยะอยู่นะ",    
    "ตอนนี้กำลังนั่งอยู่ในห้องทำงานนะ มีอะไรก็เรียกนะ",
    "ตอนนี้กำลังยุ่งอยู่ อย่าเพิ่งรบกวนนะ"
]

def record_audio(path, hint=None):
    print(f"\n🎙️ บันทึกเสียง {DURATION} วินาที...")
    if hint:
        print(f"🗣️ พูดประโยคนี้: \033[92m{hint}\033[0m")
    audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='int16')
    sd.wait()
    wav.write(path, SAMPLE_RATE, audio)
    print(f"✅ เสร็จสิ้น: {path}")

def create_profile(name):
    temp_files = []
    try:
        for i in range(2):
            hint = random.choice(SAMPLE_SENTENCES)
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                record_audio(tmp.name, hint=hint)
                temp_files.append(('audio', open(tmp.name, 'rb')))

        data = {'name': name}
        res = requests.post(f"{SERVER_URL}/create-profile", files=temp_files, data=data)
        print("📦 สร้างโปรไฟล์:", res.json())

    finally:
        for _, f in temp_files:
            f.close()
            os.remove(f.name)

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
