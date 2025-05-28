from fastapi import APIRouter
from pydantic import BaseModel
from .classifier import IntentClassifier

router = APIRouter()

# ✅ สร้างอินสแตนซ์ของ classifier
classifier = IntentClassifier()

class IntentRequest(BaseModel):
    text: str

class IntentResponse(BaseModel):
    intent: str
    confidence: float
    explanation: str = ""  # optional field (for now)

@router.post("/intent")
async def detect_intent(req: IntentRequest):
    result = classifier.classify(req.text)
    return IntentResponse(
        intent=result.get("intent", "unknown"),
        confidence=result.get("confidence", 0.0),
        explanation=result.get("explanation", "")
    )