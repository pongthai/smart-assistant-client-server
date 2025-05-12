#to run "uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload"

from fastapi import FastAPI, File, UploadFile, Form
from pydantic import BaseModel
from gpt_integration import GPTClient
from voice_profile_manager import VoiceProfileManager
import tempfile
import shutil
import os

app = FastAPI()
gpt_client = GPTClient()
vpm = VoiceProfileManager()

class ChatRequest(BaseModel):
    user_voice: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    reply = gpt_client.ask(user_voice=request.user_voice)
    return ChatResponse(response=reply)

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
