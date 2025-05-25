from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
from gpt_integration import GPTClient

app = FastAPI()
gpt_client = GPTClient()

@app.post("/ask")
async def ask_gpt(request: Request):
    try:
        data = await request.json()
        prompt = data.get("prompt")
        system_prompt = data.get("system_prompt")

        if not prompt:
            return JSONResponse(content={"error": "Prompt is required."}, status_code=400)

        reply = gpt_client.ask(prompt=prompt, system_prompt=system_prompt)
        return {"response": reply}

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    