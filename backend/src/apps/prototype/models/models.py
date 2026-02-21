from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class AudioRequest(BaseModel):
    audio_data: str  # base64 encoded audio
