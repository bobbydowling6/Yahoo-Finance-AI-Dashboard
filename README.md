# FinInsight AI: Personal Investment & RAG-Powered Yahoo Finance Dashboard

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B)
![ChromaDB](https://img.shields.io/badge/ChromaDB-VectorStore-orange)
![Google Gemini](https://img.shields.io/badge/LLM-Google%20Gemini-8E75B2)

**FinInsight AI** is an all-in-one financial intelligence platform that combines real-time portfolio performance tracking with a Retrieval-Augmented Generation (RAG) assistant. Built with **FastAPI**, **Streamlit**, **SQLite/SQLAlchemy**, **ChromaDB**, and **Google Gemini**, it allows retail investors to track positions against live market data from Yahoo Finance and query financial documents with grounded AI answers.

---

## 👤 User Story

> **As a retail investor**, I want to log into a personalized financial dashboard to view live portfolio stock prices, monitor position gains/losses, and query financial context using an AI assistant, **so that** I can make informed investment decisions in one consolidated interface without jumping between external tabs.

---

## 🏗️ Tech Stack Overview

| Layer | Technology | Usage / Purpose |
| :--- | :--- | :--- |
| **Frontend** | Streamlit | Interactive multi-tab user interface |
| **Backend Framework** | FastAPI | Async REST API & authentication endpoints |
| **ORM & Database** | SQLAlchemy + SQLite | Relational persistence for users & portfolio holdings |
| **Authentication** | JWT (JSON Web Tokens) | Secure auth with `passlib` (bcrypt) & `python-jose` |
| **Vector Store & Embeddings** | ChromaDB + `sentence-transformers` | Semantic document chunking & vector indexing |
| **LLM Engine** | Google Gemini API (`google-genai`) | Grounded financial question answering |
| **Data Sources** | `yfinance` & Local `.txt`/`.md` files | Live market data/quotes & local 10-K context files |
| **Environment & Tooling** | Miniforge3 (Conda) / Docker | Python environment management & containerization |

---

## 📊 Data Architecture & Schemas

### Database Models & Relationships (SQLAlchemy)

┌──────────────────┐               ┌───────────────────────┐
│      Users       │               │       Portfolio       │
├──────────────────┤               ├───────────────────────┤
│ id (PK)          │ 1           * │ id (PK)               │
│ email (Unique)   ├───────────────┤ user_id (FK -> users) │
│ hashed_password  │  (1-to-Many)  │ ticker                │
│ created_at       │               │ shares_owned          │
└──────────────────┘               │ buy_price             │
                                   │ created_at            │
                                   └───────────────────────┘

* **User Model**: Stores unique user credentials with hashed passwords. Cascade deletion configured for associated portfolio items.
* **Portfolio Model**: Tracks equity positions per user, including ticker, share quantity, and initial cost basis (`buy_price`).

### Pydantic Schemas

* **Auth**: `UserCreate`, `UserLogin`, `Token`, `TokenData`
* **Portfolio**: `PortfolioCreate`, `PortfolioResponse`, `PortfolioSummaryResponse`
* **RAG Pipeline**: `RAGQueryRequest`, `RAGQueryResponse` (returns answer + retrieved chunk sources), `IngestionStatusResponse`

---

## 🔌 API Endpoints Summary

### 🔑 Authentication (`/auth`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/auth/register` | Register a new user account with hashed password credentials | ❌ |
| `POST` | `/auth/login` | Authenticate credentials and return a JWT Access Token | ❌ |

### 💼 Investment Portfolio (`/portfolio`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/portfolio/` | Fetch user portfolio populated with live `yfinance` pricing & return metrics | ✅ |
| `POST` | `/portfolio/` | Add a stock position (`ticker`, `shares`, `buy_price`) to user portfolio | ✅ |
| `DELETE` | `/portfolio/{portfolio_id}` | Remove a specific holding owned by the authenticated user | ✅ |

### 📈 Market & Stock Data (`/stocks`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/stocks/{ticker}` | Fetch real-time price, valuation metrics, and company profile via `yfinance` | ❌ |

### 🤖 AI & RAG Pipeline (`/rag`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/rag/ingest` | Chunk and index `.txt`/`.md` documents in `./docs` into ChromaDB | ✅ |
| `POST` | `/rag/query` | Perform vector search in ChromaDB & generate answers via Google Gemini | ✅ |

### 🏥 System Health & Monitoring
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/health` | Application health check endpoint for container probes | ❌ |
| `GET` | `/stats` | System status and vector store indexing statistics | ❌ |

## 🚀 Getting Started

### Prerequisites

* **Miniforge3 / Conda** or **Docker & Docker Compose**
* **Google Gemini API Key** (Obtain from [Google AI Studio](https://aistudio.google.com/))

---

### Method 1: Local Setup with Miniforge3 (Conda)

1. **Clone the Repository**
   ```bash
   git clone [https://github.com/your-username/fininsight-ai.git](https://github.com/your-username/fininsight-ai.git)
   cd fininsight-ai

2. **Create and Activate Conda Environment**
Bash
conda create -n fininsight python=3.10 -y
conda activate fininsight

3. **Install Dependencies**
pip install -r requirements.txt

4. **Environment Configuration**
Create a .env file in the root directory:
GEMINI_API_KEY=your_google_gemini_api_key_here
SECRET_KEY=your_jwt_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
DATABASE_URL=sqlite:///./fininsight.db
BACKEND_URL=http://localhost:8000

5. **Start Services**
   Backend (FASTAPI):
   uvicorn backend.app.main:app --reload --port 8000

   Frontend (Streamlit) (in a new terminal tab):
   streamlit run frontend/app.py

### Method 2: Docker Compose
Alternatively, launch the entire application stack using Docker Compose:
docker compose up --build -d

Frontend Dashboard: http://localhost:8501
FastAPI Docs (Swagger): http://localhost:8000/docs

**📂 RAG Ingestion & Document Format**

Place structured, factual financial documents (.txt or .md) into the ./docs directory.
File Naming Convention: Prefix files with ticker symbols for automatic metadata tagging (e.g., AAPL_Q3_2024.txt, NVDA_10K.txt).
Ingestion Trigger: Navigate to the Document Ingestion tab in Streamlit and click Ingest Files, or send a POST request to /rag/ingest.

**⚖️ Compliance & Redistribution Note**

To adhere to terms of service regarding live financial web scraping, all ingested RAG text files utilize publicly disclosed SEC filings (10-K summaries) or original factual company descriptions rather than proprietary news content scraped directly from external sites. Real-time market prices and historical metrics are retrieved on-demand via the yfinance Python interface.

**🧪 Testing**

Automated API test coverage is built using pytest and httpx.AsyncClient.

Run the test suite in separate terminal:
pytest                               
