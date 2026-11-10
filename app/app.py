# Step 7: Create the Streamlit frontend
# Frontend- Sreamlit app for the Enterprise RBAC Chatbot 

import streamlit as st

from auth import authenticate

from chatbot import answer_question


st.set_page_config(
    page_title="Enterprise RBAC Chatbot",
    page_icon="🔐",
    layout="wide",
)


st.title(
    "🔐 Enterprise RBAC Chatbot"
)

st.caption(
    "Enterprise RBAC Chatbot - Version 2.0"
)


# --------------------------------------------------
# Authentication
# --------------------------------------------------

if "user" not in st.session_state:

    st.session_state.user = None


if not st.session_state.user:

    st.subheader(
        "Employee Login"
    )

    with st.form("login_form"):

        username = st.text_input(
            "Username",
        )

        password = st.text_input(
            "Password",
            type="password",
        )

        submitted = st.form_submit_button(
            "Login",
        )

    if submitted:

        user = authenticate(
            username,
            password,
        )

        if user:

            st.session_state.user = user

            st.rerun()

        else:

            st.error(
                "Invalid username or password."
            )

    st.stop()


# --------------------------------------------------
# Authenticated user
# --------------------------------------------------

user = st.session_state.user


st.sidebar.title(
    "Employee Information"
)

st.sidebar.write(
    f"User: {user['username']}"
)

st.sidebar.write(
    f"Department: {user['department']}"
)

st.sidebar.write(
    f"Roles: {', '.join(user['roles'])}"
)


if st.sidebar.button(
    "Logout",
):

    st.session_state.user = None

    st.session_state.messages = []

    st.rerun()


# --------------------------------------------------
# Chat history
# --------------------------------------------------

if "messages" not in st.session_state:

    st.session_state.messages = []


for message in st.session_state.messages:

    with st.chat_message(
        message["role"],
    ):

        st.markdown(
            message["content"],
        )

        if message.get("sources"):

            st.caption(
                "Sources: "
                + ", ".join(
                    message["sources"]
                )
            )


# --------------------------------------------------
# Chat input
# --------------------------------------------------

query = st.chat_input(
    "Ask a question about your company..."
)


if query:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": query,
        }
    )

    with st.chat_message(
        "user",
    ):

        st.markdown(
            query,
        )

    with st.chat_message(
        "assistant",
    ):

        with st.spinner(
            "Searching authorized company documents..."
        ):

            try:

                answer, sources = answer_question(
                    query,
                    user,
                )

            except Exception:

                answer = (
                    "The chatbot encountered an "
                    "unexpected error. Please try again."
                )

                sources = []

        st.markdown(
            answer,
        )

        if sources:

            st.caption(
                "Sources: "
                + ", ".join(
                    sources
                )
            )

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
        }
    )