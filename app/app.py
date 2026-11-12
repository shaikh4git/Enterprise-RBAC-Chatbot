# Step 7: Create the Streamlit frontend
# Frontend- Sreamlit app for the Enterprise RBAC Chatbot 

import streamlit as st

from auth import authenticate
from chatbot import answer_question
import traceback

st.set_page_config(
    page_title="Ma'din Public School Assistant",
    page_icon="🎓",
    layout="wide",
)


def display_sources(sources):
    """Display clickable source references."""

    if not sources:
        return

    st.caption("Information sources:")

    for source in sources:
        if source.startswith(("https://", "http://")):
            st.markdown(
                f"- [{source}]({source})"
            )
        else:
            st.markdown(f"- {source}")


st.title("🎓 Ma'din Public School Assistant")

st.caption(
    "Ask questions about admissions, academics, "
    "facilities, school activities, and other public "
    "school information."
)


# --------------------------------------------------
# Authentication
# --------------------------------------------------

if "user" not in st.session_state:
    st.session_state.user = None


if not st.session_state.user:

    st.subheader("User Login")

    with st.form("login_form"):

        username = st.text_input("Username")

        password = st.text_input(
            "Password",
            type="password",
        )

        submitted = st.form_submit_button("Login")

    if submitted:

        user = authenticate(
            username,
            password,
        )

        if user:
            st.session_state.user = user
            st.rerun()

        else:
            st.error("Invalid username or password.")

    st.stop()


# --------------------------------------------------
# Authenticated user
# --------------------------------------------------

user = st.session_state.user

st.sidebar.title("Account Information")

st.sidebar.write(
    f"User: {user['username']}"
)

st.sidebar.write(
    f"Department: {user['department']}"
)

st.sidebar.write(
    f"Roles: {', '.join(user['roles'])}"
)

st.sidebar.success(
    "Access to public school website information enabled."
)


if st.sidebar.button("Logout"):

    st.session_state.user = None
    st.session_state.messages = []

    st.rerun()


# --------------------------------------------------
# Chat history
# --------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []


for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])

        display_sources(
            message.get("sources", [])
        )


# --------------------------------------------------
# Chat input
# --------------------------------------------------

query = st.chat_input(
    "Ask anything about Ma'din Public School..."
)


if query:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": query,
        }
    )

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):

        with st.spinner(
            "Searching Ma'din Public School website information..."
        ):

            try:

                answer, sources = answer_question(
                    query,
                    st.session_state.user,
                )

            except Exception:
                st.error(
                    "The chatbot encountered an error. "
                    "Please check the application logs."
                )

                answer = (
                    "I could not process your question "
                    "at this time. Please try again."
                )

                sources = []

        st.markdown(answer)

        display_sources(sources)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
        }
    )