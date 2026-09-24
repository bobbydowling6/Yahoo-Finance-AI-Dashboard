import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure all database models are explicitly imported first
from app.db.models import Base, get_db, User, Portfolio
from app.main import app

# Use StaticPool to persist in-memory SQLite tables across multiple session connections
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Apply FastAPI dependency override
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    """Create clean database tables before each test and drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Provide a clean TestClient instance for testing FastAPI endpoints."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def authenticated_client(client):
    """Fixture that registers a user, logs in, and yields a client with JWT headers."""
    user_data = {"email": "trader@example.com", "password": "password123"}
    
    # Register user
    client.post("/auth/register", json=user_data)
    
    # Login to retrieve token
    login_response = client.post(
        "/auth/login",
        data={"username": user_data["email"], "password": user_data["password"]},
    )
    token = login_response.json()["access_token"]
    
    # Configure client with Authorization Bearer header
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


# =====================================================================
# RAG PIPELINE TEST CASES
# =====================================================================

@patch("app.api.rag_router.query_rag_pipeline")
def test_9_rag_query_endpoint_success(mock_rag_pipeline, authenticated_client):
    """Test 9: RAG query endpoint returns structured response when pipeline is mocked."""
    mock_rag_pipeline.return_value = {
        "query": "Can you describe what SOFI does as a company?",
        "answer": "SoFi Technologies, Inc. provides digital financial services including student loans, personal loans, and fintech platform services.",
        "retrieved_context": [
            {
                "content": "SoFi Technologies, Inc. provides various financial services.",
                "metadata": {"source": "SOFI_overview.txt", "ticker": "SOFI"}
            }
        ],
    }

    rag_payload = {
        "query": "Can you describe what SOFI does as a company?",
        "ticker": "SOFI",
        "top_k": 3
    }
    response = authenticated_client.post("/rag/query", json=rag_payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "Can you describe what SOFI does as a company?"
    assert "financial services" in data["answer"].lower()
    assert len(data["retrieved_context"]) == 1
    
    mock_rag_pipeline.assert_called_once_with(
        query="Can you describe what SOFI does as a company?",
        ticker="SOFI",
        top_k=3
    )


def test_10_unauthenticated_rag_query_denied(client):
    """Test 10: Querying RAG endpoint without authentication token returns 401 Unauthorized."""
    rag_payload = {"query": "Can you describe what SOFI does as a company?"}
    response = client.post("/rag/query", json=rag_payload)
    
    assert response.status_code == 401


@patch("app.api.rag_router.query_rag_pipeline")
def test_11_rag_query_handles_empty_retrieval_fallback(mock_rag_pipeline, authenticated_client):
    """Test 11: RAG query returns general LLM response when ChromaDB returns empty context."""
    mock_rag_pipeline.return_value = {
        "query": "What is SoFi's revenue?",
        "answer": "No specific reference documents found in vector store. However, based on general knowledge...",
        "retrieved_context": []
    }

    rag_payload = {"query": "What is SoFi's revenue?", "ticker": "SOFI"}
    response = authenticated_client.post("/rag/query", json=rag_payload)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["retrieved_context"]) == 0
    assert "No specific reference documents" in data["answer"]


def test_rag_query_success_with_mock(authenticated_client):
    """Test RAG query endpoint returns answer when Gemini and ChromaDB are mocked."""
    mock_rag_response = {
        "query": "Can you describe what SOFI does as a company?",
        "answer": "SoFi Technologies, Inc. provides various financial services.",
        "retrieved_context": [{"content": "Supply chain risks...", "metadata": {"ticker": "SOFI"}}]
    }
    
    with patch("app.api.rag_router.query_rag_pipeline", return_value=mock_rag_response):
        response = authenticated_client.post(
            "/rag/query", 
            json={"query": "Can you describe what SOFI does as a company?", "ticker": "SOFI"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "SoFi Technologies, Inc. provides" in data["answer"]
        assert len(data["retrieved_context"]) == 1