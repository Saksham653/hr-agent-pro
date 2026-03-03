<div align="center">

# 🤖 HR Agent Pro

### Autonomous HR Intelligence — Powered by Claude AI

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-Visit_Now-4F46E5?style=for-the-badge)](https://hr-agent-pro.onrender.com/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![LangChain](https://img.shields.io/badge/LangChain-0.1+-1C3C3C?style=for-the-badge)](https://langchain.com)
[![Claude](https://img.shields.io/badge/Claude-3_Haiku-D97706?style=for-the-badge)](https://anthropic.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.31+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Pinecone](https://img.shields.io/badge/Pinecone-Vector_DB-00B5AD?style=for-the-badge)](https://pinecone.io)

**An autonomous, multi-tool HR chatbot agent that answers employee questions about leave, policy, salary, and team structure — instantly and accurately.**

[**Try the Live Demo →**](https://hr-agent-pro.onrender.com/)

---

</div>

## 📸 What It Does

HR Agent Pro is a production-ready AI chatbot built for HR departments. Employees can ask natural language questions and get instant, accurate answers pulled from real HR policy documents and employee records — no HR staff involvement needed for routine queries.

```
Employee:  "How many vacation days do I have left?"
Agent:     "Alexander Verdad has 45 vacation days remaining."

Employee:  "What is the policy on unused sick leave?"
Agent:     "Unused Sick Leave can be carried over to the next year,
            up to a maximum of 30 days. Any excess is forfeited."

Employee:  "How much would my vacation leave be worth if I encash it?"
Agent:     "Based on your basic pay of PHP 15,000 and 45 VL days,
            your encashment value would be PHP 22,500."

Employee:  "Who is my supervisor?"
Agent:     "Alexander Verdad's supervisor is Joseph Santos."
```

> 🎭 **This is a demo.** The app is preloaded with sample employee data so you can explore every feature without needing real credentials. Just open it and start asking questions.

---

## ✨ Features

### 🧠 Autonomous Agent with Multiple Tools
The core of this project is a **LangChain ReAct agent** that autonomously decides which tool to use based on the question. It doesn't follow a fixed script — it reasons through the query, picks the right tool, and composes a clear answer.

| Tool | What It Handles |
|------|----------------|
| **Timekeeping Policies** | Leave rules, entitlements, eligibility, encashment policy — answers from the actual HR policy document via semantic search |
| **Employee Data** | Personal leave balances, salary, position, department, supervisor — live queries against employee records |
| **Calculator** | Leave encashment value, salary math, day calculations |

### 🌐 Multilingual Support
Automatically detects the language of the employee's message and translates both the query and the response. Employees can ask in their native language and receive answers in the same language — powered by Google Translate (free tier).

### 😊 Sentiment Analysis
Every message is analysed for emotional tone using a local DistilBERT model that runs entirely on the server — no external API needed, completely free. A sentiment badge appears on each response so HR teams can spot distressed employees at a glance.

### 🔒 Security Built-In
- **Prompt injection protection** — detects and blocks attempts to override the agent's instructions
- **Rate limiting** — per-user request throttling (20 requests/minute by default)
- **Input sanitisation** — strips control characters and truncates oversized inputs
- **Audit logging** — every query is logged to a JSONL file for compliance review

### 📊 HR Analytics Dashboard
A dedicated tab generates a live markdown analytics report from the employee data, including workforce breakdown by department and rank, average leave balances, and alerts for employees with critically low leave remaining.

### 🏥 Health Monitoring
A FastAPI health server runs alongside Streamlit, exposing `/health` and `/metrics` endpoints. Compatible with Kubernetes liveness probes, Render health checks, and Prometheus scraping.

### 🔄 AI Model Fallback Chain
```
Claude 3 Haiku (primary)
        ↓ if unavailable
Ollama Mistral (local fallback)
        ↓ if unavailable
Clear error with actionable fix
```

---

## 🗂️ Project Structure

```
hr-agent-pro/
├── app/
│   ├── backend.py          # Agent engine, tools, LLM factory, all business logic
│   ├── frontend.py         # Streamlit UI — chat, analytics, health sidebar
│   ├── health_server.py    # FastAPI /health and /metrics endpoints
│   └── auth.py             # OAuth2 + role-based access control
├── tests/
│   ├── test_backend.py         # Unit + integration tests
│   ├── test_messaging_system.py
│   └── test_query_differentiation.py
├── monitoring/
│   └── prometheus.yml      # Prometheus scrape config
├── .github/
│   └── workflows/
│       └── ci-cd.yml       # GitHub Actions: test → build → deploy
├── employee_data.csv        # Sample employee records (preloaded for demo)
├── hr_policy.txt            # HR policy document (indexed in Pinecone)
├── upload_policy.py         # One-time Pinecone ingestion script
├── Dockerfile               # Multi-stage production build
├── docker-compose.yml       # Full stack: app + Ollama + Prometheus + Grafana
├── railway.toml             # One-click Railway deployment
├── .env.template            # All environment variables documented
└── requirements.txt         # Python dependencies
```

---

## 🚀 Try the Demo

The live demo at **[hr-agent-pro.onrender.com](https://hr-agent-pro.onrender.com/)** is preloaded with a sample company dataset. No sign-up needed.

**Sample employees you can ask about:**

| Name | Department | Role | Status |
|------|-----------|------|--------|
| Alexander Verdad | Finance | AR Assistant | Permanent |
| Joseph Peña | Finance | AR Supervisor | Permanent |
| Jinky Francisco | HR | Recruitment Supervisor | Permanent |
| Mark Delos Santos | HR | HR Assistant | Probation |
| Richard Santos | Finance | AR Head | Permanent |

**Things to try:**
- `"How many vacation days does Alexander Verdad have?"`
- `"What is the maternity leave policy?"`
- `"Is Mark Delos Santos eligible for vacation leave?"`
- `"Who are the members of the Finance Department?"`
- `"What would Joseph Peña's leave encashment be worth?"`
- `"How many sick days does Jinky Francisco have left?"`
- Try asking in a different language — multilingual support is active

> ⚠️ **Note:** The demo runs on Render's free tier. If the page loads slowly on first visit, it is waking up from a cold start — this takes about 30 seconds and is normal.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Employee Browser                      │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│              Streamlit Frontend  :8501                   │
│  Chat UI · Analytics Tab · Health Sidebar · Sentiment   │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                   Backend Engine                         │
│                                                          │
│  Input → Sanitize → Translate → Sentiment → Agent       │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │           LangChain ReAct Agent                 │    │
│  │   ┌──────────────┐  ┌────────────┐  ┌────────┐ │    │
│  │   │  HR Policies │  │  Employee  │  │  Calc  │ │    │
│  │   │  (Pinecone   │  │  Data      │  │        │ │    │
│  │   │   RAG)       │  │  (pandas)  │  │        │ │    │
│  │   └──────────────┘  └────────────┘  └────────┘ │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  Claude 3 Haiku ──fallback──▶ Ollama Mistral            │
└──────────┬───────────────────────────────────────────────┘
           │
┌──────────▼──────────┐    ┌──────────────────────────────┐
│  Pinecone Vector DB  │    │  FastAPI Health Server :8001  │
│  HR Policy Chunks   │    │  /health · /metrics · /ready  │
└─────────────────────┘    └──────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| AI Agent | LangChain ReAct | Autonomous tool selection and reasoning |
| LLM | Claude 3 Haiku (Anthropic) | Fast, accurate, generous free tier |
| Embeddings | `all-MiniLM-L6-v2` (HuggingFace) | Free, local, no API key needed |
| Vector DB | Pinecone | Semantic search over HR policy document |
| Frontend | Streamlit | Rapid, clean UI with no frontend boilerplate |
| Monitoring | Prometheus + FastAPI | Production-grade health and metrics |
| Logging | Loguru | Structured logs + JSONL audit trail |
| Translation | deep-translator | Free multilingual support |
| Sentiment | DistilBERT (HuggingFace) | Local emotion detection, no API cost |
| Deployment | Render / Railway / Docker | Flexible, free-tier friendly |
| CI/CD | GitHub Actions | Automated test → build → deploy pipeline |

---

## ⚙️ Run It Yourself

### Prerequisites
- Python 3.11+
- Anthropic API key — free at [console.anthropic.com](https://console.anthropic.com)
- Pinecone API key — free at [app.pinecone.io](https://app.pinecone.io)

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/hr-agent-pro.git
cd hr-agent-pro

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.template .env
# Edit .env and add your ANTHROPIC_API_KEY and PINECONE_API_KEY

# 5. Create Pinecone index
# Go to app.pinecone.io → Create Index
# Name: tk-policy | Dimensions: 384 | Metric: cosine

# 6. Upload HR policy to Pinecone (one time only)
python upload_policy.py

# 7. Run the app
streamlit run app/frontend.py
```

Open [http://localhost:8501](http://localhost:8501)

### Docker (Full Stack)

```bash
docker-compose up -d
```

This starts the chatbot, Ollama (local LLM fallback), Prometheus, and Grafana together.

---

## 🌍 Deploy Free Online

### Railway (Recommended)
```bash
npm install -g @railway/cli
railway login
railway init
railway variables set ANTHROPIC_API_KEY=sk-ant-...
railway variables set PINECONE_API_KEY=...
railway variables set PINECONE_INDEX_NAME=tk-policy
railway up
```

### Render
1. Connect your GitHub repo at [render.com](https://render.com)
2. New Web Service → select repo → Docker runtime
3. Add environment variables in the dashboard
4. Deploy

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

Test coverage includes:
- Input sanitisation and injection detection
- Rate limiter behaviour
- Sentiment analysis output format
- Analytics report generation
- Health endpoint response structure

---

## 🔑 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | ✅ | Claude API key from console.anthropic.com |
| `PINECONE_API_KEY` | ✅ | Pinecone API key from app.pinecone.io |
| `PINECONE_INDEX_NAME` | ✅ | Name of your Pinecone index (default: `tk-policy`) |
| `PINECONE_ENVIRONMENT` | ✅ | Pinecone region (default: `us-east-1`) |
| `DEFAULT_MODEL` | ❌ | `claude` or `ollama` (default: `claude`) |
| `ENABLE_SENTIMENT` | ❌ | Enable sentiment analysis (default: `false`) |
| `ENABLE_TRANSLATION` | ❌ | Enable multilingual support (default: `true`) |
| `RATE_LIMIT_RPM` | ❌ | Requests per minute per user (default: `20`) |
| `AUTH_ENABLED` | ❌ | Require login (default: `false`) |

---

## 💡 What Makes This Different

Most HR chatbots are simple FAQ bots that match keywords. This one is different:

**It reasons.** The ReAct agent framework means the bot thinks through multi-step problems — it can calculate your leave encashment value by first looking up your salary, then looking up your leave balance, then doing the math — all from a single natural question.

**It uses your actual documents.** HR policies are chunked, embedded, and stored in Pinecone. When you ask a policy question, it retrieves the most relevant chunks and answers from the real source — not from a hardcoded script.

**It costs nothing to run.** Claude Haiku's free tier covers approximately 100,000 HR queries per month. Embeddings run locally. Translation uses free APIs. Sentiment runs locally. The entire stack can be hosted for $0.

**It handles failure gracefully.** Every external dependency — Claude API, Pinecone, translation, sentiment — has an independent fallback. The chatbot degrades gracefully instead of crashing. Users always get a helpful response, even when services are down.

---

## 📄 License

This project is for demonstration purposes. See [COPYRIGHT](COPYRIGHT) for details.

---

<div align="center">

Built with ❤️ using [LangChain](https://langchain.com) · [Anthropic Claude](https://anthropic.com) · [Streamlit](https://streamlit.io) · [Pinecone](https://pinecone.io)

**[🚀 Try the Live Demo](https://hr-agent-pro.onrender.com/)**

</div>
