"""Voice input component for EngProto"""

import base64
import streamlit as st
import requests
from streamlit_mic_recorder import mic_recorder


def render_audio_component():
    """Render voice input interface"""
    st.subheader("🎤 Voice Input")

    audio_data = mic_recorder(
        start_prompt="Start Recording",
        stop_prompt="Stop Recording",
        key='my_recorder'
    )

    # Process received audio
    # audio_data is dict: {'bytes': ..., 'sample_rate': ..., 'sample_width': ...}
    if audio_data:
        last_audio_id = st.session_state.get('last_processed_audio')
        current_audio_id = id(audio_data['bytes'])

        if current_audio_id != last_audio_id and not st.session_state.processing_audio:
            st.session_state.processing_audio = True
            st.session_state.last_processed_audio = current_audio_id

            with st.spinner("Processing audio..."):
                try:
                    raw_bytes = audio_data['bytes']
                    encoded_audio = base64.b64encode(raw_bytes).decode("utf-8")

                    response = requests.post(
                        "http://127.0.0.1:8000/api/v1/audio/audio",
                        json={"audio_data": encoded_audio},
                        timeout=60
                    )

                    if response.status_code == 200:
                        result = response.json()
                        transcription = result.get("transcription", "")
                        answer = result.get("response", "")

                        if transcription:
                            st.session_state.messages.append({
                                "role": "user",
                                "content": transcription,
                                "type": "audio",
                                "transcription": transcription
                            })
                            if answer:
                                st.session_state.messages.append({"role": "assistant", "content": answer})

                            st.success("✅ Processed!")
                            st.rerun()
                    else:
                        st.error(f"Server error: {response.status_code}")

                except Exception as e:
                    st.error(f"An error occurred: {e}")
                finally:
                    st.session_state.processing_audio = False

    # Voice input information
    with st.expander("ℹ️ How to use voice input"):
        st.markdown("""
        1. Click the microphone button 🎤
        2. Speak your message
        3. Click the stop button ⏹️
        4. Wait for audio to be processed
        5. Transcription and response will appear in chat
        """)
