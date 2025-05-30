# smart-assistant-client-server
smart-assistant-client-server

=== SETUP Notes ==

# create python environment
pongthai@rasp-pi-sa:~ $ cd smart-assistant-client-server/
pongthai@rasp-pi-sa:~/smart-assistant-client-server $ cd client/
pongthai@rasp-pi-sa:~/smart-assistant-client-server/client $ python3 -m venv venv
pongthai@rasp-pi-sa:~/smart-assistant-client-server/client $ source ./venv/bin/activate

# install pre-requisite
sudo apt install portaudio19-dev python3-dev

sudo apt install pulseaudio alsa-utils
pulseaudio --start
เพิ่มบรรทัดนี้ไว้ท้ายไฟล์ ~/.bashrc: (better to use service instead)

# install python modules
pip install -r ../requirements.txt

# create ../config.py as below

=====

# config.py

# General settings
PROJECT_NAME = "Smart Assistant"
DEBUG_MODE = True
LOG_LEVEL = "DEBUG" # Change to "INFO", "WARNING", etc.

# Server Settings
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000
SERPER_API_KEY = ""  
OPENAI_API_KEY = ""
OPENAI_MODEL = "gpt-4o-mini"    
SYSTEM_TONE = "family"
HA_URL = "http://localhost:8123"
HA_TOKEN = ""


# Client Settings
GPT_SERVER_ENDPOINT = "http://localhost:8000/chat"
TTS_SERVER_ENDPOINT = "http://localhost:8000/speak"
GOOGLE_CLOUD_CREDENTIALS_PATH = "./server/gctts_key.json"

TUYA_ACCESS_ID = ""
TUYA_ACCESS_KEY = ""
TUYA_API_ENDPOINT = "https://openapi.tuyaus.com"

ENTITY_MAP = { ("ไฟ", "ห้องนั่งเล่น", "ซ้าย"): "switch.livingroom_light_1", ("ไฟ", "ห้องนั่งเล่น", "กลาง"): "switch.livingroom_light_2", ("ไฟ", "ห้องนั่งเล่น", None): "switch.livingroom_light_2", ("ไฟ", "ห้องนอน", None): "switch.livingroom_light_2", ("ไฟ", "หน้าบ้าน", None): "switch.livingroom_light_2", ("พัดลม", "ห้องนั่งเล่น", None): "switch.livingroom_fan", ("ปลั๊ก", "ห้องครัว", None): "switch.kitchen_plug", }

WAKE_WORDS = ["ผิงผิง", "สวัสดีผิงผิง","ทดสอบ"] 
COMMAND_WORDS = { "stop": ["หยุดพูด", "หยุด", "เงียบ"], "exit": ["ออกจากโปรแกรม", "เลิกทำงาน"] }

CONFIRMATION_KEYWORDS = ["ใช่", "ใช่แล้ว", "ตกลง", "โอเค", "ได้เลย"] 
CANCEL_KEYWORDS = ["ไม่", "ไม่ใช่", "ยกเลิก", "หยุด"]

ACTION_KEYWORDS = { "เปิด": ["เปิด", "เปิดไฟ", "เปิดสวิตช์", "เปิดปลั๊ก"], "ปิด": ["ปิด", "ปิดไฟ", "ปิดสวิตช์", "ปิดปลั๊ก"], "เพิ่ม": ["เพิ่ม", "เพิ่มเสียง", "เพิ่มแสง"], "ลด": ["ลด", "ลดเสียง", "ลดแสง"], "ตั้ง": ["ตั้ง", "ตั้งเวลา", "ตั้งอุณหภูมิ"], "หยุด": ["หยุด", "ปิดเสียง", "หยุดเพลง"] } 
STOP_WORDS = ["หยุดพูด","หยุด", "เงียบ", "พอแล้ว"] 
EXIT_WORDS = ["ออกจากโปรแกรม", "เลิกทำงาน"]

IDLE_TIMEOUT = 60  # seconds
HELLO_MSG = "ว่าไงจ๊ะ"
TEMP_AUDIO_PATH = "."
SAMPLE_RATE = 48000
ENABLE_AVATAR_DISPLAY = False  # หรือ False ถ้าไม่ต้องการให้แสดง Avatar
AVATAR_SCALE = 0.5
AVATAR_STATIC="pingping_static_v2.gif"
AVATAR_ANIMATION="pingping_animation_v2.gif"
SESSION_ID = "rasp-pi-001"   

 