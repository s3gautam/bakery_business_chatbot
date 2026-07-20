import uuid

import httpx
import streamlit as st

from api_client import send_chat_message

st.set_page_config(page_title="WarmOven Assistant", page_icon="🍰", layout="centered")

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("🍰 WarmOven Cakes & Desserts")
st.caption(
    "Ask about our menu, flavours, or delivery — or leave feedback on a past order. "
    "Use the **Configure** page in the sidebar to change business settings."
)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_input = st.chat_input("Type your message... (English, Hindi, or Hinglish)")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = send_chat_message(
                    st.session_state.conversation_id, user_input
                )
                reply = result["reply"]
            except httpx.HTTPError as exc:
                reply = (
                    "Sorry, I'm having trouble reaching the kitchen right now "
                    f"({exc}). Please try again in a moment."
                )
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})

with st.sidebar:
    st.subheader("Conversation")
    st.text(f"ID: {st.session_state.conversation_id[:8]}…")
    if st.button("Start a new conversation"):
        st.session_state.conversation_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()
