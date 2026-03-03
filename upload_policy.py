"""
upload_policy.py
=================
Run this ONCE to upload your hr_policy.txt into Pinecone.
Uses free HuggingFace embeddings — no OpenAI key needed.

Usage:
    python upload_policy.py
"""

import os
from dotenv import load_dotenv

load_dotenv()

PINECONE_API_KEY   = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX     = os.getenv("PINECONE_INDEX_NAME", "tk-policy")

if not PINECONE_API_KEY:
    print("ERROR: PINECONE_API_KEY not found in your .env file.")
    print("Make sure you have a .env file with PINECONE_API_KEY set.")
    exit(1)

print("=" * 55)
print("  HR Policy → Pinecone Upload")
print("  Using FREE HuggingFace embeddings (no billing)")
print("=" * 55)

# Step 1: Load policy text
print("\n[1/4] Loading hr_policy.txt...")
try:
    with open("hr_policy.txt", encoding="utf-8") as f:
        text = f.read()
    print(f"      Loaded {len(text)} characters")
except FileNotFoundError:
    print("ERROR: hr_policy.txt not found. Make sure you're running")
    print("this script from inside the hr-chatbot-enhanced folder.")
    exit(1)

# Step 2: Split into chunks
print("\n[2/4] Splitting into chunks...")
from langchain_text_splitters import RecursiveCharacterTextSplitter
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.create_documents([text])
print(f"      Created {len(chunks)} chunks")

# Step 3: Load embedding model
print("\n[3/4] Loading free embedding model...")
print("      (downloads ~90MB on first run — please wait)")
from langchain_community.embeddings import HuggingFaceEmbeddings
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
print("      Embedding model ready!")

# Step 4: Upload to Pinecone
print("\n[4/4] Uploading to Pinecone...")
from pinecone import Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX)

# Prepare vectors
texts = [d.page_content for d in chunks]
vectors = embeddings.embed_documents(texts)

# Upsert in batches
batch = 100
for i in range(0, len(vectors), batch):
    part = [
        {"id": f"chunk-{j}", "values": vectors[j], "metadata": {"text": texts[j]}}
        for j in range(i, min(i + batch, len(vectors)))
    ]
    index.upsert(vectors=part)

print("\n" + "=" * 55)
print("  SUCCESS! HR policy uploaded to Pinecone.")
print("  You only need to run this script once.")
print("  Now run:  streamlit run app/frontend.py")
print("=" * 55)
