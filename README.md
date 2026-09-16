Project Title
FinInsight AI: Personal Investment & RAG-Powered Yahoo Finance Dashboard

User Story
As an retail investor,
I want to log into a personalized financial dashboard to view live portfolio stock prices, read relevant news, and query financial context using an AI assistant,
So that I can make informed investment decisions in one consolidated interface without jumping between external tabs.

Component Mapping, Data Architecture & Tech Stack
Tech Stack Overview
Frontend: Streamlit
Backend Framework: FastAPI
ORM & Database: SQLAlchemy with SQLite
Authentication: JWT (JSON Web Tokens) with passlib (bcrypt)
Vector Store & Embeddings: ChromaDB with sentence-transformers
LLM Engine: Google Gemini API
Data Sources: yfinance library (Live market data/news), Local text domain files
Environment & Package Management: Miniforge3 (Conda environment)

SQLAlchemy Database Models & Relationships
User Table
id (Integer, Primary Key, Index)
email (String, Unique, Index, Nullable=False)
hashed_password (String, Nullable=False)
created_at (DateTime, Default=UTC)
Relationship: portfolio_items = relationship("Portfolio", back_populates="owner", cascade="all, delete-orphan")

Portfolio Table
id (Integer, Primary Key, Index)
user_id (Integer, ForeignKey("users.id"), Nullable=False)
ticker (String(10), Nullable=False, Index=True)
shares_owned (Float, Nullable=False)
buy_price (Float, Nullable=False)
created_at (DateTime, Default=UTC)
Relationship: owner = relationship("User", back_populates="portfolio_items")

Pydantic Schemas
Auth: UserCreate, UserLogin, Token, TokenData
Portfolio: PortfolioCreate, PortfolioResponse (maps from ORM), PortfolioSummaryResponse
RAG Pipeline: RAGQueryRequest, RAGQueryResponse (includes answer and sources list), IngestionStatusResponse
API Endpoints (FastAPI)
POST /auth/register – Creates a user account with hashed credentials.
POST /auth/login – Returns a JWT Access Token upon credential verification.
POST /portfolio_item – Adds a stock ticker, shares, and buy price (Requires JWT).
GET /portfolio – Returns user's active portfolio items populated with live yfinance pricing (Requires JWT).
DELETE /portfolio_item/{portfolio_id} – Removes a portfolio item owned by the user (Requires JWT).
POST /rag/ingest – Ingests local company .txt summary files into ChromaDB.
POST /rag/query – Executes similarity search in ChromaDB and forwards context to Google Gemini for a grounded response.

Data Source Details & Volume Estimate
Volume Estimate: Initial RAG dataset consists of 10–20 textual files (~50–100 KB total) containing structured company profiles (e.g., Apple, SoFi) formatted as clean .txt documents.

Compliance & Redistribution Note: To adhere to terms of service regarding live financial web scraping, all ingested RAG text files will use publicly disclosed SEC filings (10-K summaries) or original factual company descriptions rather than proprietary, copyrighted news content copied straight from live sites. Live market rates will be pulled directly on-demand via the yfinance Python interface.

Testing, Documentation & Setup
Testing Strategy: Automated backend API endpoint test suite written with pytest and httpx.AsyncClient to test route responses, database operations, and authentication logic.
Repository Deliverables:
requirements.txt: Pinning dependencies (fastapi, sqlalchemy, pydantic, yfinance, chromadb, google-genai, streamlit, python-jose, passlib).
README.md: Containing architecture diagrams, setup/installation steps via Miniforge3, .env.exampleguidance, database migration commands, and API execution steps.
