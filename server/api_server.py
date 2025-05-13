#to run "uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload"

from fastapi import FastAPI, File, Request, UploadFile, Form,BackgroundTasks
from pydantic import BaseModel
from gpt_integration import GPTClient
from voice_profile_manager import VoiceProfileManager
from fastapi.responses import FileResponse,JSONResponse
from tts_manager import TTSManager
from usage_tracker_instance import usage_tracker

import tempfile
import shutil
import os

app = FastAPI()
gpt_client = GPTClient()
vpm = VoiceProfileManager()
tts_manager = TTSManager()

class ChatRequest(BaseModel):
    user_voice: str

class ChatResponse(BaseModel):
    response: str

def cleanup_file(path: str):
    if os.path.exists(path):
        try:
            os.remove(path)
            print(f"🧹 Deleted: {path}")
        except Exception as e:
            print(f"⚠️ Failed to delete file: {e}")

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    reply = gpt_client.ask(user_voice=request.user_voice)
    return ChatResponse(response=reply)

@app.post("/speak")
async def speak(req: Request, background_tasks: BackgroundTasks):
    data = await req.json()
    text = data.get("text", "")
    is_ssml = data.get("is_ssml", False)

    try:
        mp3_path = tts_manager.synthesize(text=text, is_ssml=is_ssml)
        background_tasks.add_task(cleanup_file, mp3_path)  # ✅ ลบหลังส่ง
        return FileResponse(mp3_path, media_type="audio/mpeg")
    except Exception as e:
        return {"error": f"TTS failed: {str(e)}"}

@app.get("/usage")
async def usage_summary():
    summary = usage_tracker.summarize(by="day")
    return JSONResponse(content=summary)


@app.post("/upload-audio")
async def upload_audio(audio: UploadFile = File(...)):
    if not audio.filename:
        return {"error": "Empty filename"}

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        temp_path = tmp_file.name
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)

    try:
        speaker = vpm.identify_speaker(temp_path)
        return {"speaker": speaker}
    finally:
        os.remove(temp_path)

@app.post("/create-profile")
async def create_profile(name: str = Form(...), audio: UploadFile = File(...)):
    if not name.strip():
        return {"error": "Missing speaker name"}

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        temp_path = tmp_file.name
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)

    try:
        vpm.train_profile(name.strip(), temp_path)
        return {"status": "ok", "profile": name.strip()}
    finally:
        os.remove(temp_path)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "Smart Assistant API is running."}
