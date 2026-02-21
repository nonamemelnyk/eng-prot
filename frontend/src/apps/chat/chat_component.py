"""Text chat component for EngProto"""

import streamlit as st
import requests


def render_chat_component():
    """Render text chat interface"""
    st.subheader("💬 Text Chat")
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if message.get("type") == "audio":
                    st.markdown(f"🎤 *[Voice message]*")
                    if "transcription" in message:
                        st.caption(f"Transcription: {message['transcription']}")
                st.markdown(message["content"])
    
    # Text input field
    if prompt := st.chat_input("Write a message..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Send request to FastAPI server
        try:
            response = requests.post(
                "http://127.0.0.1:8000/api/v1/chat",
                json={"message": prompt},
                timeout=30
            )

            if response.status_code == 200:
                answer = response.json().get("response", "No response from model")
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.rerun()
            else:
                st.error(f"Server error: {response.status_code}")

        except requests.exceptions.ConnectionError:
            st.error("Failed to connect to FastAPI. Check if server is running on port 8000.")
        except Exception as e:
            st.error(f"An error occurred: {e}")
