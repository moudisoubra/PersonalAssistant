from fastapi import FastAPI
from pydantic import BaseModel
import ollama

app = FastAPI(title="Voice AI Backend")

class UserInput(BaseModel):
    text: str

@app.post("/chat")
async def process_chat(request: UserInput):
    client = ollama.AsyncClient()
    
    # We maintain a list of messages (conversation history) for this transaction
    messages = [{"role": "user", "content": request.text}]
    
    # Ask the model
    response = await client.chat(
        model="llama3.1",
        messages=messages
    )
    
    return {
        "status": "success",
        "response": response['message'].get('content', '')
    }