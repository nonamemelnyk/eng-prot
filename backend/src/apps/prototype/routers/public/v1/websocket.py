import asyncio
import os
import base64
import io
import json
from fastapi import WebSocket, WebSocketDisconnect
from typing import List

from backend.src.apps.prototype.config.config import groq_client
from . import WebSocketRouter
import edge_tts

VOICE = "en-US-AvaNeural"


# async def text_to_speech_base64(text):
#     """Convert text to speech using edge-tts and return as base64"""
#     communicate = edge_tts.Communicate(text, VOICE)
#     audio_data = b""
#     async for chunk in communicate.stream():
#         if chunk["type"] == "audio":
#             audio_data += chunk["data"]
#
#     return base64.b64encode(audio_data).decode('utf-8')

async def process_user_message_and_send(websocket: WebSocket, user_message: str, chat_history: List[dict]):
    try:
        chat_history.append({"role": "user", "content": user_message})

        context = chat_history[-12:]

        chat_completion = await groq_client.chat.completions.create(
            messages=context,
            model="llama-3.1-8b-instant",
        )
        ai_response_text = chat_completion.choices[0].message.content

        chat_history.append({"role": "assistant", "content": ai_response_text})

        # Send text response
        await websocket.send_json({
            "type": "text",
            "user_message": user_message,
            "ai_response": ai_response_text
        })

        communicate = edge_tts.Communicate(ai_response_text, VOICE)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunk_b64 = base64.b64encode(chunk["data"]).decode('utf-8')
                await websocket.send_json({"type": "audio_chunk", "chunk": audio_chunk_b64})

        await websocket.send_json({"type": "audio_end"})

    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})


@WebSocketRouter.websocket("/chat")
async def unified_chat_websocket(websocket: WebSocket):
    """
    Unified WebSocket endpoint for both text and audio chat.
    
    Message formats:
    - Text message: {"type": "text", "content": "user message"}
    - Audio chunk: {"type": "audio_chunk", "data": "base64_audio_data"}
    - Audio end: {"type": "audio_end"}
    
    Responses:
    - Text response: {"type": "text", "user_message": "...", "ai_response": "..."}
    - Audio response: {"type": "audio", "user_message": "...", "ai_response": "...", "audio": "base64_audio"}
    - Error: {"type": "error", "message": "error description"}
    """
    chat_history = [
        {"role": "system", "content": "You are a helpful and witty AI assistant."}
    ]
    # Buffer for collecting audio chunks
    audio_chunks = []
    current_task = None

    try:

        await websocket.accept()

        while True:
            # Receive message (can be text or binary)
            message = await websocket.receive_text()
            data = json.loads(message)

            message_type = data.get("type")

            if message_type == "audio_cancel":
                if current_task and not current_task.done():
                    current_task.cancel()
                    try:
                        await current_task
                    except asyncio.CancelledError:
                        pass
                    await websocket.send_json({"type": "interrupt", "status": "stopped"})
                else:
                    # No task to cancel — send ack immediately so frontend doesn't wait 3s
                    await websocket.send_json({"type": "interrupt", "status": "stopped"})

            elif message_type == "text":
                # Handle text message
                user_message = data.get("content", "")

                current_task = asyncio.create_task(
                    process_user_message_and_send(websocket, user_message, chat_history)
                )

            elif message_type == "audio_chunk":
                # Collect audio chunk
                audio_data = data.get("data", "")
                audio_chunks.append(audio_data)

                # Send acknowledgment
                await websocket.send_json({
                    "type": "audio_chunk_received",
                    "chunk_count": len(audio_chunks)
                })

            elif message_type == "audio_end":
                # Process complete audio
                try:
                    decoded_chunks = []
                    for chunk in audio_chunks:
                        if "," in chunk:
                            chunk = chunk.split(",")[1]
                        decoded_chunks.append(base64.b64decode(chunk))
                    audio_bytes = b"".join(decoded_chunks)

                    # Create file-like object for Whisper
                    audio_file = io.BytesIO(audio_bytes)
                    audio_file.name = "audio.webm"

                    # Transcribe audio via Groq Whisper
                    transcription = await groq_client.audio.transcriptions.create(
                        file=("audio.webm", audio_file),
                        model="whisper-large-v3-turbo",
                        response_format="json",
                        language="en"
                    )

                    user_text = transcription.text

                    current_task = asyncio.create_task(
                        process_user_message_and_send(websocket, user_text, chat_history)
                    )

                    audio_chunks.clear()

                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Error processing audio: {str(e)}"
                    })
                    audio_chunks.clear()

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })

    except WebSocketDisconnect:
        print("Client disconnected from unified chat websocket")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()
