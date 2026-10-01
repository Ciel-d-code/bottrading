import os
import requests
import streamlit as st
from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# CONFIG HELPER
# ============================================================

def get_config(name):
    """
    Ambil konfigurasi dari Streamlit Secrets.
    Jika tidak tersedia, fallback ke environment variable.
    """
    try:
        value = st.secrets.get(name)
        if value:
            return value
    except Exception:
        pass

    return os.getenv(name)


# ============================================================
# CONFIGURATION
# ============================================================

NGROK_URL = get_config("NGROK_URL")
NGROK_USER = get_config("NGROK_USER")
NGROK_PASSWORD = get_config("NGROK_PASSWORD")
LANGFLOW_API_KEY = get_config("LANGFLOW_API_KEY")
FLOW_ID = get_config("FLOW_ID")


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Ciel AI Assistant",
    page_icon="🤖",
    layout="centered",
)


# ============================================================
# VALIDATE CONFIG
# ============================================================

missing_config = []

if not NGROK_URL:
    missing_config.append("NGROK_URL")

if not NGROK_USER:
    missing_config.append("NGROK_USER")

if not NGROK_PASSWORD:
    missing_config.append("NGROK_PASSWORD")

if not LANGFLOW_API_KEY:
    missing_config.append("LANGFLOW_API_KEY")

if not FLOW_ID:
    missing_config.append("FLOW_ID")


if missing_config:
    st.error(
        "❌ Konfigurasi belum lengkap.\n\n"
        f"Variabel yang belum tersedia: {', '.join(missing_config)}"
    )
    st.stop()


# ============================================================
# SESSION STATE
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Settings")

    st.success("Langflow API terhubung")

    st.caption("Flow ID")
    st.code(FLOW_ID)

    st.divider()

    if st.button(
        "🗑️ Clear Chat",
        use_container_width=True
    ):
        st.session_state.messages = []
        st.rerun()

    st.divider()

    st.caption(
        "AI Backend: Langflow\n\n"
        "Architecture: Multi-Agent System"
    )


# ============================================================
# HEADER
# ============================================================

st.title("🤖 Ciel AI Assistant")

st.caption(
    "Multi-Agent AI powered by Langflow"
)


# ============================================================
# CHAT HISTORY
# ============================================================

for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# ============================================================
# LANGFLOW API
# ============================================================

def ask_langflow(message):

    url = (
        f"{NGROK_URL.rstrip('/')}"
        f"/api/v1/run/{FLOW_ID}"
    )

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-api-key": LANGFLOW_API_KEY,
    }

    payload = {
        "input_value": message,
        "input_type": "chat",
        "output_type": "chat",
    }

    try:

        response = requests.post(
            url,
            headers=headers,

            # Basic Auth untuk ngrok
            auth=(
                NGROK_USER,
                NGROK_PASSWORD
            ),

            json=payload,
            params={
                "stream": "false"
            },
            timeout=120,
        )

        response.raise_for_status()

        data = response.json()

        # ====================================================
        # EXTRACT LANGFLOW RESPONSE
        # ====================================================

        try:

            answer = (
                data["outputs"][0]
                ["outputs"][0]
                ["results"]["message"]
                ["data"]["text"]
            )

            return answer

        except (KeyError, IndexError, TypeError):

            return (
                "⚠️ Response Langflow diterima, "
                "tetapi format output tidak dikenali.\n\n"
                f"```json\n{data}\n```"
            )

    except requests.exceptions.Timeout:

        return (
            "⏱️ Request timeout.\n\n"
            "Langflow membutuhkan terlalu lama "
            "untuk memberikan jawaban."
        )

    except requests.exceptions.ConnectionError:

        return (
            "🔌 Tidak dapat terhubung ke ngrok.\n\n"
            "Pastikan Langflow Desktop dan ngrok "
            "sedang berjalan."
        )

    except requests.exceptions.HTTPError as error:

        return (
            "🚫 Langflow/ngrok menolak request.\n\n"
            f"HTTP Error: {error}\n\n"
            f"Response:\n{response.text}"
        )

    except requests.exceptions.RequestException as error:

        return (
            "❌ Request gagal.\n\n"
            f"{error}"
        )

    except ValueError:

        return (
            "⚠️ Response dari Langflow "
            "bukan JSON yang valid."
        )


# ============================================================
# CHAT INPUT
# ============================================================

prompt = st.chat_input(
    "Tanyakan sesuatu kepada AI..."
)


if prompt:

    # --------------------------------------------------------
    # USER MESSAGE
    # --------------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    # --------------------------------------------------------
    # ASSISTANT MESSAGE
    # --------------------------------------------------------

    with st.chat_message("assistant"):

        with st.spinner(
            "🧠 Supervisor sedang berpikir..."
        ):

            answer = ask_langflow(prompt)

            st.markdown(answer)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                }
            )