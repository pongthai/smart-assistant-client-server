# smart-assistant-client-server
smart-assistant-client-server

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
GOOGLE_CLOUD_CREDENTIALS_PATH = "gctts_key.json"

TUYA_ACCESS_ID = ""
TUYA_ACCESS_KEY = ""
TUYA_API_ENDPOINT = "https://openapi.tuyaus.com"

WAKE_WORDS = ["ผิงผิง", "สวัสดีผิงผิง","ทดสอบ"]
COMMAND_WORDS = {
    "stop": ["หยุดพูด", "หยุด", "เงียบ"],
    "exit": ["ออกจากโปรแกรม", "เลิกทำงาน"]
}
IDLE_TIMEOUT = 60  # seconds
HELLO_MSG = "ว่าไงจ๊ะ"
ENABLE_AVATAR_DISPLAY = True  # หรือ False ถ้าไม่ต้องการให้แสดง Avatar


