"""
Enhanced HR Chatbot Backend
============================
Enhancements over original:
- Multi-model support: OpenAI GPT-4, Claude (Anthropic), Ollama (local fallback)
- Sentiment analysis via HuggingFace transformers (free, local)
- Automatic language detection & translation (deep-translator, free)
- Rate limiting & API key rotation
- Structured logging (loguru)
- Prometheus metrics instrumentation
- Prompt injection protection
- Audit logging for compliance
- Automated HR analytics report generation
"""

import os
import re
import json
import time
import hashlib
import datetime
from typing import Optional, Dict, Any, List, Tuple
from functools import lru_cache
from collections import defaultdict

import pandas as pd
from loguru import logger

# ─── LLM / LangChain ────────────────────────────────────────────────────────
try:
    from langchain_anthropic import ChatAnthropic
    from langchain_community.vectorstores import Pinecone as PineconeVectorStore
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain.chains import RetrievalQA
    from langchain.tools.python.tool import PythonAstREPLTool
    from langchain.agents import initialize_agent, Tool, AgentType
    from langchain.chains import LLMMathChain
    LANGCHAIN_AVAILABLE = True
except Exception:
    ChatAnthropic = None
    PineconeVectorStore = None
    HuggingFaceEmbeddings = None
    RetrievalQA = None
    PythonAstREPLTool = None
    initialize_agent = None
    Tool = None
    AgentType = None
    LLMMathChain = None
    LANGCHAIN_AVAILABLE = False

# ─── Pinecone ───────────────────────────────────────────────────────────────
from pinecone import Pinecone, ServerlessSpec

# ─── Config ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY    = os.getenv("ANTHROPIC_API_KEY", "")
PINECONE_API_KEY     = os.getenv("PINECONE_API_KEY", "")
PINECONE_ENV         = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
PINECONE_INDEX       = os.getenv("PINECONE_INDEX_NAME", "tk-policy")
OLLAMA_BASE_URL      = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL        = os.getenv("DEFAULT_MODEL", "openai")   # openai | claude | ollama
RATE_LIMIT_RPM       = int(os.getenv("RATE_LIMIT_RPM", "20"))
ENABLE_SENTIMENT     = os.getenv("ENABLE_SENTIMENT", "true").lower() == "true"
ENABLE_TRANSLATION   = os.getenv("ENABLE_TRANSLATION", "true").lower() == "true"
AUDIT_LOG_PATH       = os.getenv("AUDIT_LOG_PATH", "logs/audit.jsonl")

# ─── Logging setup ──────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logger.add("logs/app.log", rotation="10 MB", retention="30 days", level="INFO")
logger.add(AUDIT_LOG_PATH, rotation="50 MB", retention="90 days",
           level="INFO", filter=lambda r: "AUDIT" in r["message"])

# ─── Prometheus metrics ──────────────────────────────────────────────────────
try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server
    REQUEST_COUNT    = Counter("hr_chatbot_requests_total",    "Total chatbot requests",  ["model", "status"])
    RESPONSE_TIME    = Histogram("hr_chatbot_response_seconds", "Response latency")
    ACTIVE_USERS     = Gauge("hr_chatbot_active_users",         "Active user sessions")
    SENTIMENT_GAUGE  = Gauge("hr_chatbot_sentiment_score",      "Average sentiment of last 100 queries")
    PROMETHEUS_ENABLED = True
    logger.info("Prometheus metrics enabled")
except ImportError:
    PROMETHEUS_ENABLED = False
    logger.warning("prometheus_client not installed – metrics disabled")

# ─── Sentiment analysis (HuggingFace – runs locally, free) ──────────────────
_sentiment_pipeline = None

def get_sentiment_pipeline():
    global _sentiment_pipeline
    if _sentiment_pipeline is None and ENABLE_SENTIMENT:
        try:
            from transformers import pipeline
            _sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
                truncation=True, max_length=512
            )
            logger.info("Sentiment analysis pipeline loaded")
        except Exception as e:
            logger.warning(f"Could not load sentiment pipeline: {e}")
    return _sentiment_pipeline

def analyze_sentiment(text: str) -> Dict[str, Any]:
    """Returns {'label': 'POSITIVE'|'NEGATIVE', 'score': float, 'emoji': str}"""
    pipe = get_sentiment_pipeline()
    if pipe is None:
        return {"label": "UNKNOWN", "score": 0.5, "emoji": "😐"}
    try:
        result = pipe(text[:512])[0]
        emoji_map = {"POSITIVE": "😊", "NEGATIVE": "😟"}
        return {
            "label": result["label"],
            "score": round(result["score"], 3),
            "emoji": emoji_map.get(result["label"], "😐")
        }
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}")
        return {"label": "UNKNOWN", "score": 0.5, "emoji": "😐"}

# ─── Language detection & translation (deep-translator, free) ───────────────
def detect_and_translate(text: str) -> Tuple[str, str]:
    """Returns (translated_text, detected_language_code)"""
    if not ENABLE_TRANSLATION or len(text.strip()) < 4:
        return text, "en"
    try:
        from deep_translator import GoogleTranslator
        from langdetect import detect
        lang = detect(text)
        if lang == "en":
            return text, "en"
        translated = GoogleTranslator(source=lang, target="en").translate(text)
        logger.info(f"Translated from {lang} to en")
        return translated, lang
    except Exception as e:
        logger.warning(f"Translation skipped: {e}")
        return text, "en"

def translate_response(text: str, target_lang: str) -> str:
    """Translate response back to user's language"""
    if target_lang == "en" or not ENABLE_TRANSLATION:
        return text
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source="en", target=target_lang).translate(text)
    except Exception as e:
        logger.warning(f"Response translation failed: {e}")
        return text

def local_answer(text: str, user: str) -> Optional[str]:
    """Returns a local, deterministic answer for common HR queries"""
    q = text.strip().lower()
    if q in {"hi", "hello", "hey"} or q.startswith(("hi ", "hello ", "hey ", "good morning", "good evening")):
        return "Hi! Ask me about your leave balance, department, position, supervisor, or salary."
    try:
        df = pd.read_csv("employee_data.csv")
    except Exception as e:
        logger.warning(f"Local answer cannot read data: {e}")
        return None
    required = {"name", "organizational_unit", "position", "supervisor", "vacation_leave", "sick_leave", "basic_pay_in_php"}
    missing = [c for c in required if c not in df.columns]
    if missing:
        logger.error(f"Employee data missing columns: {missing}")
        return None
    row = df[df["name"].str.lower() == user.lower()]
    if row.empty:
        return None
    data = row.iloc[0]
    if ("vacation" in q and "leave" in q) or ("vl" in q) or ("vacation days" in q):
        return f"{user} has {data['vacation_leave']} vacation days remaining."
    if ("sick" in q and "leave" in q) or ("sl" in q) or ("sick days" in q):
        return f"{user} has {data['sick_leave']} sick days remaining."
    if "leave balance" in q or "leave balances" in q or ("leave" in q and "balance" in q):
        return f"{user} has {data['vacation_leave']} vacation days and {data['sick_leave']} sick days remaining."
    if "department" in q or "team" in q or "organizational unit" in q:
        return f"{user} works in the {data['organizational_unit']}."
    if "position" in q or "job title" in q or "role" in q or "job" in q:
        return f"{user}'s position is {data['position']}."
    if "supervisor" in q or "manager" in q or "boss" in q or "lead" in q:
        sup = data.get("supervisor", "")
        if isinstance(sup, str) and sup.strip():
            return f"{user}'s supervisor is {sup}."
        return f"I couldn't find a supervisor listed for {user}."
    if "salary" in q or "basic pay" in q or "pay" in q or "earn" in q:
        try:
            amount = int(data["basic_pay_in_php"])
            return f"{user}'s basic pay is PHP {amount:,} per month."
        except Exception:
            return f"I couldn't determine {user}'s salary from the records."
    return None

# ─── Prompt injection protection ─────────────────────────────────────────────
INJECTION_PATTERNS = [
    r"ignore (all )?(previous |above )?instructions",
    r"disregard (your |all |previous )?instructions",
    r"you are now",
    r"act as (a |an )?(?!hr|assistant|helpful)",
    r"jailbreak",
    r"DAN mode",
    r"forget (your |all )?instructions",
    r"new persona",
    r"system prompt",
    r"reveal (your |the )?prompt",
]
_INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)

def sanitize_input(text: str) -> Tuple[str, bool]:
    """Returns (cleaned_text, was_flagged)"""
    # Strip control chars
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Truncate to 1000 chars
    cleaned = cleaned[:1000]
    flagged = bool(_INJECTION_RE.search(cleaned))
    if flagged:
        logger.warning(f"AUDIT | INJECTION_ATTEMPT | input={text[:200]}")
    return cleaned, flagged

# ─── Rate limiter ────────────────────────────────────────────────────────────
_rate_store: Dict[str, List[float]] = defaultdict(list)

def is_rate_limited(user_id: str) -> bool:
    now = time.time()
    window = 60.0
    _rate_store[user_id] = [t for t in _rate_store[user_id] if now - t < window]
    if len(_rate_store[user_id]) >= RATE_LIMIT_RPM:
        logger.warning(f"Rate limit hit for user: {user_id}")
        return True
    _rate_store[user_id].append(now)
    return False

# ─── Pinecone + Embeddings ───────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_vectorstore():
    # Uses free local HuggingFace embeddings — no OpenAI key or billing needed
    if not LANGCHAIN_AVAILABLE or HuggingFaceEmbeddings is None or PineconeVectorStore is None:
        raise RuntimeError("LangChain unavailable")
    pc = Pinecone(api_key=PINECONE_API_KEY)
    embed = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    index = pc.Index(PINECONE_INDEX)
    return PineconeVectorStore(index, embed.embed_query, "text")

# ─── LLM factory (multi-model with fallback chain) ───────────────────────────
def get_llm(model: str = DEFAULT_MODEL):
    """
    Returns LLM instance. Falls back down the chain:
    claude → ollama → raises
    """
    order = _build_model_order(model)
    for m in order:
        try:
            if m == "claude" and ANTHROPIC_API_KEY:
                return ChatAnthropic(anthropic_api_key=ANTHROPIC_API_KEY,
                                     model="claude-3-haiku-20240307", temperature=0.0), "claude"
            elif m == "ollama":
                from langchain_community.llms import Ollama
                llm = Ollama(base_url=OLLAMA_BASE_URL, model="mistral")
                # quick connectivity check
                llm.invoke("ping")
                return llm, "ollama"
        except Exception as e:
            logger.warning(f"LLM {m} unavailable: {e}")
    raise RuntimeError("No LLM available. Check your ANTHROPIC_API_KEY in .env")

def _build_model_order(preferred: str) -> List[str]:
    all_models = ["claude", "ollama"]  # OpenAI removed — use Claude free tier instead
    order = [preferred] + [m for m in all_models if m != preferred]
    return order

# ─── Agent builder ───────────────────────────────────────────────────────────
def build_agent(user: str, model: str = DEFAULT_MODEL):
    if not LANGCHAIN_AVAILABLE:
        raise RuntimeError("LangChain unavailable")
    llm, active_model = get_llm(model)
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(PINECONE_INDEX)
    embed = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    df = pd.read_csv("employee_data.csv")

    def policy_search(query: str) -> str:
        try:
            qvec = embed.embed_query(query)
            res = index.query(vector=qvec, top_k=5, include_metadata=True)
            chunks = [m.get("metadata", {}).get("text", "") for m in res.get("matches", [])]
            context = "\n\n".join([c for c in chunks if c])
            if not context:
                return "No relevant policy text found."
            return f"{context}\n\nQuestion: {query}\nAnswer the question based on the above policy context."
        except Exception as e:
            return f"Policy search error: {e}"
    python_repl = PythonAstREPLTool(locals={"df": df})
    calculator  = LLMMathChain.from_llm(llm=llm, verbose=False)
    df_columns  = df.columns.to_list()

    tools = [
        Tool(
            name="Timekeeping Policies",
            func=policy_search,
            description=(
                "Use this to answer questions about leave policies, vacation, sick leave, "
                "maternity/paternity leave, or any HR policy questions. "
                "Input should be a clear question about the policy."
            )
        ),
        Tool(
            name="Employee Data",
            func=python_repl.run,
            description=(
                f"Use this to query employee records stored in pandas DataFrame 'df'. "
                f"Columns: {df_columns}. "
                f"Current user is '{user}'. Always filter by the user's name when answering personal queries."
            )
        ),
        Tool(
            name="Calculator",
            func=calculator.run,
            description="Use this for arithmetic and math calculations."
        ),
    ]

    agent_kwargs = {
        "prefix": (
            f"You are a friendly, professional HR assistant. "
            f"You are assisting: {user}. "
            f"Answer HR-related questions accurately. Be concise and empathetic. "
            f"You have access to the following tools:"
        )
    }

    agent = initialize_agent(
        tools, llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=False,
        agent_kwargs=agent_kwargs,
        handle_parsing_errors=True,    # NEW: graceful parsing error handling
        max_iterations=5,              # NEW: prevent infinite loops
        early_stopping_method="generate"
    )
    return agent, active_model

def _anthropic_direct_response(prompt: str, user: str) -> str:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY missing")
    from anthropic import Anthropic
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=512,
        temperature=0.2,
        system=(
            f"You are a friendly, professional HR assistant. "
            f"You are assisting: {user}. "
            f"Answer HR-related questions accurately. Be concise and empathetic."
        ),
        messages=[{"role": "user", "content": prompt}],
    )
    if not resp.content:
        return ""
    return "".join([c.text for c in resp.content if hasattr(c, "text")])

# ─── Analytics / Report generation ──────────────────────────────────────────
def generate_hr_analytics_report() -> str:
    """Generate a markdown HR analytics report from employee_data.csv"""
    try:
        df = pd.read_csv("employee_data.csv")
        total = len(df)
        dept_counts    = df["organizational_unit"].value_counts().to_dict()
        rank_counts    = df["rank"].value_counts().to_dict()
        status_counts  = df["employment_status"].value_counts().to_dict()
        avg_vl = round(df["vacation_leave"].mean(), 1)
        avg_sl = round(df["sick_leave"].mean(), 1)
        low_vl = df[df["vacation_leave"] < 5][["name", "vacation_leave"]].to_dict("records")
        low_sl = df[df["sick_leave"] < 3][["name", "sick_leave"]].to_dict("records")

        lines = [
            f"# 📊 HR Analytics Report",
            f"_Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}_\n",
            f"## Workforce Summary",
            f"- **Total Employees:** {total}",
            f"- **Avg Vacation Leave Balance:** {avg_vl} days",
            f"- **Avg Sick Leave Balance:** {avg_sl} days\n",
            f"## By Department",
            *[f"- {k}: {v}" for k, v in dept_counts.items()],
            f"\n## By Rank",
            *[f"- {k}: {v}" for k, v in rank_counts.items()],
            f"\n## By Employment Status",
            *[f"- {k}: {v}" for k, v in status_counts.items()],
        ]
        if low_vl:
            lines += [f"\n## ⚠️ Low Vacation Leave (<5 days)"]
            lines += [f"- {r['name']}: {r['vacation_leave']} days" for r in low_vl]
        if low_sl:
            lines += [f"\n## ⚠️ Low Sick Leave (<3 days)"]
            lines += [f"- {r['name']}: {r['sick_leave']} days" for r in low_sl]

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return f"⚠️ Report generation failed: {e}"

# ─── Audit logging ───────────────────────────────────────────────────────────
def audit_log(user: str, query: str, response: str, model: str, sentiment: Dict):
    record = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "user":      user,
        "query_hash": hashlib.sha256(query.encode()).hexdigest()[:16],
        "query_len": len(query),
        "model":     model,
        "sentiment_label": sentiment.get("label"),
        "sentiment_score": sentiment.get("score"),
        "response_len": len(response),
    }
    logger.info(f"AUDIT | {json.dumps(record)}")

# ─── Main public interface ───────────────────────────────────────────────────
def get_response(
    user_input: str,
    user: str = "Guest",
    model: str = DEFAULT_MODEL,
    session_id: str = "default"
) -> Dict[str, Any]:
    """
    Unified response function.

    Returns:
        {
          "response":    str,
          "model_used":  str,
          "sentiment":   dict,
          "detected_lang": str,
          "flagged":     bool,
          "error":       str | None
        }
    """
    start = time.time()

    # 1. Rate limit check
    if is_rate_limited(session_id):
        return {
            "response": "⏱️ You're sending messages too quickly. Please wait a moment.",
            "model_used": "none", "sentiment": {}, "detected_lang": "en",
            "flagged": False, "error": "rate_limited"
        }

    # 2. Input sanitization + injection check
    cleaned_input, flagged = sanitize_input(user_input)
    if flagged:
        return {
            "response": "⚠️ I detected an unusual request pattern. I can only help with HR-related questions.",
            "model_used": "none", "sentiment": {}, "detected_lang": "en",
            "flagged": True, "error": "injection_detected"
        }

    # 3. Language detection & translation to English
    english_input, detected_lang = detect_and_translate(cleaned_input)

    # 4. Sentiment analysis
    sentiment = analyze_sentiment(cleaned_input)

    # 4.5. Local fast path (no external calls)
    try:
        local_resp = local_answer(english_input, user)
        if isinstance(local_resp, str) and local_resp.strip():
            if detected_lang != "en":
                local_resp = translate_response(local_resp, detected_lang)
            if PROMETHEUS_ENABLED:
                REQUEST_COUNT.labels(model="local", status="success").inc()
            audit_log(user, cleaned_input, local_resp, "local", sentiment)
            logger.info("Local answer used")
            return {
                "response": local_resp,
                "model_used": "local",
                "sentiment": sentiment,
                "detected_lang": detected_lang,
                "flagged": flagged,
                "error": None
            }
    except Exception as e:
        logger.warning(f"Local answer path failed: {e}")

    # 5. Build and run agent
    model_used = "none"
    try:
        if not LANGCHAIN_AVAILABLE:
            response_text = _anthropic_direct_response(english_input, user)
            model_used = "claude"
        else:
            agent, model_used = build_agent(user, model)
            response_text = agent.run(english_input)

        # 6. Translate response back if needed
        if detected_lang != "en":
            response_text = translate_response(response_text, detected_lang)

    except Exception as e:
        logger.error(f"Agent error: {e}")
        try:
            fallback_resp = local_answer(english_input, user)
            if isinstance(fallback_resp, str) and fallback_resp.strip():
                if detected_lang != "en":
                    fallback_resp = translate_response(fallback_resp, detected_lang)
                if PROMETHEUS_ENABLED:
                    REQUEST_COUNT.labels(model="local", status="success").inc()
                audit_log(user, cleaned_input, fallback_resp, "local", sentiment)
                logger.info("Local fallback answer used after agent failure")
                return {
                    "response": fallback_resp,
                    "model_used": "local",
                    "sentiment": sentiment,
                    "detected_lang": detected_lang,
                    "flagged": flagged,
                    "error": str(e)
                }
        except Exception as le:
            logger.warning(f"Local fallback failed: {le}")
        response_text = (
            "I couldn't process your request due to a system issue. "
            "Please ask about leave balances, department, position, supervisor, or try again shortly."
        )
        if PROMETHEUS_ENABLED:
            REQUEST_COUNT.labels(model=model_used, status="error").inc()
        return {
            "response": response_text, "model_used": model_used,
            "sentiment": sentiment, "detected_lang": detected_lang,
            "flagged": flagged, "error": str(e)
        }

    elapsed = time.time() - start

    # 7. Metrics
    if PROMETHEUS_ENABLED:
        REQUEST_COUNT.labels(model=model_used, status="success").inc()
        RESPONSE_TIME.observe(elapsed)

    # 8. Audit log
    audit_log(user, cleaned_input, response_text, model_used, sentiment)

    logger.info(f"Response generated | model={model_used} | lang={detected_lang} | "
                f"sentiment={sentiment['label']} | elapsed={elapsed:.2f}s")

    return {
        "response": response_text,
        "model_used": model_used,
        "sentiment": sentiment,
        "detected_lang": detected_lang,
        "flagged": flagged,
        "error": None
    }
