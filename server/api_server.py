#to run "uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload"

from fastapi import FastAPI
from pydantic import BaseModel
from gpt_integration import GPTClient

app = FastAPI()
gpt_client = GPTClient()

class ChatRequest(BaseModel):
    user_voice: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    reply = gpt_client.ask(user_voice=request.user_voice)
    return ChatResponse(response=reply)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "Smart Assistant API is running."}
