"""Main UI for EngProto Chat Application"""

import streamlit as st
from chat_component import render_chat_component
from audio_component import render_audio_component


# Page configuration
st.set_page_config(page_title="EngProto Chat", page_icon="🤖", layout="wide")

# Initialize message history in Streamlit session
if "messages" not in st.session_state:
    st.session_state.messages = []
if "processing_audio" not in st.session_state:
    st.session_state.processing_audio = False

# Title and description
st.title("🤖 AI Chatbot (Llama 3 8B)")
st.markdown("You can communicate via text or voice")

# Create two columns for text and voice interface
col1, col2 = st.columns([2, 1])

with col1:
    render_chat_component()

with col2:
    render_audio_component()

# Clear history button
if st.sidebar.button("🗑️ Clear History"):
    st.session_state.messages = []
    st.rerun()

# Sidebar information
with st.sidebar:
    st.markdown("---")
    st.markdown("### 📊 Statistics")
    st.metric("Messages in history", len(st.session_state.messages))
    
    st.markdown("---")
    st.markdown("### ⚙️ Settings")
    st.markdown("""
    **Backend:** FastAPI  
    **LLM:** Llama 3.1 8B (Groq)  
    **STT:** Whisper Large v3 Turbo (Groq)
    """)