from fastapi import APIRouter

ChatRouter = APIRouter(prefix="/api/v1/chat", tags=["Chat"])
AudioRouter = APIRouter(prefix="/api/v1/audio", tags=["Audio"])
WebSocketRouter = APIRouter(prefix="/api/v1/ws", tags=["WebSocket"])

from .chat import *
from .audio import *
from .websocket import *