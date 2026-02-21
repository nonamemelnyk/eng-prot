from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
import os
from backend.src.apps.prototype.routers import ChatRouter, AudioRouter, WebSocketRouter

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ChatRouter)
app.include_router(AudioRouter)
app.include_router(WebSocketRouter)

if __name__ == "__main__":
    import uvicorn

    try:
        uvicorn.run("backend.src.apps.prototype.main:app", host="0.0.0.0", port=8000, reload=True)
    except Exception as e:
        print(e)
