# HR Chatbot Pro — Deployment Guide
## 100% Free — No OpenAI billing required

**Stack:** Claude (Anthropic free tier) · HuggingFace Embeddings · Pinecone · Streamlit · Railway

---

## What You Need (All Free)

| Service | What for | Cost |
|---|---|---|
| Anthropic Claude | AI that answers questions | Free — 5M tokens/month |
| Pinecone | Stores your HR policy | Free — 1 index |
| Railway | Hosts your app online | Free — $5 credit/month |
| HuggingFace embeddings | Converts text to vectors | Free — runs locally |

---

## Step 1 — Install Python on Your PC

1. Go to https://www.python.org/downloads/
2. Download Python 3.11
3. Run the installer — **check "Add Python to PATH"** before clicking Install
4. Verify: open Command Prompt, type `python --version`

---

## Step 2 — Set Up Project Folder

1. Create a folder on Desktop called `hr-chatbot`
2. Extract the zip into it
3. You should see `hr-chatbot-enhanced/` inside

---

## Step 3 — Get Your 2 Free API Keys

### Anthropic Claude Key (Free)
1. Go to https://console.anthropic.com → sign up free
2. Click "Get API Keys" → "Create Key" → copy it
3. Looks like: `sk-ant-api03-...`

### Pinecone Key (Free)
1. Go to https://app.pinecone.io → sign up free
2. Copy API key from dashboard
3. Create an index with these exact settings:
   - Name: `tk-policy`
   - **Dimensions: `384`** ← important, must be 384
   - Metric: `cosine`
   - Cloud: AWS, Region: us-east-1

---

## Step 4 — Create Your .env File

1. Open the `hr-chatbot-enhanced` folder
2. Copy `.env.template` → rename the copy to `.env`
3. Open `.env` in Notepad and fill in your keys:

```
ANTHROPIC_API_KEY=sk-ant-YOUR-KEY-HERE
PINECONE_API_KEY=YOUR-PINECONE-KEY-HERE
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=tk-policy
DEFAULT_MODEL=claude
ENABLE_SENTIMENT=false
ENABLE_TRANSLATION=true
AUTH_ENABLED=false
```

4. Save and close

---

## Step 5 — Install Packages & Upload HR Policy

Open Command Prompt and run these one at a time:

```bash
cd Desktop\hr-chatbot\hr-chatbot-enhanced
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python upload_policy.py
```

The last command uploads your HR policy to Pinecone. Takes 2-3 minutes first time.
You only ever need to run it once.

---

## Step 6 — Test Locally (Optional)

```bash
streamlit run app/frontend.py
```

Opens at http://localhost:8501 — try asking "How many vacation days does Alexander Verdad have?"

---

## Step 7 — Host Online Free with Railway

### Install tools:
1. Install Node.js from https://nodejs.org (LTS version)
2. In Command Prompt (venv active):
```bash
npm install -g @railway/cli
railway login
```

### Deploy:
```bash
railway init
```
Type `hr-chatbot` when asked for a name.

```bash
railway variables set ANTHROPIC_API_KEY=sk-ant-YOUR-KEY
railway variables set PINECONE_API_KEY=YOUR-KEY
railway variables set PINECONE_ENVIRONMENT=us-east-1
railway variables set PINECONE_INDEX_NAME=tk-policy
railway variables set DEFAULT_MODEL=claude
railway variables set ENABLE_SENTIMENT=false
railway variables set ENABLE_TRANSLATION=true
railway variables set AUTH_ENABLED=false
railway up
```

Wait 3-5 minutes, then:
```bash
railway open
```

You'll get a live URL like `https://hr-chatbot-production.up.railway.app` — share this with anyone!

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `python is not recognized` | Reinstall Python, check "Add to PATH" |
| `(venv)` disappeared | Run `venv\Scripts\activate` again |
| Policy upload fails | Check your `.env` keys are correct, no extra spaces |
| Pinecone dimension error | Make sure index was created with dimensions=384 (not 1536) |
| Railway deploy fails | Run `railway logs` and paste the error to Claude |

