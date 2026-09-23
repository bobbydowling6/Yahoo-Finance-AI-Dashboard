import os
import glob
import time
from pathlib import Path
import tomllib
import chromadb
from google import genai
from google.genai import types
from google.genai.errors import APIError

CURRENT_FILE = Path(__file__).resolve()
# Navigates up from app/services/rag_services.py -> app/services -> app -> backend -> Project Root
PROJECT_ROOT = CURRENT_FILE.parents[3]

# Global Constants & Configuration
CHROMA_PATH = os.getenv("CHROMA_PATH", str(PROJECT_ROOT / "chroma_db"))
MAX_RESULTS: int = int(os.environ.get("MAX_RESULTS", "3"))
CONFIDENCE_THRESHOLD: float = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.5"))
DEBUG: bool = os.environ.get("DEBUG", "false").lower() == "true"
MODEL_NAME: str = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

# Initialize persistent ChromaDB client
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection(name="financial_docs")


def get_gemini_client() -> genai.Client:
    """Initializes and returns the Google Gen AI client."""
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        config_path = PROJECT_ROOT / "config.toml"
        
        if config_path.exists():
            with open(config_path, "rb") as f:
                config = tomllib.load(f)
                api_key = (
                    config.get("GEMINI_API_KEY") 
                    or config.get("gemini", {}).get("api_key")
                )
                if api_key:
                    os.environ["GEMINI_API_KEY"] = api_key

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. "
            "Please add GEMINI_API_KEY to config.toml or set it in your terminal environment."
        )

    return genai.Client(api_key=api_key)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Simple text chunker with overlapping context window."""
    words = text.split()
    if not words:
        return []
    
    chunks = []
    step = chunk_size - overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks


def ingest_documents_from_directory(target_dir: str = "docs") -> int:
    """Ingests text/markdown files into ChromaDB using absolute path resolution."""
    docs_path = PROJECT_ROOT / target_dir if not Path(target_dir).is_absolute() else Path(target_dir)

    print(f"🔍 DEBUG: Scanning directory for ingestion: {docs_path.resolve()}")
    
    if not docs_path.exists():
        print(f"❌ DEBUG: Directory does NOT exist: {docs_path.resolve()}")
        return 0

    files = list(docs_path.glob("*.txt")) + list(docs_path.glob("*.md"))
    print(f"🔍 DEBUG: Found {len(files)} document file(s): {[f.name for f in files]}")

    if not files:
        return 0

    total_chunks = 0

    for file_path in files:
        filename = file_path.name
        ticker = filename.split("_")[0].upper() if "_" in filename else "GENERAL"

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if not content:
            print(f"⚠️ DEBUG: File {filename} is empty. Skipping.")
            continue

        chunks = chunk_text(content)
        print(f"📄 DEBUG: Processing '{filename}' ({len(chunks)} chunks)...")

        for idx, chunk in enumerate(chunks):
            doc_id = f"{filename}_{idx}"
            collection.upsert(
                documents=[chunk],
                metadatas=[{"ticker": ticker, "source": filename, "chunk_idx": idx}],
                ids=[doc_id],
            )
            total_chunks += 1

    print(f"✅ DEBUG: Ingestion finished. Total chunks indexed: {total_chunks}")
    return total_chunks


def generate_with_fallback(client: genai.Client, user_prompt: str, system_instruction: str) -> str:
    """Tries generating content with retries and fallback models on 503/server overload."""
    models_to_try = [MODEL_NAME, "gemini-3.6-flash", "gemini-3.5-flash-lite"]
    # De-duplicate model list while preserving order
    deduped_models = list(dict.fromkeys(models_to_try))
    max_retries = 3

    for model_name in deduped_models:
        for attempt in range(max_retries):
            try:
                print(f"🤖 Attempting query with model '{model_name}' (Attempt {attempt + 1})...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.2,
                    ),
                )
                return response.text
            except APIError as e:
                if "503" in str(e) or "UNAVAILABLE" in str(e) or "429" in str(e):
                    print(f"⚠️ {model_name} unavailable (503/429). Retrying in {2 ** attempt}s...")
                    time.sleep(2 ** attempt)
                else:
                    raise e

    raise RuntimeError("All Gemini models are currently experiencing high demand. Please try again in a few moments.")


def query_rag_pipeline(query: str, ticker: str | None = None, top_k: int = MAX_RESULTS) -> dict:
    """Retrieves context from ChromaDB and generates an answer using Gemini."""
    client = get_gemini_client()

    where_clause = {"ticker": ticker.upper()} if ticker and ticker.strip() else None

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where=where_clause,
    )

    retrieved_docs = results.get("documents", [[]])[0]
    retrieved_metadatas = results.get("metadatas", [[]])[0]

    if not retrieved_docs:
        context_str = "No specific reference documents found in vector store."
    else:
        context_blocks = [
            f"[Source: {meta.get('source', 'Unknown')} | Ticker: {meta.get('ticker', 'N/A')}]\n{doc}"
            for doc, meta in zip(retrieved_docs, retrieved_metadatas)
        ]
        context_str = "\n\n---\n\n".join(context_blocks)

    system_instruction = (
        "You are an expert financial analyst assistant. Answer the user's question accurately based "
        "primarily on the provided reference context documents. If the context does not contain the answer, "
        "state that clearly and provide a general financial overview."
    )

    user_prompt = f"""Financial Documents Context:
{context_str}

User Question: {query}
"""

    # Call fallback generator with retries
    answer_text = generate_with_fallback(client, user_prompt, system_instruction)

    return {
        "query": query,
        "answer": answer_text,
        "retrieved_context": [
            {"content": doc, "metadata": meta}
            for doc, meta in zip(retrieved_docs, retrieved_metadatas)
        ],
    }


if DEBUG:
    api_key_status = "set" if os.getenv("GEMINI_API_KEY") else "not set"
    print(f"🔍 DEBUG CONFIGURATION:")
    print(f"  Gemini Key Status: {api_key_status}")
    print(f"  Model: {MODEL_NAME}")
    print(f"  Max Results: {MAX_RESULTS}")
    print(f"  Threshold: {CONFIDENCE_THRESHOLD}")