"""
Enhanced HR Chatbot Frontend
==============================
New features over original:
- Multi-model selector (OpenAI / Claude / Ollama)
- Voice input via Whisper API (OpenAI)
- Sentiment indicator on each message
- Multi-language auto-detect banner
- HR Analytics Report tab
- Health status sidebar
- Chat history export
- User profile & role-based display
"""

import os
import io
import json
import datetime
import streamlit as st
from dotenv import load_dotenv
load_dotenv()
try:
    from streamlit_chat import message as st_message
except Exception:
    def st_message(text, is_user=False, key=None):
        role = "user" if is_user else "assistant"
        with st.chat_message(role):
            st.write(text)

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HR Assistant Pro",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .main-header {
      background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
      color: white; padding: 1rem 1.5rem; border-radius: 10px;
      margin-bottom: 1rem; display: flex; align-items: center; gap: 12px;
  }
  .sentiment-badge {
      display: inline-block; padding: 2px 8px; border-radius: 12px;
      font-size: 0.75rem; font-weight: 600; margin-left: 8px;
  }
  .badge-POSITIVE { background: #c8e6c9; color: #2e7d32; }
  .badge-NEGATIVE { background: #ffcdd2; color: #c62828; }
  .badge-UNKNOWN  { background: #f5f5f5; color: #757575; }
  .model-tag {
      font-size: 0.7rem; color: #9e9e9e; margin-top: 2px;
  }
  .lang-banner {
      background: #fff3e0; border-left: 4px solid #ff9800;
      padding: 8px 12px; border-radius: 4px; font-size: 0.85rem;
      margin-bottom: 8px;
  }
  .health-dot { width: 10px; height: 10px; border-radius: 50%;
                display: inline-block; margin-right: 6px; }
  .health-ok  { background: #4caf50; }
  .health-err { background: #f44336; }
</style>
""", unsafe_allow_html=True)

# ─── Session state defaults ───────────────────────────────────────────────────
def init_session():
    defaults = {
        "messages": [],          # list of {"role", "content", "sentiment", "model", "lang"}
        "current_user": "Alexander Verdad",
        "model": os.getenv("DEFAULT_MODEL", "claude"),
        "voice_enabled": False,
        "audio_bytes": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

def check_health():
    status = {}
    status["OpenAI API"] = bool(os.getenv("OPENAI_API_KEY"))
    status["Claude API"] = bool(os.getenv("ANTHROPIC_API_KEY"))
    status["Pinecone DB"] = bool(os.getenv("PINECONE_API_KEY"))
    try:
        import requests
        r = requests.get(f"{os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}/api/tags", timeout=1)
        status["Ollama (Local)"] = r.status_code == 200
    except Exception:
        status["Ollama (Local)"] = False
    return status

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div style="font-size:48px;line-height:1">🤖</div>', unsafe_allow_html=True)
    st.title("HR Assistant Pro")
    st.markdown("---")

    # User profile
    st.subheader("👤 User Profile")
    try:
        import pandas as pd
        df_users = pd.read_csv("employee_data.csv")
        user_names = df_users["name"].tolist()
    except Exception:
        user_names = ["Alexander Verdad", "Guest"]

    st.session_state["current_user"] = st.selectbox(
        "Select Employee", user_names,
        index=user_names.index(st.session_state["current_user"])
              if st.session_state["current_user"] in user_names else 0
    )

    st.markdown("---")

    # Model selector
    st.subheader("🤖 AI Model")
    model_options = {
        "openai":  "OpenAI GPT-3.5",
        "claude":  "Claude (Anthropic)",
        "ollama":  "Ollama (Local)",
    }
    st.session_state["model"] = st.selectbox(
        "Choose Model",
        list(model_options.keys()),
        format_func=lambda x: model_options[x],
        index=list(model_options.keys()).index(st.session_state["model"])
    )

    st.markdown("---")

    # Voice input toggle
    st.subheader("🎤 Voice Input")
    if bool(os.getenv("OPENAI_API_KEY")):
        st.session_state["voice_enabled"] = st.toggle(
            "Enable Voice (Whisper)", value=st.session_state["voice_enabled"]
        )
    else:
        st.session_state["voice_enabled"] = False
        st.info("Voice input requires OpenAI Whisper. Chat works free without it.")

    st.markdown("---")

    # Health status
    st.subheader("🟢 System Health")
    health = check_health()
    for service, ok in health.items():
        dot_class = "health-ok" if ok else "health-err"
        icon = "✅" if ok else "❌"
        st.markdown(
            f'<span class="health-dot {dot_class}"></span>{icon} {service}',
            unsafe_allow_html=True
        )

    st.markdown("---")

    # Export chat
    if st.button("📥 Export Chat History"):
        export_data = json.dumps(st.session_state["messages"], indent=2, default=str)
        st.download_button(
            "Download JSON",
            data=export_data,
            file_name=f"hr_chat_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json"
        )

    if st.button("🗑️ Clear Chat"):
        st.session_state["messages"] = []
        st.rerun()

    st.markdown("---")
    st.caption("© 2026 Saksham Srivastava · sakshamsrivastava7000@gmail.com")

# ─── Voice transcription ──────────────────────────────────────────────────────
def transcribe_audio(audio_bytes: bytes) -> str:
    """Transcribe audio using OpenAI Whisper API"""
    if not os.getenv("OPENAI_API_KEY"):
        st.error("Voice input requires OpenAI Whisper key. Disabled.")
        return ""
    try:
        import openai
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "voice_input.wav"
        transcript = client.audio.transcriptions.create(
            model="whisper-1", file=audio_file
        )
        return transcript.text
    except Exception as e:
        st.error(f"Transcription failed: {e}")
        return ""

# ─── Main UI ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <span style="font-size:2rem">🤖</span>
  <div>
    <h2 style="margin:0;font-size:1.4rem">HR Assistant Pro</h2>
    <p style="margin:0;opacity:0.8;font-size:0.9rem">Powered by multi-model AI · Autonomous · Multilingual</p>
  </div>
</div>
""", unsafe_allow_html=True)

# Tabs
tab_chat, tab_analytics, tab_about = st.tabs(["💬 Chat", "📊 HR Analytics", "ℹ️ About"])

def _process_and_send(text: str):
    try:
        from app.backend import get_response
    except Exception:
        import sys
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from app.backend import get_response
    st.session_state["messages"].append({
        "role": "user", "content": text, "sentiment": None, "model": None, "lang": None
    })
    with st.spinner("Thinking… 🤔"):
        result = get_response(
            user_input=text,
            user=st.session_state["current_user"],
            model=st.session_state["model"],
            session_id=st.session_state["current_user"]
        )
    bot_reply = result["response"]
    if result.get("error") == "rate_limited":
        bot_reply = "⏱️ Slow down! You're sending messages too quickly."
    elif result.get("flagged"):
        bot_reply = "⚠️ I detected a suspicious input pattern. Please ask a valid HR question."
    st.session_state["messages"].append({
        "role": "assistant",
        "content": bot_reply,
        "sentiment": result.get("sentiment", {}),
        "model": result.get("model_used", "?"),
        "lang": result.get("detected_lang", "en"),
    })
    st.rerun()

# ─── CHAT TAB ────────────────────────────────────────────────────────────────
with tab_chat:
    # Display chat history
    chat_container = st.container()
    with chat_container:
        for i, msg in enumerate(st.session_state["messages"]):
            is_user = msg["role"] == "user"
            st_message(msg["content"], is_user=is_user, key=f"msg_{i}")

            if not is_user and msg.get("sentiment"):
                s = msg["sentiment"]
                lang_info = ""
                if msg.get("lang") and msg["lang"] != "en":
                    lang_info = f" | 🌐 Detected: `{msg['lang']}`"
                st.markdown(
                    f'<div class="model-tag">Model: <b>{msg.get("model","?")}</b> · '
                    f'Sentiment: <span class="sentiment-badge badge-{s.get("label","UNKNOWN")}">'
                    f'{s.get("emoji","😐")} {s.get("label","?")}</span>{lang_info}</div>',
                    unsafe_allow_html=True
                )

    st.markdown("---")

    # Voice input section
    if st.session_state["voice_enabled"]:
        st.markdown("#### 🎤 Voice Input")
        audio_input = st.audio_input("Record your question (click mic icon)")
        if audio_input:
            st.session_state["audio_bytes"] = audio_input.getvalue()
            with st.spinner("Transcribing…"):
                transcribed = transcribe_audio(st.session_state["audio_bytes"])
            if transcribed:
                st.info(f"📝 Transcribed: *{transcribed}*")
                if st.button("✅ Send Transcribed Message"):
                    _process_and_send(transcribed)

    # Text input
    with st.form("chat_form", clear_on_submit=True):
        col1, col2 = st.columns([5, 1])
        with col1:
            user_input = st.text_input(
                "Ask your HR question…",
                placeholder="e.g. How many vacation days do I have left?",
                label_visibility="collapsed"
            )
        with col2:
            submitted = st.form_submit_button("Send 🚀", use_container_width=True)

    if submitted and user_input.strip():
        _process_and_send(user_input.strip())


# ─── ANALYTICS TAB ────────────────────────────────────────────────────────────
with tab_analytics:
    st.subheader("📊 HR Analytics Dashboard")

    col_a, col_b = st.columns([2, 1])

    with col_a:
        if st.button("🔄 Generate Full Report"):
            try:
                from app.backend import generate_hr_analytics_report
            except Exception:
                import sys
                from pathlib import Path
                root = Path(__file__).resolve().parent.parent
                if str(root) not in sys.path:
                    sys.path.insert(0, str(root))
                from app.backend import generate_hr_analytics_report
            with st.spinner("Generating report…"):
                report_md = generate_hr_analytics_report()
            st.markdown(report_md)

            st.download_button(
                "📥 Download Report (.md)",
                data=report_md,
                file_name=f"hr_report_{datetime.datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown"
            )

    with col_b:
        st.info("""
**Available Analytics:**
- 👥 Workforce headcount
- 🏢 Department breakdown
- 📊 Rank distribution
- 📅 Leave balance summary
- ⚠️ Low leave alerts
        """)

    # Quick live charts
    try:
        import pandas as pd
        import plotly.express as px

        df_chart = pd.read_csv("employee_data.csv")

        c1, c2 = st.columns(2)
        with c1:
            dept_fig = px.pie(
                df_chart, names="organizational_unit",
                title="👥 Employees by Department",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(dept_fig, use_container_width=True)

        with c2:
            leave_fig = px.bar(
                df_chart, x="name", y=["vacation_leave", "sick_leave"],
                barmode="group", title="📅 Leave Balances",
                labels={"value": "Days", "variable": "Leave Type"}
            )
            st.plotly_chart(leave_fig, use_container_width=True)

    except Exception as e:
        st.warning(f"Charts unavailable: {e}")


# ─── ABOUT TAB ───────────────────────────────────────────────────────────────
with tab_about:
    st.markdown("""
## HR Assistant Pro — Enhanced Edition

### 🆕 New Features
| Feature | Description |
|---|---|
| 🤖 Multi-model AI | OpenAI GPT, Claude, or Ollama with automatic fallback |
| 🎤 Voice Input | Whisper-powered speech-to-text |
| 🌐 Multi-language | Auto-detects and translates 100+ languages |
| 😊 Sentiment Analysis | DistilBERT-based emotion detection on queries |
| 📊 HR Analytics | Auto-generated reports with charts |
| 🛡️ Security | Prompt injection protection + rate limiting |
| 📝 Audit Logging | Compliance-ready audit trail |
| 🐳 Docker-ready | Full containerization included |

### 🏗️ Architecture
```
User → Streamlit UI → Backend Engine
                      ├── LLM Router (OpenAI / Claude / Ollama)
                      ├── Pinecone Vector DB (HR policies)
                      ├── Employee Data (CSV/DB)
                      ├── Sentiment Analyzer (HuggingFace local)
                      └── Translation Layer (Google Translate free)
```

### 📄 Original Project
Built by [TK] using LangChain, Pinecone, and OpenAI.  
Enhanced for production deployment.
    """)
    st.caption("© 2026 Saksham Srivastava · sakshamsrivastava7000@gmail.com")
