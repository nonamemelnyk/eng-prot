import os
from pydantic import BaseModel

from backend.src.apps.prototype.config.config import groq_client
from . import ChatRouter


class ChatRequest(BaseModel):
    message: str


@ChatRouter.post("")
async def chat_endpoint(request: ChatRequest):
    messages_payload = [
        {
            "role": "user",
            "content": request.message
        }
    ]
    completion = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages_payload,
    )
    return {"response": completion.choices[0].message.content}
