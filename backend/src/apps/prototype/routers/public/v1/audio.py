import os
import base64
import io
from fastapi import WebSocket, WebSocketDisconnect

from backend.src.apps.prototype.config.config import groq_client
from backend.src.apps.prototype.models.models import AudioRequest
from . import AudioRouter
import edge_tts


@AudioRouter.post("/audio")
async def process_audio(request: AudioRequest):
    """
    Endpoint for processing audio recordings.
    Accepts base64-encoded audio, transcribes it via Whisper,
    then sends the transcription to LLM to get a response.
    """
    try:
        # Decode base64 audio
        # Format: "data:audio/webm;base64,<data>"
        if "," in request.audio_data:
            audio_base64 = request.audio_data.split(",")[1]
        else:
            audio_base64 = request.audio_data

        audio_bytes = base64.b64decode(audio_base64)

        # Create file-like object
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.webm"

        # Transcribe audio via Groq Whisper
        transcription = await groq_client.audio.transcriptions.create(
            file=("audio.webm", audio_file),
            model="whisper-large-v3-turbo",
            response_format="json",
            language="en"  # can enable auto-detection by removing this parameter
        )

        transcribed_text = transcription.text

        # Get response from LLM
        messages_payload = [
            {
                "role": "user",
                "content": transcribed_text
            }
        ]

        completion = await groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages_payload,
        )

        ai_response = completion.choices[0].message.content

        return {
            "transcription": transcribed_text,
            "response": ai_response
        }

    except Exception as e:
        return {
            "error": str(e),
            "transcription": "",
            "response": "An error occurred while processing audio"
        }


VOICE = "en-US-AvaNeural"


async def text_to_speech_base64(text):
    communicate = edge_tts.Communicate(text, VOICE)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]

    return base64.b64encode(audio_data).decode('utf-8')


@AudioRouter.websocket("/audio-stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            audio_bytes = await websocket.receive_bytes()

            with open("temp_input.wav", "wb") as f:
                f.write(audio_bytes)

            with open("temp_input.wav", "rb") as file:
                transcription = await groq_client.audio.transcriptions.create(
                    file=("temp_input.wav", file.read()),
                    model="whisper-large-v3-turbo",
                    language="en"
                )

            user_text = transcription.text

            chat_completion = await groq_client.chat.completions.create(
                messages=[{"role": "user", "content": user_text}],
                model="llama-3.1-8b-instant",
            )
            ai_response_text = chat_completion.choices[0].message.content

            audio_base64 = await text_to_speech_base64(ai_response_text)

            await websocket.send_json({
                "user_text": user_text,
                "ai_text": ai_response_text,
                "audio": audio_base64
            })

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")
        await websocket.close()
